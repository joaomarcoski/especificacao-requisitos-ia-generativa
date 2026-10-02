"""
avaliar_qualidade.py — Avaliação de qualidade do SRS via LLM-as-judge
(Fase 2 do roadmap de métricas da pesquisa — Univille)

Avalia cada execução em três dimensões, numa escala de 1 a 5:
  - correctness  (correção técnica dos artefatos gerados)
  - completeness (cobertura do que o cenário pedia)
  - conciseness  (ausência de redundância/inchaço)

Reaproveita os mesmos arquivos `ragas_*.json` exportados pelo botão "Baixar
dados para avaliação RAGAS" do main.py (ou gerados por rodar_execucao.py) —
não precisa de um export novo, porque `question`/`answer` já têm o cenário
original e o SRS renderizado em texto plano. Quando o arquivo tem
`ground_truth` preenchido (os 9 Project Scenario de teste têm, via
Projetos Oficiais/Gabaritos_RAGAS/), esse gabarito é passado ao juiz como lista de fatos que
o SRS deveria cobrir — deixa a nota de completeness mais rigorosa/ancorada,
em vez de depender só da leitura solta do cenário.

Diferente de avaliar_ragas.py: roda no venv/ principal (não precisa da
biblioteca ragas, é só uma chamada estruturada ao juiz), sem asyncio (uma
chamada só por arquivo, não quatro). Mesmo juiz das outras fases (gpt-5-mini,
fora do trio Lua/Terra/Sol testado) por consistência metodológica.

Uso:
    venv\\Scripts\\python.exe avaliar_qualidade.py caminho\\para\\execucao_ragas.json
    venv\\Scripts\\python.exe avaliar_qualidade.py caminho\\para\\pasta\\
    venv\\Scripts\\python.exe avaliar_qualidade.py caminho\\para\\pasta\\ --forcar

Requer a variável de ambiente OPENAI_API_KEY (nunca grave a chave no
código — defina no terminal ou em Agente/.env antes de rodar):
    $env:OPENAI_API_KEY = "sk-..."
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Ver rodar_execucao.py / avaliar_ragas.py — mesmo motivo: nome de "sistema"
# gerado pelo modelo pode ter caracteres fora do cp1252 (console padrão do
# Windows), e isso não pode derrubar o processo inteiro.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Mesmo juiz fixo das outras fases — fora do trio gpt-5.6-luna/terra/sol
# testado, pra não incorrer em viés de autoavaliação. Consistência
# metodológica: um único juiz em todas as fases da pesquisa.
MODELO_JUIZ = "gpt-5-mini"

RESULTADOS_CSV = Path(__file__).parent.parent / "Testes" / "Execuções Oficiais" / "resultados_qualidade.csv"

CAMPOS_CSV = [
    "data_avaliacao", "arquivo", "sistema", "modelo_gerador", "modelo_juiz",
    "tinha_gabarito",
    "correctness", "correctness_justificativa",
    "completeness", "completeness_justificativa",
    "conciseness", "conciseness_justificativa",
]

DIMENSOES = ("correctness", "completeness", "conciseness")

PROMPT_JUIZ = """Você é um avaliador experiente de Engenharia de Requisitos, revisando um \
Documento de Especificação de Requisitos de Software (SRS) gerado por um \
sistema de IA a partir de um documento de cenário de projeto.

Avalie o SRS abaixo em três dimensões, cada uma numa escala de 1 (muito \
ruim) a 5 (excelente):

1. CORRECTNESS (correção técnica): os artefatos seguem as convenções \
esperadas? Todo requisito funcional usa "deve" e descreve algo verificável? \
Todo requisito não funcional tem categoria ISO/IEC 25010 e métrica de \
aceitação objetiva (não subjetiva)? Histórias de usuário seguem o formato \
Connextra ("Como/quero/para")? Critérios de aceite seguem o formato \
Dado/Quando/Então? Há alguma contradição interna, absurdo técnico, ou \
quebra de rastreabilidade entre artefatos (ex.: HU referenciando um RF que \
não existe)?

2. COMPLETENESS (completude): o SRS cobre adequadamente o que foi pedido no \
documento de cenário? Falta alguma funcionalidade, ator, restrição ou regra \
de negócio claramente mencionada no cenário e ausente do SRS? A quantidade \
de RFs/RNFs/HUs/CAs é proporcional à complexidade do cenário, nem \
superficial nem inventando escopo que o cenário não pediu?{bloco_gabarito}

3. CONCISENESS (concisão): o texto é direto, sem redundância desnecessária? \
Algum artefato repete a mesma informação de outro sem necessidade? Alguma \
descrição é desnecessariamente longa, genérica ou vaga quando poderia ser \
objetiva e específica?

DOCUMENTO DE CENÁRIO ORIGINAL (o que foi pedido):
{pergunta}

SRS GERADO (o que foi entregue):
{resposta}

Retorne SOMENTE um objeto JSON com este formato exato, sem texto antes ou \
depois, sem bloco de código markdown:
{{
  "correctness": <inteiro de 1 a 5>,
  "correctness_justificativa": "1-2 frases explicando a nota",
  "completeness": <inteiro de 1 a 5>,
  "completeness_justificativa": "1-2 frases explicando a nota",
  "conciseness": <inteiro de 1 a 5>,
  "conciseness_justificativa": "1-2 frases explicando a nota"
}}"""

BLOCO_GABARITO = """

Use também esta lista de fatos/requisitos que um SRS bem fundamentado para \
este cenário deveria conseguir cobrir, como referência adicional para \
julgar completude (nem todo item precisa aparecer literalmente, mas \
lacunas grandes contra essa lista pesam contra a nota):
{gabarito}"""


class AvaliacaoInvalida(Exception):
    """Levantado quando o juiz não retorna o formato/faixa esperados."""


def carregar_execucao(caminho: Path) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def chave_execucao(caminho: Path, dados: dict) -> str:
    return f"{caminho.name}|{dados.get('sistema', '')}|{dados.get('modelo', '')}"


def carregar_resultados_existentes(csv_path: Path) -> dict[str, dict]:
    """Lê o CSV atual pra um dict {chave_execucao: linha}. Migra o schema
    sozinho se as colunas mudarem no futuro. Usar um dict (não só um set de
    chaves já vistas) permite reescrever o arquivo inteiro sem duplicar
    linha quando --forcar reavalia algo que já estava lá."""
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
    de cada arquivo, não só no final, pra não perder progresso se o
    processo for interrompido no arquivo seguinte."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        writer.writeheader()
        for linha in resultados.values():
            writer.writerow({campo: linha.get(campo, "") for campo in CAMPOS_CSV})


def _validar_avaliacao(avaliacao: dict) -> None:
    for dimensao in DIMENSOES:
        if dimensao not in avaliacao:
            raise AvaliacaoInvalida(f"campo '{dimensao}' ausente na resposta do juiz")
        nota = avaliacao[dimensao]
        if not isinstance(nota, int) or isinstance(nota, bool) or not (1 <= nota <= 5):
            raise AvaliacaoInvalida(f"'{dimensao}' = {nota!r} não é um inteiro entre 1 e 5")
        campo_motivo = f"{dimensao}_justificativa"
        if campo_motivo not in avaliacao or not str(avaliacao[campo_motivo]).strip():
            raise AvaliacaoInvalida(f"campo '{campo_motivo}' ausente ou vazio na resposta do juiz")


def montar_prompt(pergunta: str, resposta: str, gabarito: str | None) -> str:
    bloco_gabarito = BLOCO_GABARITO.format(gabarito=gabarito) if gabarito else ""
    return PROMPT_JUIZ.format(pergunta=pergunta, resposta=resposta, bloco_gabarito=bloco_gabarito)


def avaliar_arquivo(caminho: Path, client: OpenAI) -> dict:
    dados = carregar_execucao(caminho)
    pergunta = dados.get("question")
    resposta = dados.get("answer")
    gabarito = dados.get("ground_truth")

    if not pergunta or not resposta:
        raise ValueError(
            f"{caminho.name}: 'question' ou 'answer' ausente/vazio no JSON — "
            "não há o que avaliar."
        )

    prompt = montar_prompt(pergunta, resposta, gabarito)

    response = client.responses.create(
        model=MODELO_JUIZ,
        input=[{"role": "user", "content": prompt}],
        text={"format": {"type": "json_object"}},
    )

    try:
        avaliacao = json.loads(response.output_text)
    except json.JSONDecodeError as e:
        raise AvaliacaoInvalida(f"juiz não retornou JSON válido: {e}")

    _validar_avaliacao(avaliacao)

    return {
        "data_avaliacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "arquivo": caminho.name,
        "sistema": dados.get("sistema", ""),
        "modelo_gerador": dados.get("modelo", ""),
        "modelo_juiz": MODELO_JUIZ,
        "tinha_gabarito": bool(gabarito),
        "correctness": avaliacao["correctness"],
        "correctness_justificativa": avaliacao["correctness_justificativa"],
        "completeness": avaliacao["completeness"],
        "completeness_justificativa": avaliacao["completeness_justificativa"],
        "conciseness": avaliacao["conciseness"],
        "conciseness_justificativa": avaliacao["conciseness_justificativa"],
    }


def listar_arquivos(caminho: Path) -> list[Path]:
    if caminho.is_file():
        return [caminho]
    return sorted(caminho.glob("**/ragas_*.json"))


def main_run(args: argparse.Namespace) -> None:
    load_dotenv(Path(__file__).parent / ".env")
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

    resultados = carregar_resultados_existentes(RESULTADOS_CSV)
    client = OpenAI()

    total = len(arquivos)
    for i, caminho in enumerate(arquivos, start=1):
        try:
            dados = carregar_execucao(caminho)
        except json.JSONDecodeError as e:
            print(f"[{i}/{total}] {caminho.name}: JSON inválido, pulando ({e})")
            continue

        chave = chave_execucao(caminho, dados)
        if not args.forcar and chave in resultados:
            print(f"[{i}/{total}] {caminho.name}: já avaliado, pulando (use --forcar pra refazer)")
            continue

        print(f"[{i}/{total}] {caminho.name} — avaliando qualidade com juiz {MODELO_JUIZ}...")
        try:
            linha = avaliar_arquivo(caminho, client)
        except Exception as e:
            print(f"[{i}/{total}] {caminho.name}: falhou ({e})")
            continue

        resultados[chave] = linha
        salvar_resultados(RESULTADOS_CSV, resultados)
        print(
            f"[{i}/{total}] {caminho.name}: correctness={linha['correctness']} "
            f"completeness={linha['completeness']} conciseness={linha['conciseness']}"
        )

    print(f"\nResultados salvos em: {RESULTADOS_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("caminho", help="Arquivo ragas_*.json ou pasta contendo vários")
    parser.add_argument(
        "--forcar", action="store_true",
        help="Reavalia mesmo arquivos já presentes em resultados_qualidade.csv",
    )
    args = parser.parse_args()
    main_run(args)


if __name__ == "__main__":
    main()
