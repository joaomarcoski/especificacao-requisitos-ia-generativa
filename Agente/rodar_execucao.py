"""
rodar_execucao.py — Executa o pipeline de elicitação fora do Streamlit,
salvando .docx + .csv + ragas.json numa pasta de saída.

Reaproveita as funções de negócio de main.py (criar_vector_store_usuario,
elicitar_requisitos, gerar_docx, gerar_csv_execucao, gerar_json_ragas) sem
rodar a interface Streamlit — útil para gerar lotes de teste na linha de
comando, que depois são avaliados um a um por avaliar_ragas.py.

Uso:
    venv\\Scripts\\python.exe rodar_execucao.py <ModeloLabel> <cenario.pdf|docx|txt> <pasta_saida> [--contexto "obs extras"]

<ModeloLabel> é uma chave de MODELOS em main.py: Lua, Terra ou Sol.

Requer OPENAI_API_KEY no ambiente — coloque em Agente/.env
(OPENAI_API_KEY=sk-...) ou defina a variável antes de rodar. Nunca passe a
chave como argumento de linha de comando (fica no histórico do shell).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from unittest import mock

from dotenv import load_dotenv

# O console do Windows costuma usar cp1252 (sem fallback de substituição) —
# print() de texto fora desse alcance (ex.: nome de sistema gerado em outro
# idioma/escrita) lança UnicodeEncodeError e derruba o processo. reconfigure
# pra utf-8 com substituição evita a queda; exibe "?" no lugar do caractere
# em vez de travar.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Caracteres inválidos em nome de arquivo no Windows (< > : " / \ | ? *) mais
# controle. "sistema" vem de texto gerado pelo modelo — sem essa sanitização,
# um nome com ":" ou "/" (comum em títulos do tipo "Sistema X: Módulo Y")
# quebra Path.write_bytes() depois da chamada à API já ter sido paga.
_CARACTERES_INVALIDOS_WINDOWS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitizar_nome_arquivo(nome: str) -> str:
    nome = _CARACTERES_INVALIDOS_WINDOWS.sub("_", nome).strip(" .")
    return nome or "projeto"


class _FakeSessionState(dict):
    """session_state do Streamlit aceita acesso por atributo E por chave."""
    def __getattr__(self, k):
        return self.get(k)

    def __setattr__(self, k, v):
        self[k] = v


def _instalar_stub_streamlit() -> None:
    # main.py é um script Streamlit (roda código de UI no nível de módulo,
    # não numa função main()) — importar sem isso disparava os widgets de
    # verdade. O stub deixa `st.button(...)` retornar False, então o bloco
    # de geração do app original nunca executa; este script chama as
    # funções de negócio diretamente, com seus próprios argumentos.
    st_stub = mock.MagicMock()
    st_stub.session_state = _FakeSessionState()
    st_stub.radio.return_value = "Lua"
    st_stub.text_input.return_value = ""
    st_stub.text_area.return_value = ""
    st_stub.file_uploader.return_value = None
    st_stub.button.return_value = False
    sys.modules["streamlit"] = st_stub


_instalar_stub_streamlit()
import main  # noqa: E402 — import só depois do stub, de propósito


GABARITOS_DIR = Path(__file__).parent.parent / "Projetos Oficiais" / "Gabaritos_RAGAS"
GABARITOS_RFRNF_DIR = Path(__file__).parent.parent / "Projetos Oficiais" / "Gabaritos_RFRNF"


def localizar_gabarito(caminho_cenario: Path) -> str | None:
    """Acha o gabarito (ground_truth) correspondente a um dos 9 Project
    Scenario numerados de teste, pelo número no nome do arquivo.

    Retorna None se o cenário não for um dos 9 (ex.: documento arbitrário
    de um uso real do app) — nesse caso context_precision/context_recall
    ficam de fora da avaliação, só faithfulness/answer_relevancy rodam.
    """
    m = re.search(r"Project Scenario (\d+)", caminho_cenario.name, re.IGNORECASE)
    if not m:
        return None
    numero = m.group(1)
    candidatos = list(GABARITOS_DIR.glob(f"gabarito_{numero}_*.txt"))
    if not candidatos:
        return None
    return candidatos[0].read_text(encoding="utf-8")


def localizar_gabarito_artefatos(caminho_cenario: Path) -> dict | None:
    """Acha o gabarito estruturado de RF/RNF/RN/HU/UC/CA/stakeholders/escopo
    (fase 3 — precision/recall/F1 clássicos) correspondente a um dos 9
    Project Scenario numerados de teste, pelo número no nome do arquivo.

    Retorna None se não existir gabarito desse tipo pra esse cenário ainda
    (nem todos os 9 têm um até o momento) — avaliar_classificacao.py pula
    o arquivo nesse caso, sem afetar as fases 1/2.
    """
    m = re.search(r"Project Scenario (\d+)", caminho_cenario.name, re.IGNORECASE)
    if not m:
        return None
    numero = m.group(1)
    candidatos = list(GABARITOS_RFRNF_DIR.glob(f"gabarito_rfrnf_{numero}_*.json"))
    if not candidatos:
        return None
    return json.loads(candidatos[0].read_text(encoding="utf-8"))


class ArquivoLocal:
    """Adapta um arquivo em disco pra interface que main.py espera
    (.name / .getvalue()), igual ao UploadedFile do Streamlit."""

    def __init__(self, caminho: Path):
        self.name = caminho.name
        self._dados = caminho.read_bytes()

    def getvalue(self) -> bytes:
        return self._dados


def rodar(
    modelo_label: str, caminho_cenario: Path, pasta_saida: Path, contexto: str, api_key: str,
    sufixo: str = "",
) -> dict:
    # sufixo (ex.: "_rep2") existe pro desenho de execuções repetidas (fase 4
    # — média ± desvio padrão): sem ele, rodar o mesmo cenário+modelo mais de
    # uma vez sobrescreve silenciosamente os 3 arquivos de saída da rodada
    # anterior, já que o nome depende só de {sistema}_{modelo}, não de qual
    # repetição é. Ver rodar_lote.py, que já passa esse sufixo automaticamente.
    modelo = main.MODELOS[modelo_label]
    arquivo = ArquivoLocal(caminho_cenario)

    print(f"Extraindo texto do cenário ({caminho_cenario.name})...")
    texto_cenario = main.extrair_texto_cenario([arquivo])

    client = main.OpenAI(api_key=api_key, timeout=120)
    vs_a_id = None
    try:
        print("Criando Vector Store A e enviando o documento...")
        vs_a_id = main.criar_vector_store_usuario(client, [arquivo])
        print(f"  Vector Store A: {vs_a_id}")

        print(f"Chamando o modelo {modelo} ({modelo_label})...")

        def _progresso(elapsed, mensagem=None):
            print(f"  ... {mensagem or f'{elapsed:.0f}s'}")

        dados, rag_score, duracao_s, tokens, contextos = main.elicitar_requisitos(
            api_key, modelo, vs_a_id, main.VS_B_ID, contexto, texto_cenario, on_progress=_progresso,
        )
        custo = main.calcular_custo_usd(modelo, tokens)
        print(
            f"Concluído em {duracao_s:.0f}s — RAG Score {rag_score:.4f} — "
            f"{tokens['total']} tokens — custo US$ {custo['total']:.4f}"
        )
    finally:
        if vs_a_id:
            print("Removendo Vector Store temporário...")
            main.descartar_vector_store_sessao(client, vs_a_id, on_warning=print)

    sistema = sanitizar_nome_arquivo(dados.get("sistema", "projeto")).replace(" ", "_")
    pasta_saida.mkdir(parents=True, exist_ok=True)
    base_nome = f"{sistema}_{modelo}{sufixo}"

    docx_bytes = main.gerar_docx(dados, modelo, rag_score, duracao_s, tokens, custo)
    caminho_docx = pasta_saida / f"SRS_{base_nome}.docx"
    caminho_docx.write_bytes(docx_bytes)

    csv_bytes = main.gerar_csv_execucao(dados, modelo, rag_score, duracao_s, tokens, custo)
    caminho_csv = pasta_saida / f"execucao_{base_nome}.csv"
    caminho_csv.write_bytes(csv_bytes)

    ground_truth = localizar_gabarito(caminho_cenario)
    gabarito_artefatos = localizar_gabarito_artefatos(caminho_cenario)
    print(f"Gabarito RAGAS: {'sim' if ground_truth else 'não (context_precision/recall ficam de fora)'}")
    print(f"Gabarito RF/RNF (fase 3): {'sim' if gabarito_artefatos else 'não (avaliar_classificacao.py pula este arquivo)'}")
    ragas_bytes = main.gerar_json_ragas(
        dados, modelo, contexto, texto_cenario, contextos, rag_score, ground_truth,
        gabarito_artefatos=gabarito_artefatos,
    )
    caminho_ragas = pasta_saida / f"ragas_{base_nome}.json"
    caminho_ragas.write_bytes(ragas_bytes)

    print(f"Salvo em: {pasta_saida}")
    return {
        "sistema": dados.get("sistema", "projeto"),
        "caminho_docx": caminho_docx,
        "caminho_csv": caminho_csv,
        "caminho_ragas": caminho_ragas,
        "rag_score": rag_score,
        "duracao_s": duracao_s,
        "custo_usd": custo["total"],
        "tokens_total": tokens["total"],
        "tinha_gabarito_ragas": bool(ground_truth),
        "tinha_gabarito_rfrnf": bool(gabarito_artefatos),
    }


def main_cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("modelo_label", choices=list(main.MODELOS.keys()))
    parser.add_argument("cenario", type=Path)
    parser.add_argument("pasta_saida", type=Path)
    parser.add_argument("--contexto", default="")
    parser.add_argument(
        "--repeticao", type=int, default=None,
        help="Número da repetição (2, 3, ...) para o desenho de execuções repetidas — "
             "adiciona um sufixo _repN ao nome dos 3 arquivos de saída, evitando que "
             "sobrescrevam uma execução anterior do mesmo cenário+modelo. Omitir para "
             "uma execução única (sem sufixo).",
    )
    args = parser.parse_args()

    load_dotenv(Path(__file__).parent / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        sys.exit(
            "OPENAI_API_KEY não definida. Adicione ao Agente/.env "
            "(OPENAI_API_KEY=sk-...) ou defina a variável de ambiente antes de rodar."
        )
    if not main.VS_B_ID:
        sys.exit("VS_B_ID não configurado (Agente/.env). Crie a vector store B e defina VS_B_ID (ver README).")
    if not args.cenario.exists():
        sys.exit(f"Arquivo de cenário não encontrado: {args.cenario}")

    sufixo = f"_rep{args.repeticao}" if args.repeticao else ""
    rodar(args.modelo_label, args.cenario, args.pasta_saida, args.contexto, api_key, sufixo=sufixo)


if __name__ == "__main__":
    main_cli()
