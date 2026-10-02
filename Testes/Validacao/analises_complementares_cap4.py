# Análises complementares do cap. 4 (revisão de 2026-10-02, v28). Somente leitura, não chama a API.
# Grava analises_cap4.json, lido pelo registro_afirmacoes.py.
#
# 1. Context precision × posição do 1º trecho do cenário na ordem retornada pelo file_search
#    (trecho "do cenário" = ao menos metade das suas sequências de 6 palavras está no texto do cenário).
# 2. Requisitos não funcionais: métrica de aceitação com número e com [TBD]; verbo de obrigação nos RF.
# 3. Distribuição das notas do juiz.
# 4. Ordem dos modelos no F1 por cenário (rep = 1) e sobreposição das faixas das repetições.
# 5. Jaccard dos trechos por modelo; CV da faithfulness do Sol; custo máximo; faithfulness × F1.
#
# Uso: python analises_complementares_cap4.py

import itertools
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).parent
EXEC = AQUI.parents[0] / "Execuções Oficiais"
df = pd.read_csv(AQUI / "base_consolidada_45.csv", encoding="utf-8-sig")
man = json.loads((EXEC / "_lote_manifest.json").read_text(encoding="utf-8"))
PT = {1, 5, 7}
N = 6


def toks(s):
    return re.findall(r"\w+", s.lower())


def grams(t):
    return {tuple(t[i:i + N]) for i in range(len(t) - N + 1)}


R = {}

# 1. Context precision × posição do trecho do cenário
pos, cp, sem_cenario = [], [], []
for k, v in man.items():
    d = json.loads((EXEC / v["arquivo_ragas"]).read_text(encoding="utf-8"))
    g_cen = grams(toks(d["question"].split("Documento(s) de cen", 1)[1].split("\n", 1)[1]))
    p = next((i + 1 for i, c in enumerate(d["contexts"]) if (g := grams(toks(c))) and len(g & g_cen) / len(g) >= 0.5), None)
    linha = df[df["arquivo"] == v["arquivo_ragas"]].iloc[0]
    if p is None:
        sem_cenario.append(k)
        continue
    pos.append(p)
    cp.append(linha["context_precision"])
R["cp_pos_r"] = float(np.corrcoef(cp, pos)[0, 1])
R["cp_pos_n"] = len(pos)
R["cp_pos_mediana"] = float(np.median(pos))
R["cp_sem_cenario"] = sem_cenario

# 1b. Context precision "implícita": precisão média (fórmula do ragas 0.4.3) se só os trechos do cenário
#     fossem julgados úteis; comparação com a real e relação com a posição dentro das combinações repetidas.
imp, real, grupos = [], [], {}
for k, v in man.items():
    d = json.loads((EXEC / v["arquivo_ragas"]).read_text(encoding="utf-8"))
    g_cen = grams(toks(d["question"].split("Documento(s) de cen", 1)[1].split("\n", 1)[1]))
    ver = [1 if (g := grams(toks(c))) and len(g & g_cen) / len(g) >= 0.5 else 0 for c in d["contexts"]]
    ap = sum(sum(ver[:i + 1]) / (i + 1) * ver[i] for i in range(len(ver))) / sum(ver) if sum(ver) else 0.0
    cpk = float(df[df["arquivo"] == v["arquivo_ragas"]].iloc[0]["context_precision"])
    imp.append(ap)
    real.append(cpk)
    c, mo, _ = k.split("|")
    if c in ("6", "7", "8") and 1 in ver:
        grupos.setdefault((c, mo), []).append((ver.index(1) + 1, cpk))
R["cp_implicita_media"] = float(np.mean(imp))
R["cp_real_maior_que_implicita"] = int(sum(r_ > i_ + 0.01 for r_, i_ in zip(real, imp)))
dp, dc = [], []
for lst in grupos.values():
    ps = np.array([x[0] for x in lst], float)
    cs = np.array([x[1] for x in lst])
    dp += list(ps - ps.mean())
    dc += list(cs - cs.mean())
R["cp_pos_r_dentro_combinacoes"] = float(np.corrcoef(dp, dc)[0, 1])

# 2. RNF e RF
rnf = {m: [0, 0, 0] for m in ("Lua", "Terra", "Sol", "Geral")}  # total, métrica com número, métrica com [TBD]
rf = {"total": 0, "pt_deve": 0, "pt_total": 0, "en_must": 0, "en_total": 0}
for k, v in man.items():
    c, mo, _ = k.split("|")
    a = json.loads((EXEC / v["arquivo_ragas"]).read_text(encoding="utf-8"))["artefatos"]
    for r in a["requisitos_nao_funcionais"]:
        met = str(r.get("metrica_aceitacao") or "")
        for chave in (mo, "Geral"):
            rnf[chave][0] += 1
            rnf[chave][1] += bool(re.search(r"\d", met))
            rnf[chave][2] += "[TBD]" in met
    for r in a["requisitos_funcionais"]:
        t = str(r.get("descricao") or "").lower()
        rf["total"] += 1
        if int(c) in PT:
            rf["pt_total"] += 1
            rf["pt_deve"] += bool(re.search(r"\bdeve(m|rá|rão)?\b", t))
        else:
            rf["en_total"] += 1
            rf["en_must"] += bool(re.search(r"\b(must|shall)\b", t))
# documentos de cenários em inglês gerados em português (RF com "deve" e sem must/shall)
q = pd.read_csv(EXEC / "resultados_qualidade.csv", encoding="utf-8-sig").set_index("arquivo")
en_em_pt, ms_en_reais = [], 0
for k, v in man.items():
    if int(k.split("|")[0]) in PT:
        continue
    rfs = [str(r.get("descricao") or "").lower() for r in json.loads((EXEC / v["arquivo_ragas"]).read_text(encoding="utf-8"))["artefatos"]["requisitos_funcionais"]]
    if sum(bool(re.search(r"\bdeve\b", t)) for t in rfs) > len(rfs) / 2:
        en_em_pt.append(k)
    elif re.search(r"\bmust\b|\bshall\b", str(q.loc[v["arquivo_ragas"], "correctness_justificativa"]), re.I):
        ms_en_reais += 1
R["en_em_pt"] = en_em_pt
# RF com verbo de obrigação no idioma em que o documento foi gerado; RNF com categoria ISO e método
ISO = {"Performance Efficiency", "Security", "Reliability", "Compatibility", "Interaction Capability", "Maintainability",
       "Flexibility", "Functional Suitability", "Safety"}
R["rf_verbo_ok"] = R["rnf_iso"] = R["rnf_metodo"] = 0
for k, v in man.items():
    a = json.loads((EXEC / v["arquivo_ragas"]).read_text(encoding="utf-8"))["artefatos"]
    em_pt = int(k.split("|")[0]) in PT or k in en_em_pt
    padrao = r"\bdeve(m)?\b" if em_pt else r"\b(must|shall)\b"
    R["rf_verbo_ok"] += sum(bool(re.search(padrao, str(r.get("descricao") or "").lower())) for r in a["requisitos_funcionais"])
    R["rnf_iso"] += sum(r.get("categoria_iso25010") in ISO for r in a["requisitos_nao_funcionais"])
    R["rnf_metodo"] += sum(bool(str(r.get("metodo_verificacao") or "").strip()) for r in a["requisitos_nao_funcionais"])
R["docs_em_ingles"] = sum(1 for k in man if int(k.split("|")[0]) not in PT) - len(en_em_pt)
R["must_shall_citado_docs_em_ingles"] = ms_en_reais
R["rnf"] = {m: {"total": v[0], "metrica_numero_pct": 100 * v[1] / v[0], "metrica_tbd_pct": 100 * v[2] / v[0]} for m, v in rnf.items()}
R["rf"] = rf

# 3. Distribuição das notas do juiz
R["juiz"] = {col: {int(n): int(q) for n, q in df[col].value_counts().items()} for col in ("correctness", "completeness", "conciseness")}

# 4. Ordem dos modelos por cenário e faixas das repetições
b = df[df["rep"] == 1].pivot_table(index="cenario", columns="modelo", values="geral_f1")
R["terra_maior_f1"] = int((b.idxmax(axis=1) == "Terra").sum())
R["sol_menor_f1"] = int((b.idxmin(axis=1) == "Sol").sum())
R["lua_maior_que_sol"] = int((b["Lua"] > b["Sol"]).sum())
faixas = {(c, mo): (s["geral_f1"].min(), s["geral_f1"].max()) for (c, mo), s in df[df["cenario"].isin([6, 7, 8])].groupby(["cenario", "modelo"])}
sobrepoe = lambda x, y: not (x[1] < y[0] or y[1] < x[0])
R["sol_sem_sobreposicao"] = int(sum(not sobrepoe(faixas[(c, "Sol")], faixas[(c, o)]) for c in (6, 7, 8) for o in ("Lua", "Terra")))
R["lua_terra_sobrepoe"] = int(sum(sobrepoe(faixas[(c, "Lua")], faixas[(c, "Terra")]) for c in (6, 7, 8)))

# 5. Jaccard por modelo, CV da faithfulness do Sol, custo máximo, faithfulness × F1
ctx = {k: set(json.loads((EXEC / v["arquivo_ragas"]).read_text(encoding="utf-8"))["contexts"]) for k, v in man.items()}
jac = {}
for mo in ("Lua", "Terra", "Sol"):
    jac[mo] = [100 * np.mean([len(a & b_) / len(a | b_) for a, b_ in itertools.combinations([ctx[f"{c}|{mo}|{r}"] for r in (1, 2, 3)], 2)])
               for c in (6, 7, 8)]
R["jaccard_min_max"] = {mo: [min(v), max(v)] for mo, v in jac.items()}
cv = lambda s: 100 * s.std(ddof=0) / s.mean()
R["faith_cv_sol"] = [cv(s["faithfulness"]) for _, s in df[(df["modelo"] == "Sol") & df["cenario"].isin([6, 7, 8])].groupby("cenario")]
R["custo_max"] = float(df["custo_usd"].max())
R["faith_f1_r"] = float(df["faithfulness"].corr(df["geral_f1"]))

(AQUI / "analises_cap4.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(R, ensure_ascii=False, indent=2))
