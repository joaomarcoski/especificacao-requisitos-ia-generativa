"""
avaliar_ragas.py — Avaliação RAGAS offline (Univille)

Fase 1: faithfulness + answer_relevancy (não exigem ground_truth) — sempre
rodam. Fase 2: context_precision + context_recall — só rodam se o JSON de
entrada tiver `ground_truth` preenchido (rodar_execucao.py já popula isso
sozinho, buscando o gabarito certo em Projetos Oficiais/Gabaritos_RAGAS/, para os 9 Project
Scenario numerados de teste). Se `ground_truth` vier `null`, essas duas
métricas são puladas para aquele arquivo — sem quebrar as duas primeiras.

Retomada seletiva: cada métrica é calculada e salva individualmente. Se o
processo for interrompido (Ctrl+C, queda de rede, erro da API) no meio de um
arquivo, rodar de novo sem --forcar não refaz as métricas que já tinham
terminado com sucesso — só completa o que falta. Isso importa porque cada
chamada ao juiz é paga; sem isso, uma interrupção jogaria fora resultado que
já tinha sido pago.

Roda separado do app Streamlit, sobre os arquivos `ragas_*.json` exportados
pelo botão "Baixar dados para avaliação RAGAS" do main.py. Dá pra rodar um
arquivo só ou apontar pra uma pasta inteira.

Concorrência entre arquivos: por padrão processa até 3 arquivos ao mesmo
tempo (--concorrencia muda isso). Cada arquivo continua avaliado do mesmo
jeito de sempre — mesmo prompt, mesmo juiz, mesma sequência das 4 métricas
dentro dele — só a espera de um arquivo terminar pro próximo começar é que
deixa de existir. Isso não muda em nada o que é perguntado ao juiz nem como
ele responde, só corta o tempo total de um lote grande (isso importava
porque 27 execuções de teste, uma atrás da outra, passavam de 10h corridas).
Cuidado ao subir muito esse número: cada arquivo já dispara várias chamadas
sequenciais internamente (principalmente context_precision, uma por chunk),
então concorrência alta entre arquivos pode esbarrar no limite de
requisições por minuto da sua conta — comece baixo e suba com cautela.

Ambiente: usa o venv_ragas/ (isolado do venv principal — ver
requirements_ragas.txt para o motivo). Não rode com o venv/ do app.

Uso:
    venv_ragas\\Scripts\\python.exe avaliar_ragas.py caminho\\para\\execucao_ragas.json
    venv_ragas\\Scripts\\python.exe avaliar_ragas.py caminho\\para\\pasta\\
    venv_ragas\\Scripts\\python.exe avaliar_ragas.py caminho\\para\\pasta\\ --forcar
    venv_ragas\\Scripts\\python.exe avaliar_ragas.py caminho\\para\\pasta\\ --concorrencia 5

Requer a variável de ambiente OPENAI_API_KEY (mesma chave usada no app, ou
outra — nunca grave a chave no código; ela deve ser definida no terminal
ou em Agente/.env antes de rodar o script):
    $env:OPENAI_API_KEY = "sk-..."
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Ver rodar_execucao.py — mesmo motivo: nome de "sistema" gerado pelo modelo
# pode ter caracteres fora do cp1252 (console padrão do Windows), e o
# print() desse nome roda fora de qualquer try/except no laço principal —
# sem isso, um caractere assim derruba a avaliação inteira, não só um arquivo.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Juiz fixo, deliberadamente fora do trio Lua/Terra/Sol (gpt-5.6-luna/terra/sol)
# testado pelo agente — evita viés de autoavaliação (um modelo tende a
# favorecer respostas no seu próprio "estilo"). Mesmo juiz nas duas fases
# (1 e 2) por consistência metodológica na pesquisa.
MODELO_JUIZ = "gpt-5-mini"
MODELO_EMBEDDING = "text-embedding-3-small"
# O padrão do ragas (max_tokens=1024) estoura em SRS grandes: faithfulness
# decompõe a resposta inteira (~3 mil palavras) em dezenas de afirmações
# atômicas antes de verificar cada uma contra o contexto — a saída
# estruturada dessa etapa sozinha já passa de 1024 tokens.
MAX_TOKENS_JUIZ = 32768

RESULTADOS_CSV = Path(__file__).parent.parent / "Testes" / "Execuções Oficiais" / "resultados_ragas.csv"

CAMPOS_CSV = [
    "data_avaliacao", "arquivo", "sistema", "modelo_gerador", "modelo_juiz",
    "faithfulness", "faithfulness_motivo",
    "answer_relevancy", "answer_relevancy_motivo",
    "context_precision", "context_precision_motivo",
    "context_recall", "context_recall_motivo",
    "rag_score", "n_contextos", "tinha_gabarito",
]

# Prefixo usado pra marcar uma métrica que foi tentada e falhou — precisa ser
# distinguível de um valor real (float) e de "" (nunca tentada), pra saber o
# que precisa ser retentado numa próxima rodada.
PREFIXO_ERRO = "ERRO: "


def carregar_execucao(caminho: Path) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def chave_execucao(caminho: Path, dados: dict) -> str:
    return f"{caminho.name}|{dados.get('sistema', '')}|{dados.get('modelo', '')}"


def _metrica_valida(valor) -> bool:
    """True se já existe um resultado utilizável pra essa métrica (não
    precisa recalcular). False se nunca foi calculada ou se a tentativa
    anterior falhou (string começando com PREFIXO_ERRO)."""
    if valor is None:
        return False
    valor = str(valor).strip()
    return bool(valor) and not valor.startswith(PREFIXO_ERRO)


def esta_completo(linha: dict, tem_gabarito: bool) -> bool:
    campos = ["faithfulness", "answer_relevancy"]
    if tem_gabarito:
        campos += ["context_precision", "context_recall"]
    return all(_metrica_valida(linha.get(c)) for c in campos)


def carregar_resultados_existentes(csv_path: Path) -> dict[str, dict]:
    """Lê o CSV atual pra um dict {chave_execucao: linha}. Migra o schema
    sozinho se o CSV for de antes de context_precision/recall existirem."""
    if not csv_path.exists():
        return {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    if linhas and list(linhas[0].keys()) != CAMPOS_CSV:
        linhas = [{campo: l.get(campo, "") for campo in CAMPOS_CSV} for l in linhas]
    resultados: dict[str, dict] = {}
    for linha in linhas:
        chave = f"{linha['arquivo']}|{linha['sistema']}|{linha['modelo_gerador']}"
        resultados[chave] = linha
    return resultados


def salvar_resultados(csv_path: Path, resultados: dict[str, dict]) -> None:
    """Reescreve o CSV inteiro a partir do dict em memória — chamado depois
    de cada arquivo processado, não só no final, pra não perder progresso
    se o processo for interrompido no arquivo seguinte."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        writer.writeheader()
        for linha in resultados.values():
            writer.writerow({campo: linha.get(campo, "") for campo in CAMPOS_CSV})


async def avaliar_arquivo(caminho: Path, client: AsyncOpenAI, existente: dict | None) -> dict:
    from ragas.embeddings import OpenAIEmbeddings
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecisionWithReference,
        ContextRecall,
        Faithfulness,
    )

    dados = carregar_execucao(caminho)
    pergunta = dados["question"]
    resposta = dados["answer"]
    contextos = dados["contexts"]
    gabarito = dados.get("ground_truth")

    if not contextos:
        raise ValueError(
            f"{caminho.name}: 'contexts' vazio — a execução original não capturou "
            "nenhum chunk do file_search. Não dá pra avaliar faithfulness sem contexto."
        )

    linha = dict(existente) if existente else {campo: "" for campo in CAMPOS_CSV}
    linha.update({
        "data_avaliacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "arquivo": caminho.name,
        "sistema": dados.get("sistema", ""),
        "modelo_gerador": dados.get("modelo", ""),
        "modelo_juiz": MODELO_JUIZ,
        "rag_score": dados.get("rag_score", ""),
        "n_contextos": len(contextos),
        "tinha_gabarito": bool(gabarito),
    })

    llm = llm_factory(MODELO_JUIZ, client=client, max_tokens=MAX_TOKENS_JUIZ)
    embeddings = OpenAIEmbeddings(client=client, model=MODELO_EMBEDDING)

    # Com vários arquivos rodando ao mesmo tempo, os prints de cada um se
    # intercalam no terminal — sem o nome do arquivo em cada linha, não dá
    # pra saber de qual execução é cada "calculando faithfulness...".
    rotulo = caminho.name

    async def _computar(nome_campo: str, campo_motivo: str, fabrica_coro) -> None:
        # fabrica_coro só é chamada (e portanto só cria a coroutine e manda a
        # requisição) se a métrica realmente precisar ser (re)calculada — do
        # contrário sobra uma coroutine nunca aguardada (RuntimeWarning), e em
        # tese uma requisição desnecessária se a lib validar algo no __init__.
        if _metrica_valida(linha.get(nome_campo)):
            print(f"      [{rotulo}] {nome_campo}: já calculado, reaproveitando ({linha[nome_campo]})")
            return
        print(f"      [{rotulo}] calculando {nome_campo}...")
        try:
            resultado = await fabrica_coro()
            linha[nome_campo] = round(resultado.value, 4)
            linha[campo_motivo] = resultado.reason or ""
            print(f"      [{rotulo}] {nome_campo} = {linha[nome_campo]}")
        except Exception as e:
            linha[nome_campo] = f"{PREFIXO_ERRO}{e}"
            print(f"      [{rotulo}] {nome_campo} FALHOU: {e}")

    await _computar(
        "faithfulness", "faithfulness_motivo",
        lambda: Faithfulness(llm=llm).ascore(user_input=pergunta, response=resposta, retrieved_contexts=contextos),
    )
    await _computar(
        "answer_relevancy", "answer_relevancy_motivo",
        lambda: AnswerRelevancy(llm=llm, embeddings=embeddings).ascore(user_input=pergunta, response=resposta),
    )

    if gabarito:
        await _computar(
            "context_precision", "context_precision_motivo",
            lambda: ContextPrecisionWithReference(llm=llm).ascore(
                user_input=pergunta, reference=gabarito, retrieved_contexts=contextos,
            ),
        )
        await _computar(
            "context_recall", "context_recall_motivo",
            lambda: ContextRecall(llm=llm).ascore(
                user_input=pergunta, retrieved_contexts=contextos, reference=gabarito,
            ),
        )

    return linha


def listar_arquivos(caminho: Path) -> list[Path]:
    if caminho.is_file():
        return [caminho]
    return sorted(caminho.glob("**/ragas_*.json"))


async def _processar_um(
    caminho: Path,
    client: AsyncOpenAI,
    resultados: dict[str, dict],
    semaforo: asyncio.Semaphore,
    forcar: bool,
    progresso: dict,
) -> None:
    """Processa um arquivo, respeitando o limite de concorrência do
    semáforo. `resultados` e `progresso` são compartilhados entre todas as
    tarefas concorrentes — seguro porque asyncio é cooperativo/single-thread
    (nenhuma dessas atualizações tem um `await` no meio), e porque cada
    tarefa só escreve na sua própria chave do dict.
    """
    def _log(msg: str) -> None:
        print(f"[{progresso['feitos']}/{progresso['total']}] {msg}")

    try:
        dados = carregar_execucao(caminho)
    except json.JSONDecodeError as e:
        progresso["feitos"] += 1
        _log(f"{caminho.name}: JSON inválido, pulando ({e})")
        return

    chave = chave_execucao(caminho, dados)
    tem_gabarito = bool(dados.get("ground_truth"))
    existente = None if forcar else resultados.get(chave)

    if existente and esta_completo(existente, tem_gabarito):
        progresso["feitos"] += 1
        _log(f"{caminho.name}: já avaliado (todas as métricas), pulando — use --forcar pra refazer")
        return

    async with semaforo:
        modo = "retomando" if existente else "avaliando"
        print(f"[iniciando] {caminho.name} — {modo} com juiz {MODELO_JUIZ}...")
        try:
            linha = await avaliar_arquivo(caminho, client, existente)
        except Exception as e:
            progresso["feitos"] += 1
            _log(f"{caminho.name}: falhou por completo ({e})")
            return

    resultados[chave] = linha
    salvar_resultados(RESULTADOS_CSV, resultados)

    resumo = f"faithfulness={linha['faithfulness']} answer_relevancy={linha['answer_relevancy']}"
    if tem_gabarito:
        resumo += f" context_precision={linha['context_precision']} context_recall={linha['context_recall']}"
    else:
        resumo += " (sem gabarito — context_precision/recall pulados)"
    progresso["feitos"] += 1
    _log(f"{caminho.name}: {resumo}")


async def main_async(args: argparse.Namespace) -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit(
            "OPENAI_API_KEY não definida. Rode antes:\n"
            '  $env:OPENAI_API_KEY = "sk-..."'
        )

    caminho_entrada = Path(args.caminho)
    if not caminho_entrada.exists():
        sys.exit(f"Caminho não encontrado: {caminho_entrada}")

    arquivos = listar_arquivos(caminho_entrada)
    if not arquivos:
        sys.exit(f"Nenhum arquivo 'ragas_*.json' encontrado em: {caminho_entrada}")

    if args.concorrencia < 1:
        sys.exit("--concorrencia precisa ser 1 ou mais.")

    resultados = carregar_resultados_existentes(RESULTADOS_CSV)
    client = AsyncOpenAI()
    semaforo = asyncio.Semaphore(args.concorrencia)
    progresso = {"feitos": 0, "total": len(arquivos)}

    print(f"Processando {len(arquivos)} arquivo(s), até {args.concorrencia} em paralelo...\n")
    await asyncio.gather(*(
        _processar_um(caminho, client, resultados, semaforo, args.forcar, progresso)
        for caminho in arquivos
    ))

    print(f"\nResultados salvos em: {RESULTADOS_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("caminho", help="Arquivo ragas_*.json ou pasta contendo vários")
    parser.add_argument(
        "--forcar", action="store_true",
        help="Reavalia do zero mesmo arquivos já completos ou parcialmente avaliados",
    )
    parser.add_argument(
        "--concorrencia", type=int, default=3,
        help="Quantos arquivos avaliar ao mesmo tempo (padrão: 3). Suba com cautela — "
             "cada arquivo já faz várias chamadas sequenciais por conta própria.",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
