# Resultados consolidados — 45 execuções oficiais

Gerado por `Testes/Validacao/gerar_resultados_consolidados.py` a partir dos dados oficiais (`base_consolidada_45.csv`, `resultados_*.csv`, `_lote_manifest.json`, `ragas_*.json`). **Não editar à mão** — rodar o script de novo se os dados mudarem.

## 1. Desenho do experimento

- **Data das execuções:** 20/08/2026, por `Agente/rodar_lote.py`, sem intervenção manual. Execuções anteriores à correção do bug de ancoragem foram descartadas.
- **Modelos (gerador):** Lua = gpt-5.6-luna, Terra = gpt-5.6-terra, Sol = gpt-5.6-sol; reasoning effort medium, verbosity low, saída JSON; tempo-limite 240/360/600 s.
- **Preços (US$/1M tokens, entrada/cache/saída):** Lua 0,20/0,02/1,20; Terra 2,00/0,20/12,00; Sol 5,00/0,50/30,00; + US$ 2,50 por mil chamadas ao file_search.
- **Desenho:** 9 cenários × 3 modelos × 1 execução (27, rep = 1) + 3 cenários (SLCCI = alta, SBD Rio = média, BECS = baixa) × 3 modelos × 2 execuções extras (18) = **45**.
- **Avaliador (todas as fases):** gpt-5-mini; embeddings text-embedding-3-small (só na answer relevancy). RAGAS 0.4.3.
- **Gabaritos:** RAGAS — 137 afirmações (12 a 23 por cenário); RFRNF — JSON com o núcleo essencial (5 CAs e 3–5 UCs por cenário). Glossário, premissas e restrições fora da classificação.
- **Resultado operacional:** 45 execuções concluídas, **0 falhas**; 1 erro transitório de sobrecarga (execução 28/45, SBD Rio/Terra) resolvido pelo retry automático. Todas as 45 têm os dois gabaritos.

## 2. Totais

| Item | Valor |
|---|---|
| Custo total de geração | US$ 12,04 |
| Custo por modelo (total) | Lua US$ 0,36 · Terra US$ 2,67 · Sol US$ 9,01 |
| Janela das execuções | 08:39 a 10:10 de 20/08/2026 |
| Tempo total de geração (soma das chamadas) | 82,9 min |
| Custo por componente | entrada US$ 3,24 · saída US$ 8,57 · file_search US$ 0,22 |
| Tokens por componente | entrada 1.487.440 (cache 189.395, 12,7%) · saída 531.133 (raciocínio 71.349, 13,4%) |
| Tokens totais | 2.018.573 |
| Custo das avaliações (gpt-5-mini) | não medido pelos scripts; ≤ US$ 7,89 pelo saldo da conta |
| Tempo das avaliações | RAGAS ~4h04; classificação ~1h55; juiz de qualidade ~25–30 min |
| Artefatos gerados (VP + FP) | 4.743 |
| Artefatos esperados (VP + FN) | 2.610 |

## 3. Métricas gerais (45 execuções)

Desvio amostral (n − 1) e populacional (n). O CV entre repetições (Seção 10) usa o populacional.

| Métrica | Média | Desvio amostral | Desvio pop. | Mín. | Máx. |
|---|---|---|---|---|---|
| RAG Score | 0,447 | 0,088 | 0,087 | 0,331 | 0,683 |
| Faithfulness | 0,969 | 0,112 | 0,111 | 0,250 | 1,000 |
| Answer relevancy | 0,408 | 0,087 | 0,086 | 0,261 | 0,601 |
| Context precision | 0,561 | 0,156 | 0,155 | 0,191 | 0,821 |
| Context recall | 0,899 | 0,049 | 0,048 | 0,812 | 1,000 |
| Precisão (média por execução) | 0,501 | 0,073 | 0,072 | 0,360 | 0,655 |
| Recall (média por execução) | 0,892 | 0,051 | 0,051 | 0,727 | 0,984 |
| F1 (média por execução) | 0,638 | 0,059 | 0,058 | 0,517 | 0,770 |
| Juiz: correção (1–5) | 3,93 | 0,45 | 0,44 | 3,00 | 5,00 |
| Juiz: completude (1–5) | 4,84 | 0,37 | 0,36 | 4,00 | 5,00 |
| Juiz: concisão (1–5) | 4,02 | 0,15 | 0,15 | 4,00 | 5,00 |
| Juiz: média das 3 dimensões | 4,267 | 0,220 | 0,218 | 3,667 | 4,667 |
| Tokens por execução | 44.857 | 6.261 | 6.191 | 26.861 | 59.946 |
| Tempo por execução (s) | 110,5 | 38,4 | 38,0 | 69,5 | 202,3 |
| Custo por execução (US$) | 0,267 | 0,248 | 0,245 | 0,017 | 0,702 |
| Trechos recuperados (sem duplicatas) | 29,5 | 4,7 | 4,7 | 20,0 | 38,0 |
| Chamadas ao file_search | 1,96 | 0,37 | 0,36 | 1,00 | 3,00 |

## 4. Por modelo (15 execuções cada)

| Métrica | Lua | Terra | Sol | Geral |
|---|---|---|---|---|
| RAG Score | 0,426 | 0,404 | 0,510 | 0,447 |
| Faithfulness | 0,941 | 0,974 | 0,992 | 0,969 |
| Answer relevancy | 0,421 | 0,373 | 0,432 | 0,408 |
| Context precision | 0,569 | 0,593 | 0,520 | 0,561 |
| Context recall | 0,896 | 0,889 | 0,912 | 0,899 |
| Precisão (média por execução) | 0,503 | 0,572 | 0,428 | 0,501 |
| Recall (média por execução) | 0,887 | 0,863 | 0,926 | 0,892 |
| F1 (média por execução) | 0,641 | 0,688 | 0,585 | 0,638 |
| Juiz: correção (1–5) | 3,93 | 3,87 | 4,00 | 3,93 |
| Juiz: completude (1–5) | 4,80 | 4,80 | 4,93 | 4,84 |
| Juiz: concisão (1–5) | 4,00 | 4,07 | 4,00 | 4,02 |
| Juiz: média das 3 dimensões | 4,244 | 4,244 | 4,311 | 4,267 |
| Tokens por execução | 43.618 | 41.581 | 49.373 | 44.857 |
| Tempo por execução (s) | 80,8 | 90,0 | 160,8 | 110,5 |
| Custo por execução (US$) | 0,024 | 0,178 | 0,601 | 0,267 |
| Trechos recuperados (sem duplicatas) | 29,4 | 29,1 | 30,0 | 29,5 |
| Chamadas ao file_search | 1,93 | 1,87 | 2,07 | 1,96 |

**Volume gerado por modelo** (médias por execução; razão = itens gerados ÷ esperados, somados):

| Modelo | RF | RNF | HU | CA | Razão gerado/esperado | Custo total (US$) |
|---|---|---|---|---|---|---|
| Lua | 19,7 | 8,8 | 13,7 | 20,7 | 1,77× | 0,36 |
| Terra | 17,9 | 6,1 | 14,1 | 17,9 | 1,51× | 2,67 |
| Sol | 24,1 | 11,2 | 20,6 | 23,6 | 2,17× | 9,01 |

**Todos os artefatos gerados** (média por execução; glossário contado no .docx, pois não vai para a avaliação):

| Item | Lua | Terra | Sol | Geral | Mín. | Máx. |
|---|---|---|---|---|---|---|
| Escopo incl. | 12,2 | 8,5 | 12,1 | 10,9 | 6 | 20 |
| Escopo excl. | 4,7 | 3,9 | 5,5 | 4,7 | 2 | 7 |
| Premissas | 3,8 | 3,3 | 4,9 | 4,0 | 3 | 6 |
| Restrições | 4,9 | 4,0 | 6,5 | 5,1 | 3 | 9 |
| Stakeholders | 7,0 | 5,6 | 7,3 | 6,6 | 3 | 11 |
| RN | 6,6 | 6,3 | 9,9 | 7,6 | 3 | 13 |
| RF | 19,7 | 17,9 | 24,1 | 20,6 | 12 | 31 |
| RNF | 8,8 | 6,1 | 11,2 | 8,7 | 4 | 15 |
| HU | 13,7 | 14,1 | 20,6 | 16,1 | 8 | 28 |
| UC | 9,2 | 7,5 | 11,3 | 9,3 | 5 | 17 |
| CA | 20,7 | 17,9 | 23,6 | 20,7 | 12 | 29 |
| Glossário (termos) | 10,5 | 8,1 | 12,9 | 10,5 | 6 | 17 |
| [INFERIDO] | 2,7 | 1,5 | 1,7 | 2,0 | 0 | 9 |
| [TBD] | 6,3 | 9,1 | 17,9 | 11,1 | 0 | 25 |

Todas as 45 execuções têm todos os tipos de artefato, inclusive glossário. [TBD] aparece em 42 execuções (498 no total); [INFERIDO] em 23 (89 no total). Contagem só nos artefatos exportados (sem resumo e glossário).

**Tokens e custo por componente** (média por execução):

| Modelo | Entrada | Em cache | Saída | Raciocínio | Custo entrada | Custo saída | Custo file_search |
|---|---|---|---|---|---|---|---|
| Lua | 32.692 | 4.185 | 10.926 | 961 | 0,0058 | 0,0131 | 0,0048 |
| Terra | 31.801 | 4.256 | 9.779 | 1.316 | 0,0559 | 0,1174 | 0,0047 |
| Sol | 34.669 | 4.185 | 14.704 | 2.479 | 0,1545 | 0,4411 | 0,0052 |

**Custo-benefício** (`resultados_custo_beneficio.csv`; nota do juiz = média das 3 dimensões):

| Modelo | Custo médio | Tempo médio (s) | Nota juiz | F1 | Nota/US$ | F1/US$ | Nota/1k tok | F1/1k tok | Nota/s | F1/s |
|---|---|---|---|---|---|---|---|---|---|---|
| Lua | 0,0237 | 80,8 | 4,244 | 0,641 | 178,9 | 27,0 | 0,0973 | 0,0147 | 0,0526 | 0,0079 |
| Terra | 0,1780 | 90,0 | 4,244 | 0,688 | 23,9 | 3,9 | 0,1021 | 0,0165 | 0,0472 | 0,0076 |
| Sol | 0,6008 | 160,8 | 4,311 | 0,585 | 7,2 | 1,0 | 0,0873 | 0,0118 | 0,0268 | 0,0036 |

Sol/Lua: custo 25,3×; Sol/Terra 3,4×; Terra/Lua 7,5×. Terra usa menos tokens que Lua e custa mais: a diferença de custo vem do preço por token.

## 5. Classificação por tipo de artefato (agregação micro: soma de VP/FP/FN)

**Todas as 45:**

| Tipo | VP | FP | FN | Precisão | Recall | F1 |
|---|---|---|---|---|---|---|
| Escopo (incluído) | 368 | 124 | 64 | 0,748 | 0,852 | 0,797 |
| Escopo (excluído) | 150 | 63 | 15 | 0,704 | 0,909 | 0,794 |
| Stakeholders | 192 | 107 | 6 | 0,642 | 0,970 | 0,773 |
| Regras de negócio | 168 | 175 | 66 | 0,490 | 0,718 | 0,582 |
| Requisitos funcionais | 623 | 303 | 43 | 0,673 | 0,935 | 0,783 |
| Requisitos não funcionais | 154 | 237 | 26 | 0,394 | 0,856 | 0,539 |
| Histórias de usuário | 312 | 414 | 24 | 0,430 | 0,929 | 0,588 |
| Casos de uso | 162 | 258 | 12 | 0,386 | 0,931 | 0,545 |
| Critérios de aceite | 197 | 736 | 28 | 0,211 | 0,876 | 0,340 |
| Total | 2.326 | 2.417 | 284 | 0,490 | 0,891 | 0,633 |

**Lua:**

| Tipo | VP | FP | FN | Precisão | Recall | F1 |
|---|---|---|---|---|---|---|
| Escopo (incluído) | 130 | 53 | 14 | 0,710 | 0,903 | 0,795 |
| Escopo (excluído) | 50 | 21 | 5 | 0,704 | 0,909 | 0,794 |
| Stakeholders | 63 | 42 | 3 | 0,600 | 0,955 | 0,737 |
| Regras de negócio | 49 | 50 | 29 | 0,495 | 0,628 | 0,554 |
| Requisitos funcionais | 208 | 88 | 14 | 0,703 | 0,937 | 0,803 |
| Requisitos não funcionais | 51 | 81 | 9 | 0,386 | 0,850 | 0,531 |
| Histórias de usuário | 102 | 103 | 10 | 0,498 | 0,911 | 0,644 |
| Casos de uso | 53 | 85 | 5 | 0,384 | 0,914 | 0,541 |
| Critérios de aceite | 64 | 247 | 11 | 0,206 | 0,853 | 0,332 |
| Total | 770 | 770 | 100 | 0,500 | 0,885 | 0,639 |

**Terra:**

| Tipo | VP | FP | FN | Precisão | Recall | F1 |
|---|---|---|---|---|---|---|
| Escopo (incluído) | 108 | 19 | 36 | 0,850 | 0,750 | 0,797 |
| Escopo (excluído) | 49 | 10 | 6 | 0,831 | 0,891 | 0,860 |
| Stakeholders | 63 | 21 | 3 | 0,750 | 0,955 | 0,840 |
| Regras de negócio | 57 | 38 | 21 | 0,600 | 0,731 | 0,659 |
| Requisitos funcionais | 200 | 68 | 22 | 0,746 | 0,901 | 0,816 |
| Requisitos não funcionais | 49 | 42 | 11 | 0,538 | 0,817 | 0,649 |
| Histórias de usuário | 103 | 109 | 9 | 0,486 | 0,920 | 0,636 |
| Casos de uso | 55 | 57 | 3 | 0,491 | 0,948 | 0,647 |
| Critérios de aceite | 66 | 202 | 9 | 0,246 | 0,880 | 0,385 |
| Total | 750 | 566 | 120 | 0,570 | 0,862 | 0,686 |

**Sol:**

| Tipo | VP | FP | FN | Precisão | Recall | F1 |
|---|---|---|---|---|---|---|
| Escopo (incluído) | 130 | 52 | 14 | 0,714 | 0,903 | 0,798 |
| Escopo (excluído) | 51 | 32 | 4 | 0,614 | 0,927 | 0,739 |
| Stakeholders | 66 | 44 | 0 | 0,600 | 1,000 | 0,750 |
| Regras de negócio | 62 | 87 | 16 | 0,416 | 0,795 | 0,546 |
| Requisitos funcionais | 215 | 147 | 7 | 0,594 | 0,968 | 0,736 |
| Requisitos não funcionais | 54 | 114 | 6 | 0,321 | 0,900 | 0,474 |
| Histórias de usuário | 107 | 202 | 5 | 0,346 | 0,955 | 0,508 |
| Casos de uso | 54 | 116 | 4 | 0,318 | 0,931 | 0,474 |
| Critérios de aceite | 67 | 287 | 8 | 0,189 | 0,893 | 0,312 |
| Total | 806 | 1.081 | 64 | 0,427 | 0,926 | 0,585 |

Recall > precisão em **45 das 45** execuções. F1 geral por execução de 0,517 a 0,770. CA: precisão macro (média por execução) 0,224 × micro 0,211.


**Tamanho dos gabaritos estruturados (itens esperados por execução de cada cenário):**

| Cenário | Escopo incl. | Escopo excl. | Stakeholders | RN | RF | RNF | HU | UC | CA | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 GRD | 10 | 2 | 7 | 7 | 13 | 4 | 7 | 5 | 5 | 60 |
| 2 UUIS | 11 | 2 | 4 | 7 | 19 | 6 | 10 | 5 | 5 | 69 |
| 3 IPG | 12 | 6 | 4 | 6 | 20 | 4 | 7 | 4 | 5 | 68 |
| 4 MDT | 7 | 5 | 1 | 4 | 9 | 2 | 6 | 3 | 5 | 42 |
| 5 SIMDE | 10 | 3 | 3 | 6 | 14 | 6 | 5 | 3 | 5 | 55 |
| 6 SLCCI | 9 | 3 | 5 | 5 | 13 | 4 | 6 | 4 | 5 | 54 |
| 7 SBD Rio | 10 | 3 | 5 | 5 | 13 | 6 | 7 | 4 | 5 | 58 |
| 8 BECS | 9 | 6 | 4 | 5 | 18 | 1 | 10 | 3 | 5 | 61 |
| 9 FFMIA | 10 | 1 | 5 | 3 | 15 | 5 | 8 | 5 | 5 | 57 |

Total: 524 itens nos 9 gabaritos. Pontos fracos do gabarito: MDT tem 1 stakeholder; BECS tem 1 RNF; CA é sempre 5 — afeta a precisão desses tipos.

## 6. Por cenário

**Média dos 3 modelos, só as 27 execuções-base (rep = 1):**

| Cenário | Dific. | Idioma | RAG | Faith | AR | CP | CR | P | R | F1 | Corr | Compl | Conc | Custo | Tempo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 GRD | Média | Português | 0,434 | 0,992 | 0,350 | 0,773 | 0,900 | 0,495 | 0,911 | 0,639 | 4,67 | 5,00 | 4,00 | 0,279 | 109,9 |
| 2 UUIS | Baixa | Inglês | 0,387 | 0,965 | 0,354 | 0,575 | 0,974 | 0,476 | 0,845 | 0,608 | 4,00 | 5,00 | 4,00 | 0,282 | 112,0 |
| 3 IPG | Média | Inglês | 0,347 | 0,999 | 0,504 | 0,595 | 0,900 | 0,508 | 0,868 | 0,640 | 3,67 | 4,67 | 4,00 | 0,270 | 113,8 |
| 4 MDT | Baixa | Inglês | 0,517 | 0,967 | 0,434 | 0,403 | 0,867 | 0,469 | 0,881 | 0,610 | 3,67 | 4,67 | 4,00 | 0,252 | 99,3 |
| 5 SIMDE | Baixa | Português | 0,470 | 0,750 | 0,385 | 0,685 | 0,963 | 0,484 | 0,788 | 0,598 | 4,00 | 5,00 | 4,00 | 0,266 | 106,1 |
| 6 SLCCI | Alta | Inglês | 0,442 | 0,947 | 0,383 | 0,421 | 0,902 | 0,538 | 0,901 | 0,667 | 4,00 | 5,00 | 4,33 | 0,258 | 106,1 |
| 7 SBD Rio | Média | Português | 0,483 | 0,993 | 0,529 | 0,605 | 0,911 | 0,472 | 0,879 | 0,606 | 4,00 | 4,33 | 4,00 | 0,304 | 123,4 |
| 8 BECS | Baixa | Inglês | 0,426 | 0,994 | 0,379 | 0,479 | 0,854 | 0,481 | 0,885 | 0,621 | 4,33 | 5,00 | 4,00 | 0,278 | 115,0 |
| 9 FFMIA | Alta | Inglês | 0,438 | 0,960 | 0,461 | 0,546 | 0,882 | 0,518 | 0,924 | 0,660 | 3,67 | 5,00 | 4,00 | 0,261 | 120,3 |

**F1 por cenário × modelo (rep = 1):**

| Cenário | Lua | Terra | Sol |
|---|---|---|---|
| 1 GRD | 0,632 | 0,684 | 0,600 |
| 2 UUIS | 0,565 | 0,648 | 0,611 |
| 3 IPG | 0,634 | 0,663 | 0,622 |
| 4 MDT | 0,578 | 0,679 | 0,574 |
| 5 SIMDE | 0,624 | 0,597 | 0,571 |
| 6 SLCCI | 0,690 | 0,740 | 0,571 |
| 7 SBD Rio | 0,607 | 0,695 | 0,517 |
| 8 BECS | 0,619 | 0,662 | 0,582 |
| 9 FFMIA | 0,688 | 0,699 | 0,593 |

**Por dificuldade e por idioma (rep = 1):**

| Grupo | Cenários | F1 | P | R | Faith | CR | RAG | Correção | Nota juiz |
|---|---|---|---|---|---|---|---|---|---|
| Alta | 2 | 0,664 | 0,528 | 0,913 | 0,954 | 0,892 | 0,440 | 3,833 | 4,333 |
| Baixa | 4 | 0,609 | 0,478 | 0,850 | 0,919 | 0,915 | 0,450 | 4,000 | 4,306 |
| Média | 3 | 0,628 | 0,492 | 0,886 | 0,994 | 0,904 | 0,421 | 4,111 | 4,259 |
| Inglês | 6 | 0,634 | 0,498 | 0,884 | 0,972 | 0,897 | 0,426 | 3,889 | 4,278 |
| Português | 3 | 0,614 | 0,484 | 0,859 | 0,911 | 0,925 | 0,462 | 4,222 | 4,333 |

Sem gradiente pela dificuldade atribuída (alta teve o maior F1). Correção do juiz menor em inglês (penalidade por must/shall — Seção 8).

## 7. Recuperação e contexto do RAGAS

- **Chamadas ao file_search:** média 1,96; distribuição 1 chamada(s): 4 execuções, 2 chamada(s): 39 execuções, 3 chamada(s): 2 execuções. Cada chamada pode ter várias consultas (não registradas) — não concluir que o modelo ignorou o checklist.
- **Trechos por execução (sem duplicatas):** média 29,5 (mín. 20, máx. 38).
- **Cobertura do cenário no contexto** (sequências de 6 palavras): ≥ 98% em **39/45**; entre 50% e 98% em 5; < 50% em 1 (MDT/Lua, 0%). O cenário (< 1.100 tokens) cabe em 1–2 chunks de 800 tokens.
- **Jaccard dos trechos entre repetições:** média 33,3% (mín. 9,8%, máx. 60,6%).
- **RAG Score:** média dos escores de relevância (0–1) do file_search; o fornecedor não publica o cálculo.

| Combinação | Jaccard pares (1–2, 1–3, 2–3) | Média |
|---|---|---|
| SLCCI/Lua | 42,2% · 35,0% · 35,1% | 37,5% |
| SLCCI/Terra | 35,9% · 32,7% · 30,0% | 32,9% |
| SLCCI/Sol | 11,3% · 12,2% · 26,1% | 16,5% |
| SBD Rio/Lua | 46,2% · 60,6% · 43,6% | 50,1% |
| SBD Rio/Terra | 17,5% · 44,7% · 20,0% | 27,4% |
| SBD Rio/Sol | 48,7% · 23,4% · 29,7% | 34,0% |
| BECS/Lua | 58,5% · 48,6% · 35,9% | 47,7% |
| BECS/Terra | 32,6% · 50,0% · 34,0% | 38,9% |
| BECS/Sol | 20,0% · 9,8% · 13,7% | 14,5% |

## 8. Juiz de qualidade (LLM-as-judge)

| Dimensão | Nota 3 | Nota 4 | Nota 5 |
|---|---|---|---|
| Correção | 6 | 36 | 3 |
| Completude | 0 | 7 | 38 |
| Concisão | 0 | 44 | 1 |

- Justificativas de correção que citam must/shall: **21 dos 30** docs em inglês (a rubrica e o prompt exigem "deve" — viés do método, não erro do documento).
- Justificativas que citam [TBD]: correção 43, concisão 24.
- Concisão ≈ 4 em quase todas (44/45), inclusive no Sol, que gerou 2,17× o esperado: o juiz não captou o excesso (compatível com o viés de verbosidade de Zheng et al.).
- Rastreabilidade estrutural: 726/726 HUs, 420/420 UCs, 933/933 CAs e 690 RFs com RN referenciam IDs existentes; 28/726 HUs repetem o conector no .docx ("As a As a").
- Teste do juiz da classificação antes do lote: mesma lista de 9 itens → 4, 6 e 8 correspondências.

## 9. Correlações (Pearson, 45 execuções; entre parênteses: dentro de Lua / Terra / Sol)

| Par | r |
|---|---|
| rag_score × geral_f1 | -0,53 (-0,48 / -0,01 / -0,47) |
| rag_score × faithfulness | 0,05 (-0,14 / 0,20 / 0,37) |
| rag_score × context_recall | -0,01 (0,12 / 0,08 / -0,28) |
| rag_score × context_precision | -0,26 (-0,03 / -0,45 / -0,21) |
| rag_score × qualidade_media | 0,16 (-0,16 / 0,31 / 0,10) |
| custo_usd × geral_f1 | -0,56 (-0,47 / -0,52 / -0,73) |
| faithfulness × geral_f1 | -0,04 (0,07 / -0,15 / -0,29) |
| geral_precision × qualidade_media | -0,15 (-0,26 / 0,10 / -0,15) |
| tokens_total × geral_f1 | -0,56 (-0,30 / -0,28 / -0,45) |

## 10. Estabilidade entre repetições (CV = desvio populacional ÷ média, 9 combinações × 3 execuções)

| Métrica | CV mín. % | CV médio % | CV máx. % | Combinação do máx. |
|---|---|---|---|---|
| rag_score | 1,3 | 8,8 | 21,3 | BECS/Sol |
| faithfulness | 0,0 | 1,1 | 4,4 | SLCCI/Terra |
| answer_relevancy | 1,8 | 7,8 | 13,5 | BECS/Lua |
| context_precision | 8,0 | 17,1 | 28,3 | SLCCI/Terra |
| context_recall | 0,0 | 3,1 | 8,7 | BECS/Sol |
| f1_geral | 2,3 | 4,1 | 7,0 | BECS/Lua |
| precision_geral | 2,4 | 5,9 | 10,1 | BECS/Lua |
| recall_geral | 0,9 | 2,0 | 3,4 | BECS/Lua |
| correctness | 0,0 | 5,5 | 12,9 | SBD Rio/Lua |
| completeness | 0,0 | 4,6 | 10,9 | SBD Rio/Lua |
| conciseness | 0,0 | 1,2 | 10,9 | SLCCI/Terra |
| tempo_s | 2,8 | 6,4 | 9,6 | BECS/Terra |
| custo_usd | 3,3 | 7,5 | 14,6 | SLCCI/Lua |

**Valores das 3 repetições por combinação:**

| Combinação | Métrica | Valores (rep 1; 2; 3) | Média | CV % |
|---|---|---|---|---|
| SLCCI/Lua | rag_score | 0.3819; 0.3498; 0.3725 | 0,3681 | 3,7 |
| SLCCI/Lua | faithfulness | 0.9548; 1.0000; 0.9935 | 0,9828 | 2,0 |
| SLCCI/Lua | answer_relevancy | 0.3151; 0.3180; 0.3471 | 0,3267 | 4,4 |
| SLCCI/Lua | context_precision | 0.6795; 0.5853; 0.7080 | 0,6576 | 8,0 |
| SLCCI/Lua | context_recall | 0.8824; 0.8824; 0.8824 | 0,8824 | 0,0 |
| SLCCI/Lua | f1_geral | 0.6901; 0.6452; 0.6944 | 0,6766 | 3,3 |
| SLCCI/Lua | precision_geral | 0.5568; 0.4950; 0.5556 | 0,5358 | 5,4 |
| SLCCI/Lua | recall_geral | 0.9074; 0.9259; 0.9259 | 0,9197 | 0,9 |
| SLCCI/Lua | correctness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| SLCCI/Lua | completeness | 5.0000; 5.0000; 5.0000 | 5,0000 | 0,0 |
| SLCCI/Lua | conciseness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| SLCCI/Lua | tempo_s | 77.5000; 84.6000; 70.5000 | 77,5333 | 7,4 |
| SLCCI/Lua | custo_usd | 0.0233; 0.0238; 0.0169 | 0,0214 | 14,6 |
| SLCCI/Terra | rag_score | 0.4341; 0.3516; 0.3808 | 0,3888 | 8,8 |
| SLCCI/Terra | faithfulness | 0.8966; 0.9932; 0.9787 | 0,9562 | 4,4 |
| SLCCI/Terra | answer_relevancy | 0.3609; 0.3067; 0.2843 | 0,3173 | 10,1 |
| SLCCI/Terra | context_precision | 0.3421; 0.7090; 0.6425 | 0,5645 | 28,3 |
| SLCCI/Terra | context_recall | 0.8824; 0.8824; 0.8824 | 0,8824 | 0,0 |
| SLCCI/Terra | f1_geral | 0.7402; 0.7519; 0.7101 | 0,7341 | 2,4 |
| SLCCI/Terra | precision_geral | 0.6438; 0.6329; 0.5833 | 0,6200 | 4,2 |
| SLCCI/Terra | recall_geral | 0.8704; 0.9259; 0.9074 | 0,9012 | 2,6 |
| SLCCI/Terra | correctness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| SLCCI/Terra | completeness | 5.0000; 5.0000; 4.0000 | 4,6667 | 10,1 |
| SLCCI/Terra | conciseness | 5.0000; 4.0000; 4.0000 | 4,3333 | 10,9 |
| SLCCI/Terra | tempo_s | 80.2000; 69.5000; 86.5000 | 78,7333 | 8,9 |
| SLCCI/Terra | custo_usd | 0.1607; 0.1274; 0.1778 | 0,1553 | 13,5 |
| SLCCI/Sol | rag_score | 0.5092; 0.4396; 0.6416 | 0,5301 | 15,8 |
| SLCCI/Sol | faithfulness | 0.9911; 1.0000; 0.9948 | 0,9953 | 0,4 |
| SLCCI/Sol | answer_relevancy | 0.4745; 0.3976; 0.4801 | 0,4507 | 8,4 |
| SLCCI/Sol | context_precision | 0.2409; 0.4505; 0.3406 | 0,3440 | 24,9 |
| SLCCI/Sol | context_recall | 0.9412; 0.8824; 0.8824 | 0,9020 | 3,1 |
| SLCCI/Sol | f1_geral | 0.5714; 0.5989; 0.6012 | 0,5905 | 2,3 |
| SLCCI/Sol | precision_geral | 0.4132; 0.4309; 0.4370 | 0,4270 | 2,4 |
| SLCCI/Sol | recall_geral | 0.9259; 0.9815; 0.9630 | 0,9568 | 2,4 |
| SLCCI/Sol | correctness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| SLCCI/Sol | completeness | 5.0000; 5.0000; 5.0000 | 5,0000 | 0,0 |
| SLCCI/Sol | conciseness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| SLCCI/Sol | tempo_s | 160.5000; 165.1000; 151.1000 | 158,9000 | 3,7 |
| SLCCI/Sol | custo_usd | 0.5896; 0.5959; 0.5531 | 0,5795 | 3,3 |
| SBD Rio/Lua | rag_score | 0.4659; 0.4542; 0.4732 | 0,4644 | 1,7 |
| SBD Rio/Lua | faithfulness | 1.0000; 1.0000; 1.0000 | 1,0000 | 0,0 |
| SBD Rio/Lua | answer_relevancy | 0.5841; 0.5066; 0.6006 | 0,5638 | 7,3 |
| SBD Rio/Lua | context_precision | 0.6280; 0.8213; 0.7836 | 0,7443 | 11,2 |
| SBD Rio/Lua | context_recall | 1.0000; 0.8125; 0.9167 | 0,9097 | 8,4 |
| SBD Rio/Lua | f1_geral | 0.6071; 0.5930; 0.6842 | 0,6281 | 6,4 |
| SBD Rio/Lua | precision_geral | 0.4636; 0.4474; 0.5532 | 0,4881 | 9,5 |
| SBD Rio/Lua | recall_geral | 0.8793; 0.8793; 0.8966 | 0,8851 | 0,9 |
| SBD Rio/Lua | correctness | 4.0000; 4.0000; 3.0000 | 3,6667 | 12,9 |
| SBD Rio/Lua | completeness | 4.0000; 4.0000; 5.0000 | 4,3333 | 10,9 |
| SBD Rio/Lua | conciseness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| SBD Rio/Lua | tempo_s | 75.6000; 84.7000; 71.9000 | 77,4000 | 6,9 |
| SBD Rio/Lua | custo_usd | 0.0258; 0.0270; 0.0240 | 0,0256 | 4,7 |
| SBD Rio/Terra | rag_score | 0.4647; 0.4464; 0.4603 | 0,4571 | 1,7 |
| SBD Rio/Terra | faithfulness | 0.9786; 0.9948; 0.9865 | 0,9866 | 0,7 |
| SBD Rio/Terra | answer_relevancy | 0.4134; 0.3931; 0.4104 | 0,4056 | 2,2 |
| SBD Rio/Terra | context_precision | 0.5455; 0.6910; 0.5669 | 0,6011 | 10,7 |
| SBD Rio/Terra | context_recall | 0.8667; 0.8667; 0.8667 | 0,8667 | 0,0 |
| SBD Rio/Terra | f1_geral | 0.6950; 0.6531; 0.6400 | 0,6627 | 3,5 |
| SBD Rio/Terra | precision_geral | 0.5904; 0.5393; 0.5217 | 0,5505 | 5,3 |
| SBD Rio/Terra | recall_geral | 0.8448; 0.8276; 0.8276 | 0,8333 | 1,0 |
| SBD Rio/Terra | correctness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| SBD Rio/Terra | completeness | 4.0000; 5.0000; 5.0000 | 4,6667 | 10,1 |
| SBD Rio/Terra | conciseness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| SBD Rio/Terra | tempo_s | 92.2000; 96.7000; 100.6000 | 96,5000 | 3,6 |
| SBD Rio/Terra | custo_usd | 0.1843; 0.1612; 0.1891 | 0,1782 | 6,8 |
| SBD Rio/Sol | rag_score | 0.5195; 0.5927; 0.6460 | 0,5861 | 8,8 |
| SBD Rio/Sol | faithfulness | 1.0000; 0.9956; 1.0000 | 0,9985 | 0,2 |
| SBD Rio/Sol | answer_relevancy | 0.5894; 0.4605; 0.5324 | 0,5274 | 10,0 |
| SBD Rio/Sol | context_precision | 0.6401; 0.6571; 0.4676 | 0,5883 | 14,6 |
| SBD Rio/Sol | context_recall | 0.8667; 0.8667; 1.0000 | 0,9111 | 6,9 |
| SBD Rio/Sol | f1_geral | 0.5171; 0.5596; 0.5381 | 0,5383 | 3,2 |
| SBD Rio/Sol | precision_geral | 0.3605; 0.4000; 0.3813 | 0,3806 | 4,2 |
| SBD Rio/Sol | recall_geral | 0.9138; 0.9310; 0.9138 | 0,9195 | 0,9 |
| SBD Rio/Sol | correctness | 4.0000; 4.0000; 3.0000 | 3,6667 | 12,9 |
| SBD Rio/Sol | completeness | 5.0000; 5.0000; 5.0000 | 5,0000 | 0,0 |
| SBD Rio/Sol | conciseness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| SBD Rio/Sol | tempo_s | 202.3000; 185.6000; 176.1000 | 188,0000 | 5,8 |
| SBD Rio/Sol | custo_usd | 0.7020; 0.6326; 0.6325 | 0,6557 | 5,0 |
| BECS/Lua | rag_score | 0.4148; 0.4028; 0.4143 | 0,4106 | 1,3 |
| BECS/Lua | faithfulness | 1.0000; 1.0000; 0.9947 | 0,9982 | 0,3 |
| BECS/Lua | answer_relevancy | 0.4080; 0.4088; 0.3016 | 0,3728 | 13,5 |
| BECS/Lua | context_precision | 0.3228; 0.3513; 0.5120 | 0,3954 | 21,1 |
| BECS/Lua | context_recall | 0.8750; 0.8750; 0.8750 | 0,8750 | 0,0 |
| BECS/Lua | f1_geral | 0.6190; 0.7226; 0.6328 | 0,6581 | 7,0 |
| BECS/Lua | precision_geral | 0.4860; 0.5957; 0.4828 | 0,5215 | 10,1 |
| BECS/Lua | recall_geral | 0.8525; 0.9180; 0.9180 | 0,8962 | 3,4 |
| BECS/Lua | correctness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| BECS/Lua | completeness | 5.0000; 4.0000; 5.0000 | 4,6667 | 10,1 |
| BECS/Lua | conciseness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| BECS/Lua | tempo_s | 75.0000; 70.0000; 72.5000 | 72,5000 | 2,8 |
| BECS/Lua | custo_usd | 0.0237; 0.0212; 0.0192 | 0,0214 | 8,6 |
| BECS/Terra | rag_score | 0.3805; 0.5033; 0.3458 | 0,4099 | 16,5 |
| BECS/Terra | faithfulness | 0.9939; 1.0000; 0.9788 | 0,9909 | 0,9 |
| BECS/Terra | answer_relevancy | 0.4344; 0.3199; 0.3553 | 0,3699 | 12,9 |
| BECS/Terra | context_precision | 0.5395; 0.4026; 0.5477 | 0,4966 | 13,4 |
| BECS/Terra | context_recall | 0.8750; 0.8750; 0.8667 | 0,8722 | 0,4 |
| BECS/Terra | f1_geral | 0.6625; 0.7703; 0.7200 | 0,7176 | 6,1 |
| BECS/Terra | precision_geral | 0.5354; 0.6552; 0.6067 | 0,5991 | 8,2 |
| BECS/Terra | recall_geral | 0.8689; 0.9344; 0.8852 | 0,8962 | 3,1 |
| BECS/Terra | correctness | 4.0000; 4.0000; 3.0000 | 3,6667 | 12,9 |
| BECS/Terra | completeness | 5.0000; 5.0000; 5.0000 | 5,0000 | 0,0 |
| BECS/Terra | conciseness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| BECS/Terra | tempo_s | 101.2000; 82.0000; 101.3000 | 94,8333 | 9,6 |
| BECS/Terra | custo_usd | 0.1899; 0.1685; 0.1926 | 0,1837 | 5,9 |
| BECS/Sol | rag_score | 0.4832; 0.3707; 0.6273 | 0,4937 | 21,3 |
| BECS/Sol | faithfulness | 0.9871; 1.0000; 1.0000 | 0,9957 | 0,6 |
| BECS/Sol | answer_relevancy | 0.2947; 0.3058; 0.3069 | 0,3025 | 1,8 |
| BECS/Sol | context_precision | 0.5751; 0.3473; 0.4035 | 0,4420 | 21,9 |
| BECS/Sol | context_recall | 0.8125; 1.0000; 0.8750 | 0,8958 | 8,7 |
| BECS/Sol | f1_geral | 0.5816; 0.6154; 0.6162 | 0,6044 | 2,7 |
| BECS/Sol | precision_geral | 0.4222; 0.4478; 0.4597 | 0,4432 | 3,5 |
| BECS/Sol | recall_geral | 0.9344; 0.9836; 0.9344 | 0,9508 | 2,4 |
| BECS/Sol | correctness | 5.0000; 4.0000; 4.0000 | 4,3333 | 10,9 |
| BECS/Sol | completeness | 5.0000; 5.0000; 5.0000 | 5,0000 | 0,0 |
| BECS/Sol | conciseness | 4.0000; 4.0000; 4.0000 | 4,0000 | 0,0 |
| BECS/Sol | tempo_s | 168.7000; 149.1000; 137.4000 | 151,7333 | 8,5 |
| BECS/Sol | custo_usd | 0.6208; 0.5708; 0.5549 | 0,5822 | 4,8 |

- Nome do sistema extraído pelo modelo: mudou entre repetições só em **SLCCI/Sol** (2 nomes); FFMIA tem nome diferente no Terra (sem repetição). Agrupar sempre pelo número do cenário.

## 11. Resultados atípicos investigados

| Execução | Valor | Investigação |
|---|---|---|
| SIMDE/Lua — faithfulness | 0,250 (Lua sem ela: 0,990) | 99% do cenário estava no contexto; afirmações (30 s, 5 s, 3 h, PDA) batem com o cenário → **falha do avaliador**. Havia 1 trecho contaminante ("Sistema de Controle de Propostas Comerciais", exemplo da base) que o modelo não reproduziu. |
| MDT/Lua — faithfulness e CR | 0,993 e 0,867 com 0 trecho do cenário (36 trechos) | **Falso alto**: nota alta sem sustentação real no cenário. |
| MDT/Lua — context precision | 0,191 (menor das 45) | Mesmo caso acima: nenhum trecho do cenário. |
| SLCCI/Sol rep1 — context precision | 0,241 | Instabilidade da context precision entre repetições. |
| BECS/Lua rep1 — context precision | 0,323 | 3º menor valor. |

## 12. Tabela por execução (45)

| Cenário | Modelo | Rep | RAG | Faith | AR | CP | CR | P | R | F1 | Juiz C/Cp/Cc | Custo | Tempo | Tokens | FS | Trechos | Cobert. | Nome do sistema extraído |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 GRD | Lua | 1 | 0,459 | 0,995 | 0,423 | 0,815 | 0,900 | 0,482 | 0,917 | 0,632 | 5/5/4 | 0,0266 | 84,4 | 47.084 | 2 | 24 | 99% | GRD - Sistema de Gestão de Riscos de Desastres |
| 1 GRD | Sol | 1 | 0,422 | 0,980 | 0,367 | 0,806 | 0,900 | 0,439 | 0,950 | 0,600 | 5/5/4 | 0,6098 | 147,6 | 48.781 | 2 | 28 | 99% | GRD - Sistema de Gestão de Riscos de Desastres |
| 1 GRD | Terra | 1 | 0,419 | 1,000 | 0,261 | 0,698 | 0,900 | 0,565 | 0,867 | 0,684 | 4/5/4 | 0,2008 | 97,7 | 44.267 | 2 | 26 | 99% | GRD - Sistema de Gestão de Riscos de Desastres |
| 2 UUIS | Lua | 1 | 0,430 | 0,991 | 0,334 | 0,560 | 1,000 | 0,443 | 0,783 | 0,565 | 4/5/4 | 0,0257 | 85,0 | 45.884 | 2 | 31 | 99% | Unified University Inventory System (UUIS) |
| 2 UUIS | Sol | 1 | 0,356 | 0,964 | 0,404 | 0,571 | 1,000 | 0,463 | 0,899 | 0,611 | 4/5/4 | 0,6255 | 164,1 | 49.205 | 2 | 33 | 99% | Unified University Inventory System (UUIS) |
| 2 UUIS | Terra | 1 | 0,375 | 0,939 | 0,325 | 0,594 | 0,923 | 0,522 | 0,855 | 0,648 | 4/5/4 | 0,1943 | 86,8 | 44.893 | 2 | 32 | 99% | Unified University Inventory System (UUIS) |
| 3 IPG | Lua | 1 | 0,379 | 1,000 | 0,546 | 0,420 | 0,900 | 0,500 | 0,868 | 0,634 | 4/5/4 | 0,0289 | 86,8 | 58.025 | 3 | 38 | 99% | IPG Job Manager |
| 3 IPG | Sol | 1 | 0,331 | 0,996 | 0,494 | 0,564 | 0,900 | 0,477 | 0,897 | 0,622 | 3/4/4 | 0,5834 | 158,4 | 47.048 | 2 | 32 | 99% | IPG Job Manager |
| 3 IPG | Terra | 1 | 0,331 | 1,000 | 0,471 | 0,799 | 0,900 | 0,548 | 0,838 | 0,663 | 4/5/4 | 0,1963 | 96,3 | 44.018 | 2 | 33 | 99% | IPG Job Manager |
| 4 MDT | Lua | 1 | 0,519 | 0,993 | 0,436 | 0,191 | 0,867 | 0,430 | 0,881 | 0,578 | 4/5/4 | 0,0229 | 88,8 | 43.218 | 2 | 36 | 0% | Minutia Deviation Tool (MDT) |
| 4 MDT | Sol | 1 | 0,683 | 1,000 | 0,436 | 0,494 | 0,867 | 0,425 | 0,881 | 0,574 | 4/5/4 | 0,5724 | 132,2 | 59.946 | 3 | 27 | 99% | Minutia Deviation Tool (MDT) |
| 4 MDT | Terra | 1 | 0,349 | 0,906 | 0,430 | 0,523 | 0,867 | 0,552 | 0,881 | 0,679 | 3/4/4 | 0,1600 | 76,8 | 41.147 | 2 | 32 | 99% | Minutia Deviation Tool (MDT) |
| 5 SIMDE | Lua | 1 | 0,451 | 0,250 | 0,402 | 0,641 | 0,889 | 0,512 | 0,800 | 0,624 | 4/5/4 | 0,0234 | 73,0 | 44.636 | 2 | 29 | 99% | SIMDE - Sistema Móvel de Diário Escolar |
| 5 SIMDE | Sol | 1 | 0,506 | 1,000 | 0,421 | 0,769 | 1,000 | 0,434 | 0,836 | 0,571 | 4/5/4 | 0,5873 | 151,3 | 48.737 | 2 | 33 | 78% | SIMDE - Sistema Móvel de Diário Escolar |
| 5 SIMDE | Terra | 1 | 0,452 | 1,000 | 0,332 | 0,644 | 1,000 | 0,506 | 0,727 | 0,597 | 4/5/4 | 0,1878 | 94,1 | 44.344 | 2 | 27 | 78% | SIMDE - Sistema Móvel de Diário Escolar |
| 6 SLCCI | Lua | 1 | 0,382 | 0,955 | 0,315 | 0,679 | 0,882 | 0,557 | 0,907 | 0,690 | 4/5/4 | 0,0233 | 77,5 | 43.474 | 2 | 34 | 98% | SLCCI (Sea Level Climate Change Initiative) |
| 6 SLCCI | Lua | 2 | 0,350 | 1,000 | 0,318 | 0,585 | 0,882 | 0,495 | 0,926 | 0,645 | 4/5/4 | 0,0238 | 84,6 | 43.310 | 2 | 30 | 98% | SLCCI (Sea Level Climate Change Initiative) |
| 6 SLCCI | Lua | 3 | 0,372 | 0,994 | 0,347 | 0,708 | 0,882 | 0,556 | 0,926 | 0,694 | 4/5/4 | 0,0169 | 70,5 | 29.053 | 1 | 20 | 98% | SLCCI (Sea Level Climate Change Initiative) |
| 6 SLCCI | Sol | 1 | 0,509 | 0,991 | 0,474 | 0,241 | 0,941 | 0,413 | 0,926 | 0,571 | 4/5/4 | 0,5896 | 160,5 | 48.684 | 2 | 33 | 98% | SLCCI Operational Sea Level Production System |
| 6 SLCCI | Sol | 2 | 0,440 | 1,000 | 0,398 | 0,451 | 0,882 | 0,431 | 0,982 | 0,599 | 4/5/4 | 0,5959 | 165,1 | 48.030 | 2 | 36 | 98% | SLCCI Operational Production System |
| 6 SLCCI | Sol | 3 | 0,642 | 0,995 | 0,480 | 0,341 | 0,882 | 0,437 | 0,963 | 0,601 | 4/5/4 | 0,5531 | 151,1 | 46.862 | 2 | 22 | 98% | SLCCI Operational Sea Level Production System |
| 6 SLCCI | Terra | 1 | 0,434 | 0,897 | 0,361 | 0,342 | 0,882 | 0,644 | 0,870 | 0,740 | 4/5/5 | 0,1607 | 80,2 | 41.737 | 2 | 33 | 98% | SLCCI (Sea Level Climate Change Initiative) |
| 6 SLCCI | Terra | 2 | 0,352 | 0,993 | 0,307 | 0,709 | 0,882 | 0,633 | 0,926 | 0,752 | 4/5/4 | 0,1274 | 69,5 | 26.861 | 1 | 20 | 98% | SLCCI (Sea Level Climate Change Initiative) |
| 6 SLCCI | Terra | 3 | 0,381 | 0,979 | 0,284 | 0,642 | 0,882 | 0,583 | 0,907 | 0,710 | 4/4/4 | 0,1778 | 86,5 | 43.417 | 2 | 32 | 98% | SLCCI (Sea Level Climate Change Initiative) |
| 7 SBD Rio | Lua | 1 | 0,466 | 1,000 | 0,584 | 0,628 | 1,000 | 0,464 | 0,879 | 0,607 | 4/4/4 | 0,0258 | 75,6 | 47.015 | 2 | 27 | 99% | Sistema de Bilhetagem Digital (SBD) — Rio de Janeiro |
| 7 SBD Rio | Lua | 2 | 0,454 | 1,000 | 0,507 | 0,821 | 0,812 | 0,447 | 0,879 | 0,593 | 4/4/4 | 0,0270 | 84,7 | 47.773 | 2 | 30 | 99% | Sistema de Bilhetagem Digital (SBD) — Rio de Janeiro |
| 7 SBD Rio | Lua | 3 | 0,473 | 1,000 | 0,601 | 0,784 | 0,917 | 0,553 | 0,897 | 0,684 | 3/5/4 | 0,0240 | 71,9 | 45.884 | 2 | 26 | 99% | Sistema de Bilhetagem Digital (SBD) — Rio de Janeiro |
| 7 SBD Rio | Sol | 1 | 0,519 | 1,000 | 0,589 | 0,640 | 0,867 | 0,360 | 0,914 | 0,517 | 4/5/4 | 0,7020 | 202,3 | 52.437 | 2 | 34 | 99% | Sistema de Bilhetagem Digital (SBD) — Rio de Janeiro |
| 7 SBD Rio | Sol | 2 | 0,593 | 0,996 | 0,461 | 0,657 | 0,867 | 0,400 | 0,931 | 0,560 | 4/5/4 | 0,6326 | 185,6 | 49.680 | 2 | 24 | 69% | Sistema de Bilhetagem Digital (SBD) — Rio de Janeiro |
| 7 SBD Rio | Sol | 3 | 0,646 | 1,000 | 0,532 | 0,468 | 1,000 | 0,381 | 0,914 | 0,538 | 3/5/4 | 0,6325 | 176,1 | 49.149 | 2 | 24 | 69% | Sistema de Bilhetagem Digital (SBD) — Rio de Janeiro |
| 7 SBD Rio | Terra | 1 | 0,465 | 0,979 | 0,413 | 0,545 | 0,867 | 0,590 | 0,845 | 0,695 | 4/4/4 | 0,1843 | 92,2 | 44.834 | 2 | 27 | 99% | Sistema de Bilhetagem Digital (SBD) — Rio de Janeiro |
| 7 SBD Rio | Terra | 2 | 0,446 | 0,995 | 0,393 | 0,691 | 0,867 | 0,539 | 0,828 | 0,653 | 4/5/4 | 0,1612 | 96,7 | 29.752 | 1 | 20 | 69% | Sistema de Bilhetagem Digital (SBD) — Rio de Janeiro |
| 7 SBD Rio | Terra | 3 | 0,460 | 0,987 | 0,410 | 0,567 | 0,867 | 0,522 | 0,828 | 0,640 | 4/5/4 | 0,1891 | 100,6 | 44.812 | 2 | 28 | 99% | Sistema de Bilhetagem Digital (SBD) — Rio de Janeiro |
| 8 BECS | Lua | 1 | 0,415 | 1,000 | 0,408 | 0,323 | 0,875 | 0,486 | 0,853 | 0,619 | 4/5/4 | 0,0237 | 75,0 | 43.629 | 2 | 32 | 99% | BECS (Book E-Commerce System) |
| 8 BECS | Lua | 2 | 0,403 | 1,000 | 0,409 | 0,351 | 0,875 | 0,596 | 0,918 | 0,723 | 4/4/4 | 0,0212 | 70,0 | 41.736 | 2 | 33 | 99% | BECS (Book E-Commerce System) |
| 8 BECS | Lua | 3 | 0,414 | 0,995 | 0,302 | 0,512 | 0,875 | 0,483 | 0,918 | 0,633 | 4/5/4 | 0,0192 | 72,5 | 30.156 | 1 | 20 | 99% | BECS (Book E-Commerce System) |
| 8 BECS | Sol | 1 | 0,483 | 0,987 | 0,295 | 0,575 | 0,812 | 0,422 | 0,934 | 0,582 | 5/5/4 | 0,6208 | 168,7 | 49.733 | 2 | 32 | 99% | BECS (Book E-Commerce System) |
| 8 BECS | Sol | 2 | 0,371 | 1,000 | 0,306 | 0,347 | 1,000 | 0,448 | 0,984 | 0,615 | 4/5/4 | 0,5708 | 149,1 | 46.705 | 2 | 34 | 99% | BECS (Book E-Commerce System) |
| 8 BECS | Sol | 3 | 0,627 | 1,000 | 0,307 | 0,404 | 0,875 | 0,460 | 0,934 | 0,616 | 4/5/4 | 0,5549 | 137,4 | 47.815 | 2 | 24 | 99% | BECS (Book E-Commerce System) |
| 8 BECS | Terra | 1 | 0,381 | 0,994 | 0,434 | 0,539 | 0,875 | 0,535 | 0,869 | 0,662 | 4/5/4 | 0,1899 | 101,2 | 44.283 | 2 | 29 | 99% | BECS (Book E-Commerce System) |
| 8 BECS | Terra | 2 | 0,503 | 1,000 | 0,320 | 0,403 | 0,875 | 0,655 | 0,934 | 0,770 | 4/5/4 | 0,1685 | 82,0 | 41.917 | 2 | 32 | 99% | BECS (Book E-Commerce System) |
| 8 BECS | Terra | 3 | 0,346 | 0,979 | 0,355 | 0,548 | 0,867 | 0,607 | 0,885 | 0,720 | 3/5/4 | 0,1926 | 101,3 | 43.970 | 2 | 31 | 99% | BECS (Book E-Commerce System) |
| 9 FFMIA | Lua | 1 | 0,427 | 0,944 | 0,378 | 0,516 | 0,882 | 0,540 | 0,947 | 0,688 | 3/5/4 | 0,0235 | 111,1 | 43.389 | 2 | 31 | 99% | Core Financial System |
| 9 FFMIA | Sol | 1 | 0,521 | 0,968 | 0,509 | 0,471 | 0,882 | 0,432 | 0,947 | 0,593 | 4/5/4 | 0,5811 | 162,1 | 47.784 | 2 | 34 | 99% | Core Financial System |
| 9 FFMIA | Terra | 1 | 0,365 | 0,969 | 0,495 | 0,651 | 0,882 | 0,581 | 0,877 | 0,699 | 4/5/4 | 0,1788 | 87,8 | 43.459 | 2 | 35 | 99% | Core Financial System (FFMIA Compliance Initiative) |

## 13. Síntese: o que foi bom e o que foi ruim

**Resultados positivos**
- 45/45 execuções concluídas, todas com todos os tipos de artefato; 0 falhas (1 retry automático).
- Faithfulness média 0,969 (≥ 0,94 em todos os modelos; 0,990 no Lua sem o caso SIMDE).
- Recall alto: 0,891 micro / 0,892 por execução — o protótipo cobre quase tudo o que o gabarito espera; stakeholders 0,970, RF 0,935, UC 0,931, HU 0,929.
- Rastreabilidade estrutural 100% (HU, UC, CA e RF com RN); todas as 45 com todos os tipos de artefato, inclusive glossário (6 a 17 termos).
- Juiz: completude 4,84; desempenho homogêneo entre cenários (F1 0,598–0,667), dificuldades e idiomas.
- Lua: nota do juiz equivalente (4,24 × 4,31 do Sol) a ~1/25 do custo — melhor custo-benefício; Terra: maior F1 (0,688).
- Estabilidade alta em faithfulness (CV 1,1%), recall da classificação (2,0%), context recall (3,1%), custo e tempo.

**Resultados negativos ou fracos**
- Precisão baixa: 0,490 micro — 51% do gerado sem correspondente; pior em CA (0,211: 736 FP × 197 VP), UC (0,386), RNF (0,394), HU (0,430). Parte é desenho do gabarito (núcleo essencial) e granularidade do um-para-um.
- Excesso de artefatos: 1,51× (Terra) a 2,17× (Sol) o esperado; o modelo mais caro gerou mais e teve o menor F1 (0,585).
- Regras de negócio com o menor recall (0,718) — regras implícitas nem sempre identificadas.
- Answer relevancy baixa (0,408) — efeito da adaptação da métrica (pergunta = instrução + cenário inteiro).
- Context precision instável (CV médio 17,1%, máx. 28,3%) e RAG Score instável no Sol (até 21,3%); Jaccard 33%.
- RAG Score não acompanha a qualidade (r = −0,53 com F1; ~0 com faithfulness e com o juiz).
- Correção do juiz 3,93 (a menor nota), em parte por viés do método ("deve" exigido em docs em inglês).
- Sol: 25× o custo do Lua e 2× o tempo, sem ganho de F1.

**Limitações do método reveladas pelos dados**
- Avaliadores LLM falham nos dois sentidos (SIMDE/Lua falso baixo; MDT/Lua falso alto) e variam (4/6/8 em 9 itens).
- O juiz de qualidade não penaliza volume; rubrica e prompt em português penalizam docs em inglês.
- Sem condição sem RAG, sem testes de significância, sem amostragem humana, data única.
- Contaminação na recuperação (trecho de exemplo da base no contexto do SIMDE) — a instrução anticontaminação atua na geração, não na recuperação.

