"""
rodar_lote.py — Orquestra o lote completo de execuções oficiais (fase de
geração), cobrindo o desenho metodológico decidido para a pesquisa: 27 execuções
base (9 cenários × 3 modelos, 1x cada) + 18 execuções extras (Project
Scenario 6/SLCCI, 7/SBD Rio e 8/BECS × 3 modelos × mais 2 repetições cada,
totalizando 3 execuções por modelo nesses 3 cenários) — 45 no total.

Resumível: mantém um manifesto (_lote_manifest.json) na pasta de saída com
o resultado de cada combinação (cenário, modelo, repetição) já tentada.
Rodar de novo pula tudo que já terminou com sucesso — não refaz nem gasta
API de novo. Uma execução que falhar (erro de rede, timeout, JSON inválido
etc.) é registrada como falha no manifesto e não derruba o restante do lote.

Uso:
    venv\\Scripts\\python.exe rodar_lote.py <pasta_saida>
    venv\\Scripts\\python.exe rodar_lote.py <pasta_saida> --forcar
    venv\\Scripts\\python.exe rodar_lote.py <pasta_saida> --so-cenario 8
    venv\\Scripts\\python.exe rodar_lote.py <pasta_saida> --so-modelo Lua

Requer OPENAI_API_KEY (ver rodar_execucao.py / Agente/.env). Os cenários são
lidos de Projetos Oficiais/Cenarios/Project Scenario N.pdf.
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv

import rodar_execucao  # noqa: E402 — instala o stub do streamlit e importa main como efeito colateral
import main  # noqa: E402 — reaproveita o import já feito por rodar_execucao (streamlit já mockado)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CENARIOS_DIR = Path(__file__).parent.parent / "Projetos Oficiais" / "Cenarios"

# Cenários com execução repetida (fase 4 — média ± desvio padrão): número do
# Project Scenario -> quantas execuções totais por modelo. Os outros 6
# cenários (não listados aqui) têm 1 execução por modelo, ver PADRAO_EXECUCOES.
# Desenho metodológico descrito no README (seção Resultados).
EXECUCOES_POR_MODELO = {6: 3, 7: 3, 8: 3}  # SLCCI, SBD Rio, BECS
PADRAO_EXECUCOES = 1

MANIFESTO_NOME = "_lote_manifest.json"


def localizar_cenario(numero: int) -> Path:
    candidatos = list(CENARIOS_DIR.glob(f"Project Scenario {numero}.pdf"))
    if not candidatos:
        raise FileNotFoundError(f"Project Scenario {numero}.pdf não encontrado em {CENARIOS_DIR}")
    return candidatos[0]


def gerar_combinacoes(so_cenario: int | None, so_modelo: str | None) -> list[tuple[int, str, int]]:
    combinacoes = []
    for numero in range(1, 10):
        if so_cenario and numero != so_cenario:
            continue
        n_exec = EXECUCOES_POR_MODELO.get(numero, PADRAO_EXECUCOES)
        for modelo_label in main.MODELOS:
            if so_modelo and modelo_label != so_modelo:
                continue
            for rep in range(1, n_exec + 1):
                combinacoes.append((numero, modelo_label, rep))
    return combinacoes


def chave(numero: int, modelo_label: str, rep: int) -> str:
    return f"{numero}|{modelo_label}|{rep}"


def carregar_manifesto(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def salvar_manifesto(caminho: Path, manifesto: dict) -> None:
    caminho.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")


def main_run(args: argparse.Namespace) -> None:
    load_dotenv(Path(__file__).parent / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        sys.exit(
            "OPENAI_API_KEY não definida. Adicione ao Agente/.env "
            "(OPENAI_API_KEY=sk-...) ou defina a variável de ambiente antes de rodar."
        )
    if not main.VS_B_ID:
        sys.exit("VS_B_ID não configurado (Agente/.env). Crie a vector store B e defina VS_B_ID (ver README).")

    pasta_saida: Path = args.pasta_saida
    pasta_saida.mkdir(parents=True, exist_ok=True)
    caminho_manifesto = pasta_saida / MANIFESTO_NOME
    manifesto = {} if args.forcar else carregar_manifesto(caminho_manifesto)

    combinacoes = gerar_combinacoes(args.so_cenario, args.so_modelo)
    total = len(combinacoes)
    print(f"Lote: {total} combinação(ões) — pasta de saída: {pasta_saida}\n")

    ja_feitos = sum(1 for c in combinacoes if manifesto.get(chave(*c), {}).get("status") == "ok")
    if ja_feitos and not args.forcar:
        print(f"{ja_feitos}/{total} já concluída(s) em execução anterior (retomando) — use --forcar pra refazer tudo.\n")

    for i, (numero, modelo_label, rep) in enumerate(combinacoes, start=1):
        k = chave(numero, modelo_label, rep)
        if not args.forcar and manifesto.get(k, {}).get("status") == "ok":
            print(f"[{i}/{total}] Scenario {numero} / {modelo_label} / rep{rep}: já feito, pulando.")
            continue

        try:
            caminho_cenario = localizar_cenario(numero)
        except FileNotFoundError as e:
            manifesto[k] = {"status": "falhou", "erro": str(e)}
            salvar_manifesto(caminho_manifesto, manifesto)
            print(f"[{i}/{total}] FALHOU (cenário não encontrado): {e}\n")
            continue

        n_exec = EXECUCOES_POR_MODELO.get(numero, PADRAO_EXECUCOES)
        sufixo = f"_rep{rep}" if n_exec > 1 else ""

        print(f"[{i}/{total}] Scenario {numero} ({caminho_cenario.name}) / {modelo_label} / rep{rep}...")
        inicio = time.time()
        try:
            resultado = rodar_execucao.rodar(
                modelo_label, caminho_cenario, pasta_saida, "", api_key, sufixo=sufixo,
            )
            manifesto[k] = {
                "status": "ok",
                "sistema": resultado["sistema"],
                "arquivo_ragas": resultado["caminho_ragas"].name,
                "rag_score": resultado["rag_score"],
                "duracao_s": round(resultado["duracao_s"], 1),
                "custo_usd": resultado["custo_usd"],
                "tinha_gabarito_ragas": resultado["tinha_gabarito_ragas"],
                "tinha_gabarito_rfrnf": resultado["tinha_gabarito_rfrnf"],
            }
            print(
                f"[{i}/{total}] OK — {resultado['sistema']} — "
                f"{resultado['duracao_s']:.0f}s — US$ {resultado['custo_usd']:.4f}\n"
            )
        except Exception as e:
            traceback.print_exc()
            manifesto[k] = {"status": "falhou", "erro": str(e), "duracao_s": round(time.time() - inicio, 1)}
            print(f"[{i}/{total}] FALHOU: {e}\n")
        finally:
            salvar_manifesto(caminho_manifesto, manifesto)

    ok = sum(1 for v in manifesto.values() if v.get("status") == "ok")
    falhas = sum(1 for v in manifesto.values() if v.get("status") == "falhou")
    custo_total = sum(v.get("custo_usd", 0) for v in manifesto.values() if v.get("status") == "ok")
    print(f"\nLote concluído: {ok} OK, {falhas} falha(s). Custo de geração acumulado: US$ {custo_total:.4f}")
    print(f"Manifesto: {caminho_manifesto}")
    if falhas:
        print("Rode o mesmo comando de novo pra retomar só o que falhou (não refaz o que já deu certo).")


def main_cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pasta_saida", type=Path)
    parser.add_argument("--forcar", action="store_true", help="Refaz tudo, ignorando o manifesto de progresso")
    parser.add_argument("--so-cenario", type=int, default=None, help="Roda só um número de Project Scenario (1-9)")
    parser.add_argument(
        "--so-modelo", choices=list(main.MODELOS.keys()), default=None,
        help="Roda só um modelo (Lua/Terra/Sol)",
    )
    args = parser.parse_args()
    main_run(args)


if __name__ == "__main__":
    main_cli()
