"""
avaliar_classificacao.py — Precision / Recall / F1 clássicos (estilo sklearn)
(Fase 3 da avaliação da pesquisa — Univille)

Compara, artefato por artefato (escopo em/fora, stakeholders, regras de
negócio, RF, RNF, HU, casos de uso, critérios de aceite), a lista ESPERADA
(gabarito em Projetos Oficiais/Gabaritos_RFRNF/gabarito_rfrnf_N_*.json) contra a lista
GERADA pelo agente numa execução. Como a descrição gerada nunca é texto
idêntico ao do gabarito, o casamento item a item é feito pelo mesmo juiz das
outras fases (gpt-5-mini), que decide correspondência semântica um-para-um
(cada item gerado só pode cobrir no máximo um item esperado).

A partir do casamento: TP = itens esperados cobertos por um item gerado,
FN = itens esperados não cobertos, FP = itens gerados que não correspondem
a nada esperado. precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = média
harmônica — as mesmas fórmulas de sklearn.metrics.precision_recall_fscore_support,
aplicadas sobre o resultado do casamento em vez de sobre um vetor de classes.

Reaproveita os mesmos arquivos `ragas_*.json` das outras fases — só que
agora eles também precisam ter as chaves `artefatos` (saída estruturada da
execução) e `gabarito_artefatos` (gabarito da fase 3), ambas adicionadas por
gerar_json_ragas()/rodar_execucao.py. Arquivos gerados antes dessa mudança,
ou de cenários sem gabarito_rfrnf_N_*.json ainda escrito, são pulados com
aviso — não quebra o processamento dos demais.

Roda no venv/ principal (não precisa de ragas), sem asyncio — mesmo padrão
de simplicidade do avaliar_qualidade.py. Cada arquivo faz até 9 chamadas
sequenciais ao juiz (uma por categoria de artefato; categorias com listas
vazias dos dois lados são puladas sem chamada).

Uso:
    venv\\Scripts\\python.exe avaliar_classificacao.py caminho\\para\\execucao_ragas.json
    venv\\Scripts\\python.exe avaliar_classificacao.py caminho\\para\\pasta\\
    venv\\Scripts\\python.exe avaliar_classificacao.py caminho\\para\\pasta\\ --forcar

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

# Ver rodar_execucao.py / avaliar_ragas.py / avaliar_qualidade.py — mesmo
# motivo: texto gerado pelo modelo pode ter caracteres fora do cp1252
# (console padrão do Windows), e isso não pode derrubar o processo inteiro.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Mesmo juiz fixo das outras fases — fora do trio gpt-5.6-luna/terra/sol
# testado, pra não incorrer em viés de autoavaliação. Consistência
# metodológica: um único juiz em todas as fases da pesquisa.
MODELO_JUIZ = "gpt-5-mini"

RESULTADOS_CSV = Path(__file__).parent.parent / "Testes" / "Execuções Oficiais" / "resultados_classificacao.csv"

# (chave em artefatos/gabarito_artefatos, rótulo pro prompt, prefixo curto pras colunas do CSV)
CATEGORIAS = [
    ("escopo_em_escopo", "itens em escopo", "escopo_em"),
    ("escopo_fora_de_escopo", "itens fora de escopo", "escopo_fora"),
    ("stakeholders", "stakeholders", "stk"),
    ("regras_de_negocio", "regras de negócio", "rn"),
    ("requisitos_funcionais", "requisitos funcionais", "rf"),
    ("requisitos_nao_funcionais", "requisitos não funcionais", "rnf"),
    ("historias_de_usuario", "histórias de usuário", "hu"),
    ("casos_de_uso", "casos de uso", "uc"),
    ("criterios_de_aceite", "critérios de aceite", "ca"),
]

CAMPOS_CSV = ["data_avaliacao", "arquivo", "sistema", "modelo_gerador", "modelo_juiz"]
for _, _, _codigo in CATEGORIAS:
    CAMPOS_CSV += [f"{_codigo}_tp", f"{_codigo}_fp", f"{_codigo}_fn",
                   f"{_codigo}_precision", f"{_codigo}_recall", f"{_codigo}_f1"]
CAMPOS_CSV += ["geral_tp", "geral_fp", "geral_fn", "geral_precision", "geral_recall", "geral_f1"]

PROMPT_MATCHING = """Você está comparando duas listas de {rotulo} de um SRS (Documento de \
Especificação de Requisitos de Software): uma lista ESPERADA (gabarito de referência) e \
uma lista GERADA (produzida por um agente de IA a partir do mesmo cenário de projeto).

Para cada item da lista ESPERADA, decida se existe um item correspondente na lista \
GERADA — mesmo que a redação seja diferente, considere correspondência se a essência \
semântica for a mesma (mesmo requisito, mesma regra, mesmo ator, mesma condição etc.). \
Cada item da lista GERADA só pode ser usado para corresponder a NO MÁXIMO um item da \
lista ESPERADA (correspondência um-para-um) — se dois itens gerados parecerem cobrir o \
mesmo item esperado, escolha o que corresponde melhor e deixe o outro sem correspondência.

LISTA ESPERADA:
{esperados}

LISTA GERADA:
{gerados}

Retorne SOMENTE um objeto JSON no formato exato abaixo, sem texto antes ou depois, sem \
bloco de código markdown — uma entrada em "matches" para CADA item da lista ESPERADA, na \
mesma ordem em que foram listados. Use o id exatamente como aparece entre colchetes nas \
listas acima, mas SEM os colchetes (ex.: "ESP::RF-01", não "[ESP::RF-01]"):
{{
  "matches": [
    {{"esperado_id": "<id do item esperado>", "gerado_id": "<id do item gerado correspondente, ou null se nenhum corresponder>"}}
  ]
}}"""


class AvaliacaoInvalida(Exception):
    """Levantado quando o juiz não retorna o formato esperado."""


def carregar_execucao(caminho: Path) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def chave_execucao(caminho: Path, dados: dict) -> str:
    return f"{caminho.name}|{dados.get('sistema', '')}|{dados.get('modelo', '')}"


def carregar_resultados_existentes(csv_path: Path) -> dict[str, dict]:
    """Lê o CSV atual pra um dict {chave_execucao: linha}. Migra o schema
    sozinho se as colunas mudarem no futuro (mesmo padrão das outras fases)."""
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
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        writer.writeheader()
        for linha in resultados.values():
            writer.writerow({campo: linha.get(campo, "") for campo in CAMPOS_CSV})


def _texto_item_gerado(chave: str, item: dict) -> str:
    """Achata um item gerado (schema varia por tipo de artefato — ver
    PROMPT_SISTEMA em main.py) num texto comparável ao 'descricao' do
    gabarito. Mesma ideia de renderizar_texto_srs(), só que por item."""
    if chave == "stakeholders":
        return f"{item.get('nome', '')} ({item.get('tipo', '')}): {item.get('necessidades', '')}"
    if chave == "regras_de_negocio":
        return f"{item.get('titulo', '')}: {item.get('descricao', '')}"
    if chave == "requisitos_funcionais":
        return f"{item.get('titulo', '')}: {item.get('descricao', '')} [{item.get('prioridade', '')}]"
    if chave == "requisitos_nao_funcionais":
        return (f"({item.get('categoria_iso25010', '')}) {item.get('descricao', '')} "
                f"| Métrica: {item.get('metrica_aceitacao', '')}")
    if chave == "historias_de_usuario":
        return f"Como {item.get('como', '')}, quero {item.get('quero', '')}, para {item.get('para', '')}"
    if chave == "casos_de_uso":
        fluxo = "; ".join(item.get("fluxo_principal", []))
        return f"{item.get('nome', '')} | Ator: {item.get('ator_principal', '')} | Fluxo: {fluxo}"
    if chave == "criterios_de_aceite":
        return f"Dado {item.get('dado', '')}, quando {item.get('quando', '')}, então {item.get('entao', '')}"
    return json.dumps(item, ensure_ascii=False)


def _itens_gabarito(gabarito_artefatos: dict, chave: str) -> list[tuple[str, str]]:
    if chave in ("escopo_em_escopo", "escopo_fora_de_escopo"):
        campo = "em_escopo" if chave == "escopo_em_escopo" else "fora_de_escopo"
        textos = (gabarito_artefatos.get("escopo") or {}).get(campo, [])
        return [(f"{chave.upper()}-{i + 1}", t) for i, t in enumerate(textos)]
    itens = gabarito_artefatos.get(chave) or []
    return [(it.get("id") or f"{chave}-{i + 1}", it.get("descricao", "")) for i, it in enumerate(itens)]


def _itens_gerados(artefatos: dict, chave: str) -> list[tuple[str, str]]:
    if chave in ("escopo_em_escopo", "escopo_fora_de_escopo"):
        campo = "em_escopo" if chave == "escopo_em_escopo" else "fora_de_escopo"
        textos = (artefatos.get("escopo") or {}).get(campo, [])
        return [(f"{chave.upper()}-{i + 1}", t) for i, t in enumerate(textos)]
    itens = artefatos.get(chave) or []
    return [(it.get("id") or f"{chave}-{i + 1}", _texto_item_gerado(chave, it)) for i, it in enumerate(itens)]


def _formatar_lista(itens: list[tuple[str, str]], prefixo: str) -> str:
    # O prefixo evita colisão de id entre as duas listas no prompt — sem
    # isso, categorias sem id "de fábrica" (escopo em/fora de escopo, onde
    # tanto o gabarito quanto a saída gerada são listas de string cruas)
    # acabam com o mesmo esquema sintético dos dois lados (ex.: os dois
    # começam em "ESCOPO_EM_ESCOPO-1"), e o juiz confunde qual id pertence a
    # qual lista — visto na prática: matches inconsistentes mesmo com texto
    # claramente equivalente.
    return "\n".join(f"- [{prefixo}{id_}] {texto}" for id_, texto in itens) or "(lista vazia)"


def avaliar_categoria(client: OpenAI, rotulo: str, esperados: list[tuple[str, str]],
                       gerados: list[tuple[str, str]]) -> dict:
    total_e, total_g = len(esperados), len(gerados)

    if total_e == 0 and total_g == 0:
        return {"tp": 0, "fp": 0, "fn": 0, "precision": "", "recall": "", "f1": ""}
    if total_e == 0:
        return {"tp": 0, "fp": total_g, "fn": 0, "precision": 0.0, "recall": "", "f1": ""}
    if total_g == 0:
        return {"tp": 0, "fp": 0, "fn": total_e, "precision": "", "recall": 0.0, "f1": ""}

    # Prefixos diferentes por lista — ver comentário em _formatar_lista.
    PREFIXO_E, PREFIXO_G = "ESP::", "GER::"
    prompt = PROMPT_MATCHING.format(
        rotulo=rotulo,
        esperados=_formatar_lista(esperados, PREFIXO_E),
        gerados=_formatar_lista(gerados, PREFIXO_G),
    )
    response = client.responses.create(
        model=MODELO_JUIZ,
        input=[{"role": "user", "content": prompt}],
        text={"format": {"type": "json_object"}},
    )
    try:
        resultado = json.loads(response.output_text)
    except json.JSONDecodeError as e:
        raise AvaliacaoInvalida(f"juiz não retornou JSON válido: {e}")

    matches = resultado.get("matches")
    if not isinstance(matches, list):
        raise AvaliacaoInvalida("campo 'matches' ausente ou não é uma lista na resposta do juiz")

    def _normalizar_id(bruto, prefixo: str) -> str | None:
        # O juiz às vezes ecoa os colchetes/espaços do jeito em que os ids
        # aparecem no prompt ("- [ESP::X] texto") em vez de só o id — mais
        # robusto normalizar aqui do que confiar que a saída vem sempre
        # limpa.
        if not isinstance(bruto, str):
            return None
        limpo = bruto.strip().strip("[]").strip()
        return limpo[len(prefixo):] if limpo.startswith(prefixo) else limpo

    ids_esperados_validos = {id_ for id_, _ in esperados}
    ids_gerados_validos = {id_ for id_, _ in gerados}
    esperados_usados: set[str] = set()
    gerados_usados: set[str] = set()
    tp = 0
    for m in matches:
        eid = _normalizar_id(m.get("esperado_id"), PREFIXO_E)
        gid = _normalizar_id(m.get("gerado_id"), PREFIXO_G)
        if eid not in ids_esperados_validos or eid in esperados_usados:
            continue
        # Correspondência um-para-um nos dois sentidos: nem um id esperado
        # nem um id gerado podem contar duas vezes — sem isso, o juiz
        # repetindo o mesmo esperado_id em duas entradas (ou o mesmo
        # gerado_id) inflaria TP além de total_e/total_g, o que deixaria
        # precision/recall passarem de 1.0.
        if gid and gid in ids_gerados_validos and gid not in gerados_usados:
            esperados_usados.add(eid)
            gerados_usados.add(gid)
            tp += 1

    fn = total_e - tp
    fp = total_g - tp
    precision = tp / total_g
    recall = tp / total_e
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4),
    }


def avaliar_arquivo(caminho: Path, client: OpenAI) -> dict:
    dados = carregar_execucao(caminho)
    artefatos = dados.get("artefatos")
    gabarito_artefatos = dados.get("gabarito_artefatos")

    if not artefatos:
        raise ValueError(
            f"{caminho.name}: sem chave 'artefatos' — arquivo gerado antes da fase 3 existir. "
            "Rode rodar_execucao.py de novo pra este cenário pra regerar o export com essa chave."
        )
    if not gabarito_artefatos:
        raise ValueError(
            f"{caminho.name}: sem 'gabarito_artefatos' — ainda não existe gabarito_rfrnf_N_*.json "
            "pra este cenário em Projetos Oficiais/Gabaritos_RFRNF/."
        )

    linha = {
        "data_avaliacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "arquivo": caminho.name,
        "sistema": dados.get("sistema", ""),
        "modelo_gerador": dados.get("modelo", ""),
        "modelo_juiz": MODELO_JUIZ,
    }

    tp_total = fp_total = fn_total = 0
    for chave, rotulo, codigo in CATEGORIAS:
        esperados = _itens_gabarito(gabarito_artefatos, chave)
        gerados = _itens_gerados(artefatos, chave)
        print(f"      [{caminho.name}] {codigo}: {len(esperados)} esperado(s) x {len(gerados)} gerado(s)...")
        try:
            resultado = avaliar_categoria(client, rotulo, esperados, gerados)
        except Exception as e:
            print(f"      [{caminho.name}] {codigo} FALHOU: {e}")
            resultado = {"tp": "", "fp": "", "fn": "", "precision": f"ERRO: {e}", "recall": "", "f1": ""}

        for campo, valor in resultado.items():
            linha[f"{codigo}_{campo}"] = valor
        if isinstance(resultado["tp"], int):
            tp_total += resultado["tp"]
            fp_total += resultado["fp"]
            fn_total += resultado["fn"]

    precision_geral = tp_total / (tp_total + fp_total) if (tp_total + fp_total) else ""
    recall_geral = tp_total / (tp_total + fn_total) if (tp_total + fn_total) else ""
    f1_geral = ""
    if isinstance(precision_geral, float) and isinstance(recall_geral, float) and (precision_geral + recall_geral) > 0:
        f1_geral = round(2 * precision_geral * recall_geral / (precision_geral + recall_geral), 4)
    linha.update({
        "geral_tp": tp_total, "geral_fp": fp_total, "geral_fn": fn_total,
        "geral_precision": round(precision_geral, 4) if isinstance(precision_geral, float) else precision_geral,
        "geral_recall": round(recall_geral, 4) if isinstance(recall_geral, float) else recall_geral,
        "geral_f1": f1_geral,
    })
    return linha


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

        print(f"[{i}/{total}] {caminho.name} — avaliando classificação com juiz {MODELO_JUIZ}...")
        try:
            linha = avaliar_arquivo(caminho, client)
        except Exception as e:
            print(f"[{i}/{total}] {caminho.name}: pulado ({e})")
            continue

        resultados[chave] = linha
        salvar_resultados(RESULTADOS_CSV, resultados)
        print(f"[{i}/{total}] {caminho.name}: geral precision={linha['geral_precision']} "
              f"recall={linha['geral_recall']} f1={linha['geral_f1']}")

    print(f"\nResultados salvos em: {RESULTADOS_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("caminho", help="Arquivo ragas_*.json ou pasta contendo vários")
    parser.add_argument(
        "--forcar", action="store_true",
        help="Reavalia mesmo arquivos já presentes em resultados_classificacao.csv",
    )
    args = parser.parse_args()
    main_run(args)


if __name__ == "__main__":
    main()
