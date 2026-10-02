# Gera Testes/Execuções Oficiais/RESULTADOS_CONSOLIDADOS.md — todos os resultados das 45 execuções oficiais
# (20/08/2026) num único arquivo de consulta, calculados a partir dos dados oficiais. Somente leitura, não chama a API.
#
# Fontes: base_consolidada_45.csv (gerada por validar_dados.py), resultados_*.csv, _lote_manifest.json, ragas_*.json.
# Uso: python gerar_resultados_consolidados.py

import itertools
import json
import re
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
EXEC = AQUI.parent / "Execuções Oficiais"
SAIDA = EXEC / "RESULTADOS_CONSOLIDADOS.md"

DIF = {"GRD": "Média", "UUIS": "Baixa", "IPG": "Média", "MDT": "Baixa", "SIMDE": "Baixa", "SLCCI": "Alta",
       "SBD Rio": "Média", "BECS": "Baixa", "FFMIA": "Alta"}
MODELOS = ["Lua", "Terra", "Sol"]
TIPOS = [("escopo_em", "Escopo (incluído)"), ("escopo_fora", "Escopo (excluído)"), ("stk", "Stakeholders"),
         ("rn", "Regras de negócio"), ("rf", "Requisitos funcionais"), ("rnf", "Requisitos não funcionais"),
         ("hu", "Histórias de usuário"), ("uc", "Casos de uso"), ("ca", "Critérios de aceite"), ("geral", "Total")]
METRICAS = [("rag_score", "RAG Score"), ("faithfulness", "Faithfulness"), ("answer_relevancy", "Answer relevancy"),
            ("context_precision", "Context precision"), ("context_recall", "Context recall"),
            ("geral_precision", "Precisão (média por execução)"), ("geral_recall", "Recall (média por execução)"),
            ("geral_f1", "F1 (média por execução)"), ("correctness", "Juiz: correção (1–5)"),
            ("completeness", "Juiz: completude (1–5)"), ("conciseness", "Juiz: concisão (1–5)"),
            ("qualidade_media", "Juiz: média das 3 dimensões"), ("tokens_total", "Tokens por execução"),
            ("tempo_s", "Tempo por execução (s)"), ("custo_usd", "Custo por execução (US$)"),
            ("n_contextos", "Trechos recuperados (sem duplicatas)"), ("file_search_chamadas", "Chamadas ao file_search")]

DEC = {"tokens_total": 0, "tempo_s": 1, "n_contextos": 1, "file_search_chamadas": 2, "correctness": 2,
       "completeness": 2, "conciseness": 2, "qualidade_media": 3}


def f(x, c=3):
    if isinstance(x, str):
        return x
    if pd.isna(x):
        return "—"
    s = f"{x:,.{c}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def tabela(cab, linhas):
    out = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    out += ["| " + " | ".join(str(c) for c in l) + " |" for l in linhas]
    return "\n".join(out)


def cobertura(q, cs, n=6):
    t = re.findall(r"\w+", q.split("Documento(s) de cen", 1)[1].split("\n", 1)[1].lower())
    g = [tuple(t[i:i + n]) for i in range(len(t) - n + 1)]
    u = set()
    for x in cs:
        w = re.findall(r"\w+", x.lower())
        u |= {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}
    return sum(x in u for x in g) / len(g)


def main():
    b = pd.read_csv(AQUI / "base_consolidada_45.csv", encoding="utf-8-sig")
    b["dif"] = b["nome"].map(DIF)
    b["idioma"] = b["cenario"].map(lambda c: "Português" if c in (1, 5, 7) else "Inglês")
    q = pd.read_csv(EXEC / "resultados_qualidade.csv", encoding="utf-8-sig")
    rep = pd.read_csv(EXEC / "resultados_repeticoes.csv", encoding="utf-8-sig")
    cb = pd.read_csv(EXEC / "resultados_custo_beneficio.csv", encoding="utf-8-sig")
    man = json.loads((EXEC / "_lote_manifest.json").read_text(encoding="utf-8"))

    # contexto do RAGAS: cobertura do cenário e Jaccard entre repetições
    rg = {k: json.loads((EXEC / v["arquivo_ragas"]).read_text(encoding="utf-8")) for k, v in man.items()}
    arq2key = {v["arquivo_ragas"]: k for k, v in man.items()}
    b["cobertura_cenario"] = b["arquivo"].map(lambda a: cobertura(rg[arq2key[a]]["question"], rg[arq2key[a]]["contexts"]))
    jac = {}
    for c in (6, 7, 8):
        for mo in MODELOS:
            s = [set(rg[f"{c}|{mo}|{r}"]["contexts"]) for r in (1, 2, 3)]
            jac[(c, mo)] = [len(x & y) / len(x | y) for x, y in itertools.combinations(s, 2)]

    # dados por execução que não estão na base consolidada: custo/tokens detalhados, todos os artefatos, marcações,
    # glossário (só existe no .docx: o export de avaliação não o inclui) e tamanho dos gabaritos
    import docx
    ext = {}
    for a, k in arq2key.items():
        nome = a[len("ragas_"):-len(".json")]
        e = pd.read_csv(EXEC / f"execucao_{nome}.csv", encoding="utf-8-sig").iloc[0]
        art = rg[k]["artefatos"]
        esc = art.get("escopo", {})
        txt = json.dumps(art, ensure_ascii=False)
        dx = docx.Document(EXEC / f"SRS_{nome}.docx")
        glo = max([len(t.rows) - 1 for t in dx.tables
                   if re.search(r"\bterm", " ".join(c.text for c in t.rows[0].cells), re.I)] or [0])
        ext[a] = dict(data=e.data_execucao, t_in=e.tokens_input, t_cache=e.tokens_cached, t_out=e.tokens_output,
                      t_reas=e.tokens_reasoning, c_in=e.custo_input_usd, c_out=e.custo_output_usd,
                      c_fs=e.custo_file_search_usd, n_stk=len(art.get("stakeholders", [])),
                      n_rn=len(art.get("regras_de_negocio", [])), n_uc=len(art.get("casos_de_uso", [])),
                      n_em=len(esc.get("em_escopo", [])), n_fora=len(esc.get("fora_de_escopo", [])),
                      n_prem=len(esc.get("premissas", [])), n_rest=len(esc.get("restricoes", [])), n_glo=glo,
                      n_inf=txt.count("[INFERIDO]"), n_tbd=txt.count("[TBD]"))
    b = b.join(pd.DataFrame.from_dict(ext, orient="index"), on="arquivo")
    gab = {}
    for k in man:
        c = int(k.split("|")[0])
        if c not in gab:
            g = rg[k]["gabarito_artefatos"]
            gab[c] = [len(g["escopo"]["em_escopo"]), len(g["escopo"]["fora_de_escopo"]), len(g["stakeholders"]),
                      len(g["regras_de_negocio"]), len(g["requisitos_funcionais"]), len(g["requisitos_nao_funcionais"]),
                      len(g["historias_de_usuario"]), len(g["casos_de_uso"]), len(g["criterios_de_aceite"])]

    L = []
    A = L.append
    A("# Resultados consolidados — 45 execuções oficiais\n")
    A("Gerado por `Testes/Validacao/gerar_resultados_consolidados.py` a partir dos dados oficiais "
      "(`base_consolidada_45.csv`, `resultados_*.csv`, `_lote_manifest.json`, `ragas_*.json`). **Não editar à mão** — "
      "rodar o script de novo se os dados mudarem.\n")

    # 1. desenho
    A("## 1. Desenho do experimento\n")
    A("- **Data das execuções:** 20/08/2026, por `Agente/rodar_lote.py`, sem intervenção manual. Execuções anteriores "
      "à correção do bug de ancoragem foram descartadas.")
    A("- **Modelos (gerador):** Lua = gpt-5.6-luna, Terra = gpt-5.6-terra, Sol = gpt-5.6-sol; reasoning effort "
      "medium, verbosity low, saída JSON; tempo-limite 240/360/600 s.")
    A("- **Preços (US$/1M tokens, entrada/cache/saída):** Lua 0,20/0,02/1,20; Terra 2,00/0,20/12,00; Sol "
      "5,00/0,50/30,00; + US$ 2,50 por mil chamadas ao file_search.")
    A("- **Desenho:** 9 cenários × 3 modelos × 1 execução (27, rep = 1) + 3 cenários (SLCCI = alta, SBD Rio = média, "
      "BECS = baixa) × 3 modelos × 2 execuções extras (18) = **45**.")
    A("- **Avaliador (todas as fases):** gpt-5-mini; embeddings text-embedding-3-small (só na answer relevancy). "
      "RAGAS 0.4.3.")
    A("- **Gabaritos:** RAGAS — 137 afirmações (12 a 23 por cenário); RFRNF — JSON com o núcleo essencial "
      "(5 CAs e 3–5 UCs por cenário). Glossário, premissas e restrições fora da classificação.")
    A(f"- **Resultado operacional:** {len(b)} execuções concluídas, **0 falhas**; 1 erro transitório de sobrecarga "
      "(execução 28/45, SBD Rio/Terra) resolvido pelo retry automático. Todas as 45 têm os dois gabaritos.\n")

    # 2. totais
    A("## 2. Totais\n")
    A(tabela(["Item", "Valor"], [
        ["Custo total de geração", "US$ " + f(b["custo_usd"].sum(), 2)],
        ["Custo por modelo (total)", " · ".join(f"{m} US$ {f(b[b.modelo == m]['custo_usd'].sum(), 2)}" for m in MODELOS)],
        ["Janela das execuções", f"{b['data'].min()[11:16]} a {b['data'].max()[11:16]} de 20/08/2026"],
        ["Tempo total de geração (soma das chamadas)", f"{f(b['tempo_s'].sum() / 60, 1)} min"],
        ["Custo por componente", f"entrada US$ {f(b['c_in'].sum(), 2)} · saída US$ {f(b['c_out'].sum(), 2)} · "
                                 f"file_search US$ {f(b['c_fs'].sum(), 2)}"],
        ["Tokens por componente", f"entrada {f(b['t_in'].sum(), 0)} (cache {f(b['t_cache'].sum(), 0)}, "
                                  f"{f(b['t_cache'].sum() / b['t_in'].sum() * 100, 1)}%) · saída {f(b['t_out'].sum(), 0)} "
                                  f"(raciocínio {f(b['t_reas'].sum(), 0)}, {f(b['t_reas'].sum() / b['t_out'].sum() * 100, 1)}%)"],
        ["Tokens totais", f(b["tokens_total"].sum(), 0)],
        ["Custo das avaliações (gpt-5-mini)", "não medido pelos scripts; ≤ US$ 7,89 pelo saldo da conta"],
        ["Tempo das avaliações", "RAGAS ~4h04; classificação ~1h55; juiz de qualidade ~25–30 min"],
        ["Artefatos gerados (VP + FP)", f(b["geral_tp"].sum() + b["geral_fp"].sum(), 0)],
        ["Artefatos esperados (VP + FN)", f(b["geral_tp"].sum() + b["geral_fn"].sum(), 0)],
    ]))
    A("")

    # 3. geral
    A("## 3. Métricas gerais (45 execuções)\n")
    A("Desvio amostral (n − 1) e populacional (n). O CV entre repetições (Seção 10) usa o populacional.\n")
    A(tabela(["Métrica", "Média", "Desvio amostral", "Desvio pop.", "Mín.", "Máx."],
             [[n, f(b[c].mean(), DEC.get(c, 3)), f(b[c].std(), DEC.get(c, 3)), f(b[c].std(ddof=0), DEC.get(c, 3)),
               f(b[c].min(), DEC.get(c, 3)), f(b[c].max(), DEC.get(c, 3))] for c, n in METRICAS]))
    A("")

    # 4. por modelo
    A("## 4. Por modelo (15 execuções cada)\n")
    A(tabela(["Métrica"] + MODELOS + ["Geral"],
             [[n] + [f(b[b.modelo == m][c].mean(), DEC.get(c, 3)) for m in MODELOS] + [f(b[c].mean(), DEC.get(c, 3))] for c, n in METRICAS]))
    A("")
    lin = []
    for m in MODELOS:
        d = b[b.modelo == m]
        lin.append([m, f(d["total_rfs"].mean(), 1), f(d["total_rnfs"].mean(), 1), f(d["total_hus"].mean(), 1),
                    f(d["total_cas"].mean(), 1),
                    f((d["geral_tp"].sum() + d["geral_fp"].sum()) / (d["geral_tp"].sum() + d["geral_fn"].sum()), 2) + "×",
                    f(d["custo_usd"].sum(), 2)])
    A("**Volume gerado por modelo** (médias por execução; razão = itens gerados ÷ esperados, somados):\n")
    A(tabela(["Modelo", "RF", "RNF", "HU", "CA", "Razão gerado/esperado", "Custo total (US$)"], lin))
    A("")
    cols_art = [("n_em", "Escopo incl."), ("n_fora", "Escopo excl."), ("n_prem", "Premissas"), ("n_rest", "Restrições"),
                ("n_stk", "Stakeholders"), ("n_rn", "RN"), ("total_rfs", "RF"), ("total_rnfs", "RNF"), ("total_hus", "HU"),
                ("n_uc", "UC"), ("total_cas", "CA"), ("n_glo", "Glossário (termos)"), ("n_inf", "[INFERIDO]"),
                ("n_tbd", "[TBD]")]
    A("**Todos os artefatos gerados** (média por execução; glossário contado no .docx, pois não vai para a avaliação):\n")
    A(tabela(["Item"] + MODELOS + ["Geral", "Mín.", "Máx."],
             [[n] + [f(b[b.modelo == m][c].mean(), 1) for m in MODELOS] + [f(b[c].mean(), 1), f(b[c].min(), 0),
                                                                           f(b[c].max(), 0)] for c, n in cols_art]))
    A(f"\nTodas as 45 execuções têm todos os tipos de artefato, inclusive glossário. [TBD] aparece em "
      f"{int((b.n_tbd > 0).sum())} execuções ({f(b.n_tbd.sum(), 0)} no total); [INFERIDO] em {int((b.n_inf > 0).sum())} "
      f"({f(b.n_inf.sum(), 0)} no total). Contagem só nos artefatos exportados (sem resumo e glossário).\n")
    A("**Tokens e custo por componente** (média por execução):\n")
    A(tabela(["Modelo", "Entrada", "Em cache", "Saída", "Raciocínio", "Custo entrada", "Custo saída", "Custo file_search"],
             [[m] + [f(b[b.modelo == m][c].mean(), 0) for c in ("t_in", "t_cache", "t_out", "t_reas")]
              + [f(b[b.modelo == m][c].mean(), 4) for c in ("c_in", "c_out", "c_fs")] for m in MODELOS]))
    A("")
    A("**Custo-benefício** (`resultados_custo_beneficio.csv`; nota do juiz = média das 3 dimensões):\n")
    A(tabela(["Modelo", "Custo médio", "Tempo médio (s)", "Nota juiz", "F1", "Nota/US$", "F1/US$", "Nota/1k tok",
              "F1/1k tok", "Nota/s", "F1/s"],
             [[r.modelo, f(r.custo_medio_usd, 4), f(r.tempo_medio_s, 1), f(r.qualidade_llm_media_1a5), f(r.f1_geral_medio),
               f(r.qualidade_por_usd, 1), f(r.f1_por_usd, 1), f(r.qualidade_por_1k_tokens, 4), f(r.f1_por_1k_tokens, 4),
               f(r.qualidade_por_segundo, 4), f(r.f1_por_segundo, 4)] for r in cb.itertuples()]))
    A(f"\nSol/Lua: custo {f(b[b.modelo == 'Sol'].custo_usd.mean() / b[b.modelo == 'Lua'].custo_usd.mean(), 1)}×; "
      f"Sol/Terra {f(b[b.modelo == 'Sol'].custo_usd.mean() / b[b.modelo == 'Terra'].custo_usd.mean(), 1)}×; "
      f"Terra/Lua {f(b[b.modelo == 'Terra'].custo_usd.mean() / b[b.modelo == 'Lua'].custo_usd.mean(), 1)}×. "
      "Terra usa menos tokens que Lua e custa mais: a diferença de custo vem do preço por token.\n")

    # 5. classificação por tipo
    A("## 5. Classificação por tipo de artefato (agregação micro: soma de VP/FP/FN)\n")

    def micro(d):
        rows = []
        for k, n in TIPOS:
            tp, fp, fn = d[f"{k}_tp"].sum(), d[f"{k}_fp"].sum(), d[f"{k}_fn"].sum()
            p, r = tp / (tp + fp), tp / (tp + fn)
            rows.append([n, f(tp, 0), f(fp, 0), f(fn, 0), f(p), f(r), f(2 * p * r / (p + r))])
        return rows
    A("**Todas as 45:**\n")
    A(tabela(["Tipo", "VP", "FP", "FN", "Precisão", "Recall", "F1"], micro(b)))
    for m in MODELOS:
        A(f"\n**{m}:**\n")
        A(tabela(["Tipo", "VP", "FP", "FN", "Precisão", "Recall", "F1"], micro(b[b.modelo == m])))
    A(f"\nRecall > precisão em **{int((b.geral_recall > b.geral_precision).sum())} das 45** execuções. "
      f"F1 geral por execução de {f(b.geral_f1.min())} a {f(b.geral_f1.max())}. "
      f"CA: precisão macro (média por execução) {f(b.ca_precision.mean())} × micro "
      f"{f(b.ca_tp.sum() / (b.ca_tp.sum() + b.ca_fp.sum()))}.\n")

    A("\n**Tamanho dos gabaritos estruturados (itens esperados por execução de cada cenário):**\n")
    nomes = {c: b[b.cenario == c].nome.iloc[0] for c in range(1, 10)}
    A(tabela(["Cenário", "Escopo incl.", "Escopo excl.", "Stakeholders", "RN", "RF", "RNF", "HU", "UC", "CA", "Total"],
             [[f"{c} {nomes[c]}"] + gab[c] + [sum(gab[c])] for c in range(1, 10)]))
    A(f"\nTotal: {sum(sum(v) for v in gab.values())} itens nos 9 gabaritos. Pontos fracos do gabarito: MDT tem 1 "
      "stakeholder; BECS tem 1 RNF; CA é sempre 5 — afeta a precisão desses tipos.\n")

    # 6. por cenário
    A("## 6. Por cenário\n")
    b27 = b[b.rep == 1]
    A("**Média dos 3 modelos, só as 27 execuções-base (rep = 1):**\n")
    cols = ["rag_score", "faithfulness", "answer_relevancy", "context_precision", "context_recall", "geral_precision",
            "geral_recall", "geral_f1", "correctness", "completeness", "conciseness", "custo_usd", "tempo_s"]
    lin = []
    for c in range(1, 10):
        d = b27[b27.cenario == c]
        lin.append([f"{c} {d.nome.iloc[0]}", d.dif.iloc[0], d.idioma.iloc[0]] + [f(d[x].mean(), {"tempo_s": 1, "correctness": 2, "completeness": 2, "conciseness": 2}.get(x, 3)) for x in cols])
    A(tabela(["Cenário", "Dific.", "Idioma", "RAG", "Faith", "AR", "CP", "CR", "P", "R", "F1", "Corr", "Compl", "Conc",
              "Custo", "Tempo"], lin))
    A("\n**F1 por cenário × modelo (rep = 1):**\n")
    lin = []
    for c in range(1, 10):
        d = b27[b27.cenario == c]
        lin.append([f"{c} {d.nome.iloc[0]}"] + [f(d[d.modelo == m].geral_f1.iloc[0]) for m in MODELOS])
    A(tabela(["Cenário"] + MODELOS, lin))
    A("\n**Por dificuldade e por idioma (rep = 1):**\n")
    lin = [[g, f(len(d) / 3, 0)] + [f(d[x].mean()) for x in ["geral_f1", "geral_precision", "geral_recall", "faithfulness",
                                                               "context_recall", "rag_score", "correctness", "qualidade_media"]]
           for g, d in list(b27.groupby("dif")) + list(b27.groupby("idioma"))]
    A(tabela(["Grupo", "Cenários", "F1", "P", "R", "Faith", "CR", "RAG", "Correção", "Nota juiz"], lin))
    A("\nSem gradiente pela dificuldade atribuída (alta teve o maior F1). Correção do juiz menor em inglês "
      "(penalidade por must/shall — Seção 8).\n")

    # 7. recuperação
    A("## 7. Recuperação e contexto do RAGAS\n")
    fs = b.file_search_chamadas.value_counts().sort_index()
    A(f"- **Chamadas ao file_search:** média {f(b.file_search_chamadas.mean(), 2)}; distribuição "
      + ", ".join(f"{int(k)} chamada(s): {v} execuções" for k, v in fs.items())
      + ". Cada chamada pode ter várias consultas (não registradas) — não concluir que o modelo ignorou o checklist.")
    A(f"- **Trechos por execução (sem duplicatas):** média {f(b.n_contextos.mean(), 1)} "
      f"(mín. {int(b.n_contextos.min())}, máx. {int(b.n_contextos.max())}).")
    cv = b.cobertura_cenario
    A(f"- **Cobertura do cenário no contexto** (sequências de 6 palavras): ≥ 98% em **{int((cv >= 0.98).sum())}/45**; "
      f"entre 50% e 98% em {int(((cv >= 0.5) & (cv < 0.98)).sum())}; < 50% em {int((cv < 0.5).sum())} (MDT/Lua, 0%). "
      "O cenário (< 1.100 tokens) cabe em 1–2 chunks de 800 tokens.")
    A(f"- **Jaccard dos trechos entre repetições:** média {f(sum(sum(v) for v in jac.values()) / 27 * 100, 1)}% "
      f"(mín. {f(min(min(v) for v in jac.values()) * 100, 1)}%, máx. {f(max(max(v) for v in jac.values()) * 100, 1)}%).")
    A("- **RAG Score:** média dos escores de relevância (0–1) do file_search; o fornecedor não publica o cálculo.\n")
    A(tabela(["Combinação", "Jaccard pares (1–2, 1–3, 2–3)", "Média"],
             [[f"{b[b.cenario == c].nome.iloc[0]}/{m}", " · ".join(f(x * 100, 1) + "%" for x in v),
               f(sum(v) / 3 * 100, 1) + "%"] for (c, m), v in jac.items()]))
    A("")

    # 8. juiz
    A("## 8. Juiz de qualidade (LLM-as-judge)\n")
    A(tabela(["Dimensão", "Nota 3", "Nota 4", "Nota 5"],
             [[n, *(int((q[c] == v).sum()) for v in (3, 4, 5))]
              for c, n in [("correctness", "Correção"), ("completeness", "Completude"), ("conciseness", "Concisão")]]))
    s = q["correctness_justificativa"].fillna("")
    en = ~q["arquivo"].str.contains("GRD|SIMDE|Bilhetagem", regex=True)
    ms = s.str.contains(r"\bmust\b|\bshall\b", case=False, regex=True)
    A(f"\n- Justificativas de correção que citam must/shall: **{int((ms & en).sum())} dos {int(en.sum())}** docs em inglês "
      "(a rubrica e o prompt exigem \"deve\" — viés do método, não erro do documento).")
    A(f"- Justificativas que citam [TBD]: correção {int(s.str.contains('TBD').sum())}, concisão "
      f"{int(q['conciseness_justificativa'].fillna('').str.contains('TBD').sum())}.")
    A("- Concisão ≈ 4 em quase todas (44/45), inclusive no Sol, que gerou 2,17× o esperado: o juiz não captou o excesso "
      "(compatível com o viés de verbosidade de Zheng et al.).")
    A("- Rastreabilidade estrutural: 726/726 HUs, 420/420 UCs, 933/933 CAs e 690 RFs com RN "
      "referenciam IDs existentes; 28/726 HUs repetem o conector no .docx (\"As a As a\").")
    A("- Teste do juiz da classificação antes do lote: mesma lista de 9 itens → 4, 6 e 8 correspondências.\n")

    # 9. correlações
    A("## 9. Correlações (Pearson, 45 execuções; entre parênteses: dentro de Lua / Terra / Sol)\n")

    def corr(x, y):
        return f(b[x].corr(b[y]), 2) + " (" + " / ".join(f(b[b.modelo == m][x].corr(b[b.modelo == m][y]), 2) for m in MODELOS) + ")"
    A(tabela(["Par", "r"], [[f"{x} × {y}", corr(x, y)] for x, y in [
        ("rag_score", "geral_f1"), ("rag_score", "faithfulness"), ("rag_score", "context_recall"),
        ("rag_score", "context_precision"), ("rag_score", "qualidade_media"), ("custo_usd", "geral_f1"),
        ("faithfulness", "geral_f1"), ("geral_precision", "qualidade_media"), ("tokens_total", "geral_f1")]]))
    A("")

    # 10. repetições
    A("## 10. Estabilidade entre repetições (CV = desvio populacional ÷ média, 9 combinações × 3 execuções)\n")
    lin = []
    for mt, d in rep.groupby("metrica", sort=False):
        lin.append([mt, f(d.cv_percentual.min(), 1), f(d.cv_percentual.mean(), 1), f(d.cv_percentual.max(), 1),
                    f"{d.loc[d.cv_percentual.idxmax(), 'nome_cenario']}/{d.loc[d.cv_percentual.idxmax(), 'modelo']}"])
    A(tabela(["Métrica", "CV mín. %", "CV médio %", "CV máx. %", "Combinação do máx."], lin))
    A("\n**Valores das 3 repetições por combinação:**\n")
    lin = [[f"{r.nome_cenario}/{r.modelo}", r.metrica, r.valores, f(r.media, 4), f(r.cv_percentual, 1)]
           for r in rep.itertuples()]
    A(tabela(["Combinação", "Métrica", "Valores (rep 1; 2; 3)", "Média", "CV %"], lin))
    A("\n- Nome do sistema extraído pelo modelo: mudou entre repetições só em **SLCCI/Sol** (2 nomes); FFMIA tem nome "
      "diferente no Terra (sem repetição). Agrupar sempre pelo número do cenário.\n")

    # 11. outliers
    A("## 11. Resultados atípicos investigados\n")
    A(tabela(["Execução", "Valor", "Investigação"], [
        ["SIMDE/Lua — faithfulness", "0,250 (Lua sem ela: 0,990)",
         "99% do cenário estava no contexto; afirmações (30 s, 5 s, 3 h, PDA) batem com o cenário → **falha do avaliador**. "
         "Havia 1 trecho contaminante (\"Sistema de Controle de Propostas Comerciais\", exemplo da base) que o modelo não reproduziu."],
        ["MDT/Lua — faithfulness e CR", "0,993 e 0,867 com 0 trecho do cenário (36 trechos)",
         "**Falso alto**: nota alta sem sustentação real no cenário."],
        ["MDT/Lua — context precision", "0,191 (menor das 45)", "Mesmo caso acima: nenhum trecho do cenário."],
        ["SLCCI/Sol rep1 — context precision", "0,241", "Instabilidade da context precision entre repetições."],
        ["BECS/Lua rep1 — context precision", "0,323", "3º menor valor."],
    ]))
    A("")

    # 12. por execução
    A("## 12. Tabela por execução (45)\n")
    lin = []
    for r in b.sort_values(["cenario", "modelo", "rep"]).itertuples():
        lin.append([f"{r.cenario} {r.nome}", r.modelo, r.rep, f(r.rag_score), f(r.faithfulness), f(r.answer_relevancy),
                    f(r.context_precision), f(r.context_recall), f(r.geral_precision), f(r.geral_recall), f(r.geral_f1),
                    f"{int(r.correctness)}/{int(r.completeness)}/{int(r.conciseness)}", f(r.custo_usd, 4), f(r.tempo_s, 1),
                    f(r.tokens_total, 0), int(r.file_search_chamadas), int(r.n_contextos), f(r.cobertura_cenario * 100, 0) + "%",
                    r.sistema])
    A(tabela(["Cenário", "Modelo", "Rep", "RAG", "Faith", "AR", "CP", "CR", "P", "R", "F1", "Juiz C/Cp/Cc", "Custo",
              "Tempo", "Tokens", "FS", "Trechos", "Cobert.", "Nome do sistema extraído"], lin))
    A("")

    # 13. síntese qualitativa
    A("## 13. Síntese: o que foi bom e o que foi ruim\n")
    A("**Resultados positivos**")
    A("- 45/45 execuções concluídas, todas com todos os tipos de artefato; 0 falhas (1 retry automático).")
    A("- Faithfulness média 0,969 (≥ 0,94 em todos os modelos; 0,990 no Lua sem o caso SIMDE).")
    A("- Recall alto: 0,891 micro / 0,892 por execução — o protótipo cobre quase tudo o que o gabarito espera; "
      "stakeholders 0,970, RF 0,935, UC 0,931, HU 0,929.")
    A("- Rastreabilidade estrutural 100% (HU, UC, CA e RF com RN); todas as 45 com todos os tipos de artefato, "
      "inclusive glossário (6 a 17 termos).")
    A("- Juiz: completude 4,84; desempenho homogêneo entre cenários (F1 0,598–0,667), dificuldades e idiomas.")
    A("- Lua: nota do juiz equivalente (4,24 × 4,31 do Sol) a ~1/25 do custo — melhor custo-benefício; Terra: maior F1 (0,688).")
    A("- Estabilidade alta em faithfulness (CV 1,1%), recall da classificação (2,0%), context recall (3,1%), custo e tempo.\n")
    A("**Resultados negativos ou fracos**")
    A("- Precisão baixa: 0,490 micro — 51% do gerado sem correspondente; pior em CA (0,211: 736 FP × 197 VP), UC (0,386), "
      "RNF (0,394), HU (0,430). Parte é desenho do gabarito (núcleo essencial) e granularidade do um-para-um.")
    A("- Excesso de artefatos: 1,51× (Terra) a 2,17× (Sol) o esperado; o modelo mais caro gerou mais e teve o menor F1 (0,585).")
    A("- Regras de negócio com o menor recall (0,718) — regras implícitas nem sempre identificadas.")
    A("- Answer relevancy baixa (0,408) — efeito da adaptação da métrica (pergunta = instrução + cenário inteiro).")
    A("- Context precision instável (CV médio 17,1%, máx. 28,3%) e RAG Score instável no Sol (até 21,3%); Jaccard 33%.")
    A("- RAG Score não acompanha a qualidade (r = −0,53 com F1; ~0 com faithfulness e com o juiz).")
    A("- Correção do juiz 3,93 (a menor nota), em parte por viés do método (\"deve\" exigido em docs em inglês).")
    A("- Sol: 25× o custo do Lua e 2× o tempo, sem ganho de F1.\n")
    A("**Limitações do método reveladas pelos dados**")
    A("- Avaliadores LLM falham nos dois sentidos (SIMDE/Lua falso baixo; MDT/Lua falso alto) e variam (4/6/8 em 9 itens).")
    A("- O juiz de qualidade não penaliza volume; rubrica e prompt em português penalizam docs em inglês.")
    A("- Sem condição sem RAG, sem testes de significância, sem amostragem humana, data única.")
    A("- Contaminação na recuperação (trecho de exemplo da base no contexto do SIMDE) — a instrução anticontaminação "
      "atua na geração, não na recuperação.\n")

    SAIDA.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"gravado: {SAIDA} ({len(L)} linhas)")


if __name__ == "__main__":
    main()
