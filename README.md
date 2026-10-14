# Especificação de requisitos de software com IA generativa e RAG

Código, insumos e resultados da pesquisa **"Especificação de requisitos de software com inteligência artificial generativa: avaliação de um protótipo com recuperação aumentada"** (Bacharelado em Engenharia de Software — Universidade da Região de Joinville, Univille, 2026).

A pesquisa avalia o desempenho de um protótipo baseado em IA generativa com Geração Aumentada por Recuperação (RAG) na elaboração de um documento formal de Especificação de Requisitos de Software (SRS) a partir de insumos de projeto. O protótipo foi executado 45 vezes, com três modelos e nove cenários, e os documentos gerados foram avaliados por quatro frentes: RAG Score, métricas do RAGAS, Precisão/Recall/F1 por tipo de artefato e LLM-as-judge.

## Estrutura

```
Agente/                         Protótipo e scripts de geração e avaliação
  main.py                       Protótipo (Streamlit + Responses API da OpenAI): prompt, RAG, geração do JSON e do .docx
  rodar_execucao.py             Executa o protótipo para um cenário e um modelo, sem interface
  rodar_lote.py                 Executa o lote completo (45 execuções), com manifesto de progresso
  avaliar_ragas.py              Faithfulness, answer relevancy, context precision e context recall (RAGAS 0.4.3)
  avaliar_classificacao.py      Precisão, Recall e F1 por tipo de artefato (correspondência com o gabarito estruturado)
  avaliar_qualidade.py          LLM-as-judge: notas de correção, completude e concisão (1 a 5)
  requirements.txt              Dependências do protótipo e da classificação/qualidade
  requirements_ragas.txt        Dependências da avaliação RAGAS (ambiente separado)
  .env.example                  Variáveis de ambiente necessárias

Projetos Oficiais/
  Cenarios/                     Os nove cenários de projeto (insumos do experimento)
  Gabaritos_RAGAS/              Gabaritos de afirmações atômicas por cenário (context precision/recall)
  Gabaritos_RFRNF/              Gabaritos estruturados (JSON) com os artefatos esperados por cenário

Testes/
  Execuções Oficiais/           Resultados das 45 execuções oficiais (ver abaixo)
  Historico/Novos modelos/      Execuções de calibração anteriores ao lote (teste A/B do prompt)
  Validacao/                    Scripts de consolidação e análise dos resultados
  Graficos/                     Script e figuras do artigo
```

## Por onde começar

1. **Resultados:** `Testes/Execuções Oficiais/RESULTADOS_CONSOLIDADOS.md` reúne todos os números das 45 execuções num único documento.
2. **Protótipo:** em `Agente/main.py`, o prompt de sistema está em `PROMPT_SISTEMA`; a chamada ao modelo com as duas *vector stores* em `elicitar_requisitos()`; o RAG Score em `calcular_rag_score()`; o custo em `calcular_custo_usd()`; e o documento .docx em `gerar_docx()`.
3. **Avaliação:** os três scripts `Agente/avaliar_*.py` leem os arquivos `ragas_*.json` de cada execução e gravam os `resultados_*.csv`.
4. **Exemplo de saída:** qualquer `SRS_*.docx` em `Testes/Execuções Oficiais/` é um documento gerado pelo protótipo, sem edição.

## Fluxo dos dados

```
Projetos Oficiais/Cenarios/Project Scenario N.pdf
        │  rodar_lote.py → rodar_execucao.py → funções de main.py
        ▼
Testes/Execuções Oficiais/   SRS_*.docx · execucao_*.csv · ragas_*.json · _lote_manifest.json
        │  avaliar_ragas.py · avaliar_classificacao.py · avaliar_qualidade.py
        │  (usam os gabaritos de Projetos Oficiais/Gabaritos_RAGAS e Gabaritos_RFRNF)
        ▼
Testes/Execuções Oficiais/   resultados_ragas.csv · resultados_classificacao.csv · resultados_qualidade.csv
        │  Testes/Validacao/*.py   (somente leitura, sem chamadas à API)
        ▼
base_consolidada_45.csv · valores_recalculados.json · analises_cap4.json · RESULTADOS_CONSOLIDADOS.md
        │  Testes/Graficos/gerar_graficos.py
        ▼
Testes/Graficos/figura_01 … figura_07.png
```

Os nomes das pastas, inclusive os espaços e acentos, são usados pelos scripts para localizar cenários, gabaritos e resultados; renomeá-los impede a execução.

## Protótipo

- **Modelos avaliados** (família GPT-5.6 da OpenAI): Lua (`gpt-5.6-luna`), Terra (`gpt-5.6-terra`) e Sol (`gpt-5.6-sol`), com esforço de raciocínio médio, verbosidade baixa e saída em JSON.
- **Arquitetura RAG com duas fontes:** o texto do cenário é enviado integralmente na mensagem ao modelo (fonte de conteúdo) e também carregado numa *vector store* A, criada a cada execução, para buscas pontuais; uma *vector store* B fixa contém a base de conhecimento de Engenharia de Requisitos (fonte de estrutura e qualidade de escrita). As buscas usam a ferramenta `file_search` da Responses API.
- **Saída:** escopo, stakeholders, regras de negócio, requisitos funcionais e não funcionais (com categoria da ISO/IEC 25010), histórias de usuário (Connextra), casos de uso, critérios de aceite (Dado/Quando/Então) e glossário, exportados em .docx, .csv e .json.

### Base de conhecimento (vector store B)

A *vector store* B foi criada uma única vez na conta da OpenAI com sete documentos: dois guias elaborados pelo autor (templates, exemplos e checklists de escrita de artefatos) e cinco documentos de referência — os *syllabi* CPRE Foundation Level e Elicitation do IREB, o Padrão Essencial Global de Análise de Negócios do IIBA, capítulos de amostra de *Software Requirements* (Wiegers e Beatty, 2013) e o artigo de Llanque, Flores e Dávila (2022). **Esses documentos não estão no repositório**, pois os de terceiros têm direitos autorais. Para reproduzir, crie uma *vector store* com documentos equivalentes (painel da OpenAI ou API `vector_stores`) e informe o identificador em `VS_B_ID`.

## Como executar

Requer uma chave da API da OpenAI. As execuções usaram Python 3.13.

```powershell
cd Agente
copy .env.example .env          # preencha OPENAI_API_KEY e VS_B_ID

# Protótipo, geração em lote, classificação e qualidade
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run main.py                                   # interface
python rodar_lote.py "..\Testes\Execuções Oficiais"     # lote de 45 execuções
python avaliar_classificacao.py "..\Testes\Execuções Oficiais"
python avaliar_qualidade.py "..\Testes\Execuções Oficiais"

# Avaliação RAGAS (ambiente separado, por conflito de dependências)
python -m venv venv_ragas
.\venv_ragas\Scripts\Activate.ps1
pip install -r requirements_ragas.txt
python avaliar_ragas.py "..\Testes\Execuções Oficiais"
```

O avaliador das três frentes (RAGAS, classificação e qualidade) é o modelo `gpt-5-mini`; os *embeddings* da answer relevancy usam `text-embedding-3-small`. A geração e as avaliações chamam a API e têm custo; os resultados abaixo já estão no repositório e não precisam ser refeitos para a análise.

## Resultados (`Testes/Execuções Oficiais/`)

As 45 execuções oficiais foram realizadas em 20/08/2026: os nove cenários uma vez em cada modelo (27) e três cenários (BECS, SBD e SLCCI) com duas execuções adicionais por modelo (18).

| Arquivo | Conteúdo |
|---|---|
| `_lote_manifest.json` | Manifesto do lote (combinações, status e arquivos de cada execução) |
| `execucao_*.csv` | Dados operacionais de cada execução: tokens, tempo, custo, RAG Score, chamadas ao `file_search` |
| `ragas_*.json` | Exportação de cada execução: pergunta, documento gerado, trechos recuperados, gabaritos e artefatos em JSON |
| `SRS_*.docx` | Documentos de especificação gerados pelo protótipo |
| `resultados_ragas.csv` | Faithfulness, answer relevancy, context precision e context recall por execução |
| `resultados_classificacao.csv` | VP, FP, FN, Precisão, Recall e F1 por tipo de artefato e execução |
| `resultados_qualidade.csv` | Notas e justificativas do LLM-as-judge por execução |
| `resultados_repeticoes.csv` | Coeficiente de variação de cada métrica nas nove combinações com três execuções |
| `resultados_custo_beneficio.csv` | Médias por modelo e razões de qualidade e F1 por dólar, token e segundo |
| `RESULTADOS_CONSOLIDADOS.md` | Todos os resultados num único documento (gerado por script) |

## Análise dos resultados (`Testes/Validacao/` e `Testes/Graficos/`)

Somente leitura dos arquivos acima; não chamam a API. Dependências: `pip install pandas numpy matplotlib`.

| Script | O que faz |
|---|---|
| `validar_dados.py` | Confere os CSVs contra os dados brutos, recalcula custo, P/R/F1, coeficientes de variação e custo-benefício e gera `base_consolidada_45.csv` e `valores_recalculados.json` |
| `cobertura_cenario_contexto.py` | Mede quanto do texto de cada cenário estava nos trechos recuperados avaliados pelo RAGAS |
| `analises_complementares_cap4.py` | Análises complementares do capítulo 4 do artigo (context precision × posição dos trechos, marcações [TBD] nos requisitos não funcionais, ordem dos modelos por cenário, sobreposição dos trechos entre repetições) e gera `analises_cap4.json` |
| `gerar_resultados_consolidados.py` | Gera `Testes/Execuções Oficiais/RESULTADOS_CONSOLIDADOS.md` |
| `gerar_graficos.py` | Gera as sete figuras do artigo (`figura_01` a `figura_07`) |

Saídas gravadas em `Testes/Validacao/`: `base_consolidada_45.csv` (uma linha por execução, com todas as métricas), `valores_recalculados.json` e `analises_cap4.json`.

Ordem sugerida: `validar_dados.py` → `cobertura_cenario_contexto.py` e `analises_complementares_cap4.py` → `gerar_resultados_consolidados.py` → `gerar_graficos.py`.

## Cenários

Os nove cenários foram elaborados pelo autor a partir de documentos públicos de requisitos, que serviram apenas de base para a redação e não foram fornecidos ao protótipo. Os documentos de origem não estão no repositório; as referências completas estão no artigo.

| Nº | Cenário | Idioma | Dificuldade |
|---|---|---|---|
| 1 | GRD — Gestão de Riscos de Desastres | Português | Média |
| 2 | UUIS — Unified University Inventory System | Inglês | Baixa |
| 3 | IPG Job Manager | Inglês | Média |
| 4 | MDT — Minutia Deviation Tool | Inglês | Baixa |
| 5 | SIMDE — Sistema Móvel de Diário Escolar | Português | Baixa |
| 6 | SLCCI — Sea Level Climate Change Initiative | Inglês | Alta |
| 7 | SBD — Sistema de Bilhetagem Digital (Rio de Janeiro) | Português | Média |
| 8 | BECS — Book E-Commerce System | Inglês | Baixa |
| 9 | Core Financial System (FFMIA) | Inglês | Alta |

## Conteúdo de terceiros

Os arquivos `Testes/Execuções Oficiais/ragas_*.json` guardam, no campo `contexts`, os trechos que a busca do protótipo recuperou em cada execução. Além dos cenários e dos guias elaborados pelo autor, esses trechos vêm dos seguintes documentos de terceiros, reproduzidos apenas como dado de avaliação (necessário para refazer as métricas do RAGAS) e **não cobertos pela licença CC BY 4.0 deste repositório**:

- BRAND, Anja et al. *Elicitação de requisitos: syllabus CPRE Practitioner/Specialist*. Versão 3.2.0. International Requirements Engineering Board, 2025.
- BÜHNE, Stan et al. *CPRE Nível Fundamental: syllabus*. Versão 3.2.1. International Requirements Engineering Board, 2024.
- IIBA – INTERNATIONAL INSTITUTE OF BUSINESS ANALYSIS. *Padrão Essencial Global do IIBA para Análise de Negócios: um complemento para o Guia BABOK versão 3*. Toronto: IIBA, 2017.
- LLANQUE, Alex; FLORES, Vaneza; DÁVILA, Abraham. User-Centered Methodologies for Requirements Engineering: A Comparative Analysis using ISO/IEC/IEEE 29148. *ReCIBE*, v. 11, n. 1, p. C2-1–C2-14, 2022.
- WIEGERS, Karl; BEATTY, Joy. *Software Requirements*. 3. ed. Redmond: Microsoft Press, 2013 (capítulos de amostra).

Os endereços de e-mail dos autores que constavam num desses trechos foram substituídos por `[e-mail removido]`.

## Licença

- **Código** (`*.py` e arquivos de configuração): [MIT](LICENSE).
- **Dados e resultados** (cenários, gabaritos, resultados, documentos gerados e figuras): [CC BY 4.0](LICENSE-DATA.md), exceto o conteúdo de terceiros descrito acima.

## Autoria

João Filipe Marcoski — orientação de Chaiene Mercedes da Silva Minella. Universidade da Região de Joinville (Univille).
