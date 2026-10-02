# Gera as figuras dos capítulos 3 e 4 do artigo a partir dos resultados das
# 45 execuções oficiais (Testes/Execuções Oficiais). Só lê os CSVs já
# produzidos pelo pipeline — não chama a API nem recalcula nenhuma métrica.
#
# Uso: python gerar_graficos.py   (salva os PNGs nesta mesma pasta)

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import FuncFormatter

PASTA = Path(__file__).parent
DADOS = PASTA.parent / "Execuções Oficiais"

# Cada modelo tem sempre a mesma cor e o mesmo marcador em todas as figuras.
# Os marcadores/hachuras garantem a leitura também em impressão em cinza.
MODELOS = {"gpt-5.6-luna": "Lua", "gpt-5.6-terra": "Terra", "gpt-5.6-sol": "Sol"}
ORDEM = ["Lua", "Terra", "Sol"]
COR = {"Lua": "#2a78d6", "Terra": "#eb6834", "Sol": "#1baf7a"}
MARCADOR = {"Lua": "o", "Terra": "s", "Sol": "^"}
HACHURA = {"Lua": "", "Terra": "//", "Sol": ".."}
CINZA = "#898781"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
GRADE = "#e1e0d9"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": TINTA,
    "xtick.color": TINTA_2,
    "ytick.color": TINTA_2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

# Separador decimal brasileiro nos eixos (0,5 em vez de 0.5)
virgula = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))


def br(valor, casas=2):
    return f"{valor:.{casas}f}".replace(".", ",")


def grade(ax, eixo="y"):
    ax.grid(axis=eixo, color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)


def salvar(fig, nome):
    fig.savefig(PASTA / nome, facecolor="white")
    plt.close(fig)
    print("salvo:", nome)


# ---------------------------------------------------------------------------
# Carregamento — o número do cenário vem do manifesto do lote, nunca do campo
# "sistema" (o nome do sistema varia entre execuções do mesmo cenário).
# ---------------------------------------------------------------------------
manifesto = json.loads((DADOS / "_lote_manifest.json").read_text(encoding="utf-8"))
cenario_do_arquivo = {v["arquivo_ragas"]: int(k.split("|")[0]) for k, v in manifesto.items()}
NOMES_CENARIO = {1: "GRD", 2: "UUIS", 3: "IPG", 4: "MDT", 5: "SIMDE",
                 6: "SLCCI", 7: "SBD Rio", 8: "BECS", 9: "FFMIA"}

ragas = pd.read_csv(DADOS / "resultados_ragas.csv", encoding="utf-8-sig")
classif = pd.read_csv(DADOS / "resultados_classificacao.csv", encoding="utf-8-sig")
qualidade = pd.read_csv(DADOS / "resultados_qualidade.csv", encoding="utf-8-sig")
repeticoes = pd.read_csv(DADOS / "resultados_repeticoes.csv", encoding="utf-8-sig")

execucoes = []
for arq in DADOS.glob("execucao_*.csv"):
    linha = pd.read_csv(arq, encoding="utf-8-sig").iloc[0].to_dict()
    linha["arquivo"] = "ragas_" + arq.stem[len("execucao_"):] + ".json"
    execucoes.append(linha)
execucoes = pd.DataFrame(execucoes)

df = (ragas[["arquivo", "modelo_gerador", "faithfulness", "answer_relevancy",
             "context_precision", "context_recall", "rag_score"]]
      .merge(classif[["arquivo", "geral_precision", "geral_recall", "geral_f1"]], on="arquivo")
      .merge(execucoes[["arquivo", "custo_total_usd", "tempo_execucao_s", "tokens_total"]], on="arquivo"))
df["modelo"] = df["modelo_gerador"].map(MODELOS)
df["cenario"] = df["arquivo"].map(cenario_do_arquivo)
assert len(df) == 45 and df["cenario"].notna().all()


# ---------------------------------------------------------------------------
# Figura 1 — Arquitetura do protótipo (diagrama de fluxo)
# ---------------------------------------------------------------------------
def figura_arquitetura():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 112)
    ax.set_ylim(1, 46)
    ax.axis("off")

    def caixa(x, y, w, h, titulo, detalhe, cor="#f0efec", borda="#52514e"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    facecolor=cor, edgecolor=borda, linewidth=1))
        ax.text(x + w / 2, y + h * 0.66, titulo, ha="center", va="center",
                fontsize=9.5, fontweight="bold", color=TINTA)
        ax.text(x + w / 2, y + h * 0.3, detalhe, ha="center", va="center",
                fontsize=8, color=TINTA_2)

    def seta(x1, y1, x2, y2, texto=None, dy=1.6):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                     mutation_scale=12, color=TINTA_2, linewidth=1))
        if texto:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + dy, texto, ha="center",
                    fontsize=7.5, color=TINTA_2, style="italic")

    caixa(1, 30, 21, 13, "Usuário", "interface Streamlit\ncenário (PDF/DOCX/TXT)")
    caixa(29, 30, 26, 13, "Requisição ao modelo", "prompt do sistema +\ntexto integral do cenário")
    caixa(62, 30, 21, 13, "Modelo GPT-5.6", "Lua | Terra | Sol\nResponses API")
    caixa(90, 30, 21, 13, "Saída", "JSON estruturado\n→ SRS em .docx")
    caixa(46, 4, 23, 13, "Vector store B", "base fixa de ER\n(7 documentos)", cor="#dcebfb")
    caixa(76, 4, 23, 13, "Vector store A", "cenário da sessão\n(apoio pontual)", cor="#eef4fc")
    caixa(8, 4, 27, 13, "Métricas da execução", "RAG Score, tokens,\ntempo e custo")

    seta(22.4, 36.5, 28.6, 36.5)
    seta(55.4, 36.5, 61.6, 36.5)
    seta(83.4, 36.5, 89.6, 36.5)
    seta(69, 29.5, 60, 17.5, "file_search", dy=0)
    seta(76, 29.5, 84, 17.5)
    seta(62, 31, 35.5, 14, "escores dos trechos", dy=2.5)
    salvar(fig, "figura_01_arquitetura.png")


# ---------------------------------------------------------------------------
# Figura 2 — Faithfulness por execução (strip plot)
# ---------------------------------------------------------------------------
def figura_faithfulness():
    fig, ax = plt.subplots(figsize=(7, 3.6))
    rng = np.random.default_rng(7)
    for i, m in enumerate(ORDEM):
        s = df[df["modelo"] == m]
        x = i + rng.uniform(-0.12, 0.12, len(s))
        ax.scatter(x, s["faithfulness"], s=40, color=COR[m], marker=MARCADOR[m],
                   edgecolor="white", linewidth=0.8, zorder=3)
        media = s["faithfulness"].mean()
        ax.hlines(media, i - 0.2, i + 0.2, color=TINTA, linewidth=1.5, zorder=4)
        ax.text(i + 0.23, media, f"média\n{br(media, 3)}", va="center", fontsize=7.5, color=TINTA)

    out = df.loc[df["faithfulness"].idxmin()]
    ax.annotate(f"{NOMES_CENARIO[out['cenario']]} ({out['modelo']}): {br(out['faithfulness'])}",
                xy=(ORDEM.index(out["modelo"]), out["faithfulness"]),
                xytext=(0.45, 0.4), fontsize=8, color=TINTA_2,
                arrowprops=dict(arrowstyle="-", color=CINZA, linewidth=0.8))
    ax.set_xticks(range(3), ORDEM)
    ax.set_xlim(-0.5, 2.9)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Faithfulness (0 a 1)")
    ax.yaxis.set_major_formatter(virgula)
    grade(ax)
    salvar(fig, "figura_02_faithfulness_execucoes.png")


# ---------------------------------------------------------------------------
# Figura 4 — Precisão × Recall por tipo de artefato (dumbbell)
# ---------------------------------------------------------------------------
CATEGORIAS = {
    "escopo_em": "Escopo (incluído)", "escopo_fora": "Escopo (excluído)",
    "stk": "Stakeholders", "rn": "Regras de negócio", "rf": "Req. funcionais",
    "rnf": "Req. não funcionais", "hu": "Histórias de usuário",
    "uc": "Casos de uso", "ca": "Critérios de aceite",
}


def totais_por_categoria(base):
    linhas = []
    for c, nome in CATEGORIAS.items():
        tp, fp, fn = (base[f"{c}_{k}"].sum() for k in ("tp", "fp", "fn"))
        p, r = tp / (tp + fp), tp / (tp + fn)
        linhas.append({"categoria": nome, "tp": tp, "fp": fp, "fn": fn,
                       "precisao": p, "recall": r, "f1": 2 * p * r / (p + r)})
    return pd.DataFrame(linhas)


def figura_precisao_recall():
    t = totais_por_categoria(classif)
    t["distancia"] = t["recall"] - t["precisao"]
    t = t.sort_values("distancia").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    y = np.arange(len(t))
    ax.hlines(y, t["precisao"], t["recall"], color="#c3c2b7", linewidth=3, zorder=2)
    ax.scatter(t["precisao"], y, s=55, color="#1c5cab", marker="o", zorder=3, label="Precisão")
    ax.scatter(t["recall"], y, s=55, color="white", edgecolor="#1c5cab", linewidth=1.6,
               marker="o", zorder=3, label="Recall")
    for yi, (p, r) in enumerate(zip(t["precisao"], t["recall"])):
        ax.text(p - 0.02, yi, br(p), ha="right", va="center", fontsize=8, color=TINTA_2)
        ax.text(r + 0.02, yi, br(r), ha="left", va="center", fontsize=8, color=TINTA_2)
    ax.set_yticks(y, t["categoria"])
    ax.set_xlim(0, 1.1)
    ax.set_xlabel("Valor (0 a 1) — soma de VP, FP e FN das 45 execuções")
    ax.xaxis.set_major_formatter(virgula)
    grade(ax, "x")
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    salvar(fig, "figura_04_precisao_recall_artefatos.png")
    return t


# ---------------------------------------------------------------------------
# Figura 5 — Itens gerados em relação ao gabarito, por modelo
# ---------------------------------------------------------------------------
def figura_razao_gerado():
    razoes = {}
    for mod, m in MODELOS.items():
        s = classif[classif["modelo_gerador"] == mod]
        gerados = s["geral_tp"].sum() + s["geral_fp"].sum()
        esperados = s["geral_tp"].sum() + s["geral_fn"].sum()
        razoes[m] = gerados / esperados

    fig, ax = plt.subplots(figsize=(6, 3.4))
    x = np.arange(3)
    barras = ax.bar(x, [razoes[m] for m in ORDEM], width=0.55,
                    color=[COR[m] for m in ORDEM], hatch=[HACHURA[m] for m in ORDEM],
                    edgecolor="white", linewidth=0.8, zorder=3)
    for b, m in zip(barras, ORDEM):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.04,
                f"{br(razoes[m])}×", ha="center", fontsize=9, color=TINTA)
    ax.hlines(1, -0.5, 2.3, color=TINTA, linewidth=1, linestyle="--", zorder=4)
    ax.text(2.33, 1.0, " gabarito\n (1,0×)", ha="left", va="center", fontsize=8, color=TINTA)
    ax.set_xlim(-0.5, 2.85)
    ax.set_xticks(x, ORDEM)
    ax.set_ylim(0, 2.5)
    ax.set_ylabel("Itens gerados / itens esperados")
    ax.yaxis.set_major_formatter(virgula)
    grade(ax)
    salvar(fig, "figura_05_razao_gerado_esperado.png")
    return razoes


# ---------------------------------------------------------------------------
# Figura 6 — Custo por execução × F1 (dispersão, custo em escala log)
# ---------------------------------------------------------------------------
def figura_custo_f1():
    fig, ax = plt.subplots(figsize=(7, 4))
    for m in ORDEM:
        s = df[df["modelo"] == m]
        ax.scatter(s["custo_total_usd"], s["geral_f1"], s=42, color=COR[m], marker=MARCADOR[m],
                   edgecolor="white", linewidth=0.8, zorder=3,
                   label=f"{m} (média US$ {br(s['custo_total_usd'].mean(), 3)}; F1 {br(s['geral_f1'].mean(), 3)})")
    ax.set_xscale("log")
    ax.set_xticks([0.02, 0.05, 0.1, 0.2, 0.5, 1.0])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: "US$ " + f"{v:g}".replace(".", ",")))
    ax.xaxis.set_minor_formatter(FuncFormatter(lambda *_: ""))
    ax.set_xlim(0.012, 1.0)
    ax.set_ylim(0.4, 0.9)
    ax.yaxis.set_major_formatter(virgula)
    ax.set_xlabel("Custo da execução (escala logarítmica)")
    ax.set_ylabel("F1 geral")
    grade(ax, "both")
    ax.legend(loc="lower left", frameon=False, fontsize=8)
    salvar(fig, "figura_06_custo_f1.png")


# ---------------------------------------------------------------------------
# Figura 7 — Estabilidade entre repetições: faixa de CV por métrica
# ---------------------------------------------------------------------------
METRICAS_CV = {
    "context_precision": "Context precision", "rag_score": "RAG Score",
    "answer_relevancy": "Answer relevancy", "custo_usd": "Custo",
    "tempo_s": "Tempo", "precision_geral": "Precisão (P/R/F1)",
    "correctness": "Juiz: correção", "completeness": "Juiz: completude",
    "f1_geral": "F1 geral", "context_recall": "Context recall",
    "recall_geral": "Recall (P/R/F1)", "conciseness": "Juiz: concisão",
    "faithfulness": "Faithfulness",
}
RECUPERACAO = {"context_precision", "rag_score"}


def figura_estabilidade():
    g = (repeticoes.groupby("metrica")["cv_percentual"]
         .agg(["min", "mean", "max"]).loc[list(METRICAS_CV)]
         .sort_values("mean"))
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    y = np.arange(len(g))
    for yi, (met, lin) in enumerate(g.iterrows()):
        destaque = met in RECUPERACAO
        cor = "#1c5cab" if destaque else CINZA
        ax.hlines(yi, lin["min"], lin["max"], color=cor, linewidth=4 if destaque else 3,
                  alpha=0.35 if destaque else 0.45, zorder=2)
        ax.scatter(lin["mean"], yi, s=36, color=cor, zorder=3)
        ax.text(lin["max"] + 0.6, yi, f"{br(lin['mean'], 1)}% (até {br(lin['max'], 1)}%)",
                va="center", fontsize=7.5, color=TINTA if destaque else TINTA_2)
    ax.set_yticks(y, [METRICAS_CV[m] for m in g.index])
    for rotulo, met in zip(ax.get_yticklabels(), g.index):
        if met in RECUPERACAO:
            rotulo.set_fontweight("bold")
            rotulo.set_color(TINTA)
    ax.set_xlim(0, 36)
    ax.set_xlabel("Coeficiente de variação entre repetições (%) — mínimo, média e máximo")
    ax.xaxis.set_major_formatter(virgula)
    grade(ax, "x")
    salvar(fig, "figura_07_estabilidade_repeticoes.png")
    return g


# ---------------------------------------------------------------------------
# Figura 3 — RAG Score × F1 (dispersão)
# ---------------------------------------------------------------------------
def figura_rag_f1():
    r = df["rag_score"].corr(df["geral_f1"])
    fig, ax = plt.subplots(figsize=(7, 4))
    for m in ORDEM:
        s = df[df["modelo"] == m]
        ax.scatter(s["rag_score"], s["geral_f1"], s=42, color=COR[m], marker=MARCADOR[m],
                   edgecolor="white", linewidth=0.8, zorder=3, label=m)
    a, b = np.polyfit(df["rag_score"], df["geral_f1"], 1)
    xs = np.linspace(df["rag_score"].min(), df["rag_score"].max(), 2)
    ax.plot(xs, a * xs + b, color=CINZA, linewidth=1.2, linestyle="--", zorder=2)
    ax.text(0.98, 0.95, f"r de Pearson = {br(r).replace('-', '−')} (n = 45)", transform=ax.transAxes,
            ha="right", va="top", fontsize=8.5, color=TINTA)
    ax.set_xlabel("RAG Score (média dos escores de similaridade)")
    ax.set_ylabel("F1 geral")
    ax.xaxis.set_major_formatter(virgula)
    ax.yaxis.set_major_formatter(virgula)
    grade(ax, "both")
    ax.legend(loc="lower left", frameon=False, fontsize=8.5, title="Modelo", title_fontsize=8.5)
    salvar(fig, "figura_03_rag_score_f1.png")
    return r


if __name__ == "__main__":
    figura_arquitetura()
    figura_faithfulness()
    t = figura_precisao_recall()
    razoes = figura_razao_gerado()
    figura_custo_f1()
    g = figura_estabilidade()
    r = figura_rag_f1()

    print("\nPrecisão/Recall por categoria (micro):")
    print(t[["categoria", "tp", "fp", "fn", "precisao", "recall", "f1"]].round(3).to_string(index=False))
    print("\nRazão gerado/esperado:", {m: round(v, 2) for m, v in razoes.items()})
    print("r(RAG Score, F1) =", round(r, 3))
