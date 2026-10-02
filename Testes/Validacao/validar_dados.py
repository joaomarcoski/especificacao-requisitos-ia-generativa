# Validação dos dados do artigo — somente leitura, não chama a API.
#
# Camada 1: integridade das fontes brutas (manifesto, execucao_*.csv,
#           ragas_*.json, gabaritos) contra os CSVs de resultado.
# Camada 3: recalcula os valores que alimentam tabelas e figuras.
#
# Também grava valores_recalculados.json com todos os números canônicos,
# usados na conferência das afirmações do texto (camada 2).
#
# Uso: python validar_dados.py

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "Testes" / "Execuções Oficiais"
GAB_RFRNF = RAIZ / "Projetos Oficiais" / "Gabaritos_RFRNF"
GAB_RAGAS = RAIZ / "Projetos Oficiais" / "Gabaritos_RAGAS"
SAIDA = Path(__file__).parent

sys.path.insert(0, str(RAIZ / "Agente"))
# PRECOS_USD e o preço do file_search são lidos do próprio main.py, sem importar
# o módulo (ele importa streamlit e openai).
_src = (RAIZ / "Agente" / "main.py").read_text(encoding="utf-8")
_ns = {}
exec(re.search(r"PRECOS_USD = \{.*?\n\}", _src, re.S).group(0), _ns)
exec(re.search(r"PRECO_FILE_SEARCH_POR_1K_CHAMADAS = .*", _src).group(0), _ns)
PRECOS_USD = _ns["PRECOS_USD"]
PRECO_BUSCA = _ns["PRECO_FILE_SEARCH_POR_1K_CHAMADAS"]

MODELOS = {"gpt-5.6-luna": "Lua", "gpt-5.6-terra": "Terra", "gpt-5.6-sol": "Sol"}
ORDEM = ["Lua", "Terra", "Sol"]
NOMES = {1: "GRD", 2: "UUIS", 3: "IPG", 4: "MDT", 5: "SIMDE",
         6: "SLCCI", 7: "SBD Rio", 8: "BECS", 9: "FFMIA"}
CATS = {"escopo_em": ("escopo", "em_escopo"), "escopo_fora": ("escopo", "fora_de_escopo"),
        "stk": "stakeholders", "rn": "regras_de_negocio", "rf": "requisitos_funcionais",
        "rnf": "requisitos_nao_funcionais", "hu": "historias_de_usuario",
        "uc": "casos_de_uso", "ca": "criterios_de_aceite"}

ok, falhas = [], []


def checar(cond, nome, detalhe=""):
    (ok if cond else falhas).append(f"{nome}{' — ' + str(detalhe) if detalhe else ''}")
    return cond


def tamanho(art, cat):
    ref = CATS[cat]
    if isinstance(ref, tuple):
        return len((art.get(ref[0]) or {}).get(ref[1], []) or [])
    return len(art.get(ref) or [])


# ---------------------------------------------------------------------------
# 1.1 Linha de base (hash)
# ---------------------------------------------------------------------------
hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(DADOS.iterdir()) if p.is_file()}

# ---------------------------------------------------------------------------
# 1.2 Cobertura do lote
# ---------------------------------------------------------------------------
manifesto = json.loads((DADOS / "_lote_manifest.json").read_text(encoding="utf-8"))
checar(len(manifesto) == 45, "manifesto tem 45 entradas", len(manifesto))
chaves = [tuple(k.split("|")) for k in manifesto]
esperadas = {(str(c), m, "1") for c in range(1, 10) for m in ORDEM} | \
            {(str(c), m, str(r)) for c in (6, 7, 8) for m in ORDEM for r in (2, 3)}
checar(set(chaves) == esperadas, "manifesto = 27 base + 18 repetições (cenários 6, 7, 8)")
checar(all(v["status"] == "ok" for v in manifesto.values()), "todas as execuções com status ok")
checar(all(v["tinha_gabarito_ragas"] and v["tinha_gabarito_rfrnf"] for v in manifesto.values()),
       "todas as execuções tinham os dois gabaritos")

ragas = pd.read_csv(DADOS / "resultados_ragas.csv", encoding="utf-8-sig")
classif = pd.read_csv(DADOS / "resultados_classificacao.csv", encoding="utf-8-sig")
qual = pd.read_csv(DADOS / "resultados_qualidade.csv", encoding="utf-8-sig")
reps = pd.read_csv(DADOS / "resultados_repeticoes.csv", encoding="utf-8-sig")
cb = pd.read_csv(DADOS / "resultados_custo_beneficio.csv", encoding="utf-8-sig")

arquivos = {v["arquivo_ragas"]: k for k, v in manifesto.items()}
for nome, t in (("ragas", ragas), ("classificacao", classif), ("qualidade", qual)):
    checar(len(t) == 45 and t["arquivo"].is_unique, f"resultados_{nome}.csv: 45 linhas únicas")
    checar(set(t["arquivo"]) == set(arquivos), f"resultados_{nome}.csv: mesmos arquivos do manifesto")

execs = {}
for arq_ragas, chave in arquivos.items():
    base = arq_ragas[len("ragas_"):-len(".json")]
    for pref, ext in (("ragas_", ".json"), ("execucao_", ".csv"), ("SRS_", ".docx")):
        checar((DADOS / f"{pref}{base}{ext}").exists(), f"existe {pref}{base}{ext}")
    execs[arq_ragas] = pd.read_csv(DADOS / f"execucao_{base}.csv", encoding="utf-8-sig").iloc[0].to_dict()

# ---------------------------------------------------------------------------
# 1.3 Faixas válidas
# ---------------------------------------------------------------------------
for c in ("faithfulness", "answer_relevancy", "context_precision", "context_recall", "rag_score"):
    checar(ragas[c].between(0, 1).all() and ragas[c].notna().all(), f"ragas.{c} em [0,1] sem NaN")
for c in [c for c in classif.columns if c.endswith(("_precision", "_recall", "_f1"))]:
    checar(classif[c].between(0, 1).all() and classif[c].notna().all(), f"classif.{c} em [0,1] sem NaN")
for c in ("correctness", "completeness", "conciseness"):
    checar(qual[c].isin([1, 2, 3, 4, 5]).all(), f"qualidade.{c} inteiro 1–5")

# ---------------------------------------------------------------------------
# 1.4–1.6 Execução, RAGAS e classificação contra as fontes brutas
# ---------------------------------------------------------------------------
div_custo, div_contagem, div_classif = [], [], []
linhas = []
for arq_ragas, chave in arquivos.items():
    cen, mod, rep = chave.split("|")
    e = execs[arq_ragas]
    j = json.loads((DADOS / arq_ragas).read_text(encoding="utf-8"))
    modelo = e["modelo"]

    # tokens e custo (fórmula de calcular_custo_usd em main.py)
    p = PRECOS_USD[modelo]
    c_in = ((e["tokens_input"] - e["tokens_cached"]) * p["input"] + e["tokens_cached"] * p["cached_input"]) / 1e6
    c_out = e["tokens_output"] * p["output"] / 1e6
    c_bus = e["file_search_chamadas"] * PRECO_BUSCA / 1000
    total = round(c_in + c_out + c_bus, 6)
    if abs(total - e["custo_total_usd"]) > 2e-6 or e["tokens_total"] != e["tokens_input"] + e["tokens_output"]:
        div_custo.append((arq_ragas, total, e["custo_total_usd"]))

    # manifesto x execucao x ragas
    r = ragas[ragas["arquivo"] == arq_ragas].iloc[0]
    m = manifesto[chave]
    checar(abs(m["rag_score"] - e["rag_score"]) < 1e-4 and abs(r["rag_score"] - e["rag_score"]) < 1e-4,
           f"rag_score igual no manifesto/execução/ragas ({arq_ragas})")
    checar(abs(m["custo_usd"] - e["custo_total_usd"]) < 1e-6, f"custo igual manifesto/execução ({arq_ragas})")
    checar(r["n_contextos"] == len(j["contexts"]), f"n_contextos = contextos no JSON ({arq_ragas})")
    checar(j["modelo"] == modelo, f"modelo igual JSON/execução ({arq_ragas})")

    art = j["artefatos"]
    for col, cat in (("total_rfs", "rf"), ("total_rnfs", "rnf"), ("total_hus", "hu"), ("total_cas", "ca")):
        if e[col] != tamanho(art, cat):
            div_contagem.append((arq_ragas, col, e[col], tamanho(art, cat)))

    # classificação: TP+FN = esperados, TP+FP = gerados, P/R/F1 coerentes
    k = classif[classif["arquivo"] == arq_ragas].iloc[0]
    gab = j["gabarito_artefatos"]
    stp = sfp = sfn = 0
    for cat in CATS:
        tp, fp, fn = int(k[f"{cat}_tp"]), int(k[f"{cat}_fp"]), int(k[f"{cat}_fn"])
        stp, sfp, sfn = stp + tp, sfp + fp, sfn + fn
        if tp + fn != tamanho(gab, cat) or tp + fp != tamanho(art, cat):
            div_classif.append((arq_ragas, cat, "contagem", tp + fn, tamanho(gab, cat), tp + fp, tamanho(art, cat)))
        pr = tp / (tp + fp) if tp + fp else 0
        rc = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0
        for nome, v in (("precision", pr), ("recall", rc), ("f1", f1)):
            if abs(k[f"{cat}_{nome}"] - v) > 6e-5:
                div_classif.append((arq_ragas, cat, nome, k[f"{cat}_{nome}"], round(v, 4)))
    if (stp, sfp, sfn) != (k["geral_tp"], k["geral_fp"], k["geral_fn"]):
        div_classif.append((arq_ragas, "geral", "soma", (stp, sfp, sfn)))

    q = qual[qual["arquivo"] == arq_ragas].iloc[0]
    linhas.append({
        "arquivo": arq_ragas, "cenario": int(cen), "nome": NOMES[int(cen)], "modelo": mod, "rep": int(rep),
        "idioma": None, "sistema": e["sistema"],
        **{c: r[c] for c in ("faithfulness", "answer_relevancy", "context_precision", "context_recall", "rag_score", "n_contextos")},
        **{c: k[c] for c in classif.columns if c.endswith(("_tp", "_fp", "_fn", "_precision", "_recall", "_f1"))},
        "correctness": q["correctness"], "completeness": q["completeness"], "conciseness": q["conciseness"],
        "custo_usd": e["custo_total_usd"], "tempo_s": e["tempo_execucao_s"], "tokens_total": e["tokens_total"],
        "tokens_input": e["tokens_input"], "tokens_output": e["tokens_output"], "tokens_reasoning": e["tokens_reasoning"],
        "tokens_cached": e["tokens_cached"], "file_search_chamadas": e["file_search_chamadas"],
        "total_rfs": e["total_rfs"], "total_rnfs": e["total_rnfs"], "total_hus": e["total_hus"], "total_cas": e["total_cas"],
    })

checar(not div_custo, "custo e tokens_total recalculados batem com execucao_*.csv", div_custo[:5])
checar(not div_contagem, "totais de RF/RNF/HU/CA batem com os artefatos do JSON", div_contagem[:5])
checar(not div_classif, "classificação: contagens e P/R/F1 coerentes com TP/FP/FN e listas", div_classif[:8])

df = pd.DataFrame(linhas)
df["qualidade_media"] = df[["correctness", "completeness", "conciseness"]].mean(axis=1)

# ---------------------------------------------------------------------------
# 1.7 Gabaritos
# ---------------------------------------------------------------------------
gabaritos = {}
for arq in sorted(GAB_RFRNF.glob("gabarito_rfrnf_*.json")):
    n = int(re.search(r"gabarito_rfrnf_(\d+)", arq.name).group(1))
    g = json.loads(arq.read_text(encoding="utf-8"))
    gabaritos[n] = {cat: tamanho(g, cat) for cat in CATS}
    ids = {it["id"] for c in ("requisitos_funcionais", "requisitos_nao_funcionais", "historias_de_usuario") for it in g.get(c, [])}
    refs = [x.strip() for ca in g.get("criterios_de_aceite", []) for x in re.split(r"[/,]", ca.get("rf_hu_ref", ""))]
    checar(all(x in ids for x in refs if x), f"gabarito {n}: rf_hu_ref aponta para RF/RNF/HU existente", [x for x in refs if x not in ids])
checar(len(gabaritos) == 9 and len(list(GAB_RAGAS.glob("gabarito_*.txt"))) == 9, "9 gabaritos de cada formato")
checar(all(g["ca"] == 5 for g in gabaritos.values()), "gabaritos: sempre 5 CAs", {n: g["ca"] for n, g in gabaritos.items()})
checar(all(3 <= g["uc"] <= 5 for g in gabaritos.values()), "gabaritos: 3 a 5 UCs", {n: g["uc"] for n, g in gabaritos.items()})
# o gabarito embutido no JSON de cada execução é o do arquivo do cenário
for _, lin in df.iterrows():
    j = json.loads((DADOS / lin["arquivo"]).read_text(encoding="utf-8"))
    checar({c: tamanho(j["gabarito_artefatos"], c) for c in CATS} == gabaritos[lin["cenario"]],
           f"gabarito embutido = arquivo do cenário {lin['cenario']} ({lin['arquivo']})")

# ---------------------------------------------------------------------------
# 1.8 Recalcular repetições e custo-benefício
# ---------------------------------------------------------------------------
MAPA_REP = {"rag_score": "rag_score", "faithfulness": "faithfulness", "answer_relevancy": "answer_relevancy",
            "context_precision": "context_precision", "context_recall": "context_recall",
            "f1_geral": "geral_f1", "precision_geral": "geral_precision", "recall_geral": "geral_recall",
            "correctness": "correctness", "completeness": "completeness", "conciseness": "conciseness",
            "tempo_s": "tempo_s", "custo_usd": "custo_usd"}
div_rep = []
for _, lin in reps.iterrows():
    s = df[(df["cenario"] == lin["cenario"]) & (df["modelo"] == lin["modelo"])].sort_values("rep")
    v = s[MAPA_REP[lin["metrica"]]].astype(float).to_numpy()
    media, dp = v.mean(), v.std(ddof=0)
    cv = dp / media * 100 if media else 0
    valores = [float(x) for x in str(lin["valores"]).split(";")]
    if (len(v) != lin["n_execucoes"] or not np.allclose(valores, v, atol=6e-5)
            or abs(media - lin["media"]) > 6e-5 or abs(dp - lin["desvio_padrao"]) > 6e-5
            or abs(cv - lin["cv_percentual"]) > 0.051):
        div_rep.append((lin["cenario"], lin["modelo"], lin["metrica"], valores, round(media, 4), round(dp, 4), round(cv, 1)))
checar(len(reps) == 117, "resultados_repeticoes.csv tem 117 linhas (9 combinações × 13 métricas)", len(reps))
checar(not div_rep, "repetições recalculadas (desvio populacional, ddof=0) batem com o CSV", div_rep[:5])
dp_amostral = {(c, m): None for c, m in []}

div_cb = []
for _, lin in cb.iterrows():
    s = df[df["modelo"] == lin["modelo"]]
    calc = {"n_execucoes": len(s), "tokens_medio": s["tokens_total"].mean(), "custo_medio_usd": s["custo_usd"].mean(),
            "tempo_medio_s": s["tempo_s"].mean(), "qualidade_llm_media_1a5": s["qualidade_media"].mean(),
            "f1_geral_medio": s["geral_f1"].mean()}
    calc["qualidade_por_1k_tokens"] = calc["qualidade_llm_media_1a5"] / calc["tokens_medio"] * 1000
    calc["f1_por_1k_tokens"] = calc["f1_geral_medio"] / calc["tokens_medio"] * 1000
    calc["qualidade_por_segundo"] = calc["qualidade_llm_media_1a5"] / calc["tempo_medio_s"]
    calc["f1_por_segundo"] = calc["f1_geral_medio"] / calc["tempo_medio_s"]
    calc["qualidade_por_usd"] = calc["qualidade_llm_media_1a5"] / calc["custo_medio_usd"]
    calc["f1_por_usd"] = calc["f1_geral_medio"] / calc["custo_medio_usd"]
    for c, v in calc.items():
        tol = max(abs(v) * 0.005, 0.0011)  # o CSV guarda valores arredondados
        if abs(v - lin[c]) > tol:
            div_cb.append((lin["modelo"], c, lin[c], round(v, 5)))
checar(not div_cb, "custo-benefício recalculado bate com o CSV (tolerância de arredondamento)", div_cb)

# ---------------------------------------------------------------------------
# Valores canônicos para a camada 2 (texto) e camada 3 (tabelas/figuras)
# ---------------------------------------------------------------------------
def r4(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


V = {}
METRICAS = ["rag_score", "faithfulness", "answer_relevancy", "context_precision", "context_recall",
            "geral_precision", "geral_recall", "geral_f1", "correctness", "completeness", "conciseness",
            "qualidade_media", "custo_usd", "tempo_s", "tokens_total", "tokens_input", "tokens_output",
            "tokens_reasoning", "n_contextos", "file_search_chamadas", "total_rfs", "total_rnfs", "total_hus", "total_cas"]
V["geral"] = {m: {"media": r4(df[m].mean()), "dp_amostral": r4(df[m].std()), "min": r4(df[m].min()),
                  "max": r4(df[m].max()), "mediana": r4(df[m].median())} for m in METRICAS}
V["por_modelo"] = {mod: {m: {"media": r4(s[m].mean()), "dp_amostral": r4(s[m].std()), "min": r4(s[m].min()),
                             "max": r4(s[m].max()), "soma": r4(s[m].sum())} for m in METRICAS}
                   for mod, s in df.groupby("modelo")}
V["por_cenario"] = {NOMES[c]: {m: r4(s[m].mean()) for m in METRICAS} for c, s in df.groupby("cenario")}
V["por_cenario_modelo_base"] = {f"{NOMES[c]}|{m}": {k: r4(s[k].mean()) for k in METRICAS}
                                for (c, m), s in df[df["rep"] == 1].groupby(["cenario", "modelo"])}
V["base27_por_modelo"] = {mod: {m: r4(s[m].mean()) for m in METRICAS} for mod, s in df[df["rep"] == 1].groupby("modelo")}


def micro(s, cats=CATS):
    out = {}
    for c in list(cats) + ["geral"]:
        tp, fp, fn = s[f"{c}_tp"].sum(), s[f"{c}_fp"].sum(), s[f"{c}_fn"].sum()
        p, r = tp / (tp + fp), tp / (tp + fn)
        out[c] = {"tp": int(tp), "fp": int(fp), "fn": int(fn), "gerados": int(tp + fp), "esperados": int(tp + fn),
                  "precisao_micro": r4(p), "recall_micro": r4(r), "f1_micro": r4(2 * p * r / (p + r)),
                  "precisao_macro": r4(s[f"{c}_precision"].mean()), "recall_macro": r4(s[f"{c}_recall"].mean()),
                  "f1_macro": r4(s[f"{c}_f1"].mean()), "razao_gerado_esperado": r4((tp + fp) / (tp + fn))}
    return out


V["classificacao_total"] = micro(df)
V["classificacao_por_modelo"] = {mod: micro(s) for mod, s in df.groupby("modelo")}

pt = df["cenario"].isin([1, 5, 7])
V["idioma"] = {"pt_rag": r4(df[pt]["rag_score"].mean()), "en_rag": r4(df[~pt]["rag_score"].mean())}
V["correlacoes"] = {}
for a, b in (("rag_score", "geral_f1"), ("rag_score", "faithfulness"), ("rag_score", "context_recall"),
             ("rag_score", "qualidade_media"), ("rag_score", "context_precision"), ("custo_usd", "geral_f1"),
             ("faithfulness", "geral_f1"), ("geral_precision", "qualidade_media")):
    V["correlacoes"][f"{a}~{b}"] = {"todas": r4(df[a].corr(df[b])),
                                   **{m: r4(s[a].corr(s[b])) for m, s in df.groupby("modelo")}}
V["file_search_distribuicao"] = {int(k): int(v) for k, v in df["file_search_chamadas"].value_counts().items()}
V["outliers"] = {
    "faithfulness_min": df.loc[df["faithfulness"].idxmin(), ["nome", "modelo", "rep", "faithfulness", "n_contextos"]].to_dict(),
    "context_precision_3_menores": df.nsmallest(3, "context_precision")[["nome", "modelo", "rep", "context_precision"]].to_dict("records"),
    "lua_faith_sem_simde": r4(df[(df["modelo"] == "Lua") & ~((df["nome"] == "SIMDE"))]["faithfulness"].mean()),
    "f1_faixa": [r4(df["geral_f1"].min()), r4(df["geral_f1"].max())],
}
V["repeticoes_cv_por_metrica"] = {m: {"min": r4(s["cv_percentual"].min()), "media": r4(s["cv_percentual"].mean()),
                                      "max": r4(s["cv_percentual"].max())} for m, s in reps.groupby("metrica")}
V["repeticoes_cv"] = {f"{r.nome_cenario}|{r.modelo}|{r.metrica}": r.cv_percentual for r in reps.itertuples()}
V["totais"] = {"custo_total": r4(df["custo_usd"].sum()), "tempo_total_s": r4(df["tempo_s"].sum()),
               "n": len(df), "gabaritos": gabaritos}
V["sistema_nomes_por_cenario"] = {NOMES[c]: sorted(s["sistema"].unique()) for c, s in df.groupby("cenario")}
V["hashes"] = hashes

(SAIDA / "valores_recalculados.json").write_text(json.dumps(V, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
df.to_csv(SAIDA / "base_consolidada_45.csv", index=False, encoding="utf-8-sig")

print(f"\n{len(ok)} verificações OK / {len(falhas)} divergências")
for f in falhas:
    print("  ✘", f)
