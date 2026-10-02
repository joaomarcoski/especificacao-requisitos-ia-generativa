"""
main.py — Modelo Inteligente para Elicitação de Requisitos (Univille)

Fluxo:
  1. Usuário informa API Key, modelo, observações e faz upload dos arquivos
  2. Sistema cria Vector Store A com os arquivos do usuário
  3. Sistema chama a Responses API com file_search em VS A + VS B (base fixa)
  4. Modelo retorna JSON estruturado com todos os artefatos do SRS
  5. RAG Score é extraído de file_search_call.results
  6. python-docx gera o .docx final para download
"""

import csv
import json
import os
import time
import uuid
from datetime import datetime
from io import BytesIO, StringIO

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
load_dotenv()

MODELOS = {
    "Lua":  "gpt-5.6-luna",
    "Terra": "gpt-5.6-terra",
    "Sol":  "gpt-5.6-sol",
}

TIMEOUTS = {
    "gpt-5.6-luna":  240,
    "gpt-5.6-terra": 360,
    "gpt-5.6-sol":   600,
}

# Esforço de raciocínio por modelo. Sem isso, a API usa "medium" por padrão
# em todos os modelos gpt-5.6 — caro para uma tarefa de extração/formatação,
# que não exige raciocínio multi-etapas profundo. Reduzir o esforço corta
# tokens de "pensamento" ocultos e acelera a resposta em todos os modelos.
REASONING_EFFORT = {
    "gpt-5.6-luna":  "medium",
    "gpt-5.6-terra": "medium",
    "gpt-5.6-sol":   "medium",
}

# Preços oficiais da OpenAI (USD por 1M de tokens), conferidos em
# developers.openai.com/api/docs/pricing em 18/08/2026 (preços pós-corte de
# 30/07/2026). Não inclui o custo de armazenamento do Vector Store
# ($0.10/GB/dia, 1GB grátis), que é recorrente e não atribuível a uma
# execução isolada.
PRECOS_USD = {
    "gpt-5.6-sol":   {"input": 5.00, "cached_input": 0.50, "output": 30.00},
    "gpt-5.6-terra": {"input": 2.00, "cached_input": 0.20, "output": 12.00},
    "gpt-5.6-luna":  {"input": 0.20, "cached_input": 0.02, "output": 1.20},
}
# Custo por chamada da ferramenta file_search — cobrado à parte dos tokens,
# só na Responses API.
PRECO_FILE_SEARCH_POR_1K_CHAMADAS = 2.50

VS_B_ID = os.getenv("VS_B_ID", "")

# ---------------------------------------------------------------------------
# Prompt de elicitação
# ---------------------------------------------------------------------------
PROMPT_SISTEMA = """PAPEL
Você é um Engenheiro de Requisitos Sênior, especializado em elicitação e especificação de software, com domínio das normas ISO/IEC/IEEE 29148:2018 (Software Requirements Specification) e ISO/IEC 25010:2023 (qualidade de software). Você escreve sempre no mesmo idioma do documento de cenário do usuário, em tom formal e tecnicamente preciso — se o cenário estiver em português, o SRS sai em português; se estiver em inglês, o SRS sai em inglês; e assim por diante para qualquer outro idioma em que o cenário esteja escrito.

OBJETIVO
Analisar o(s) documento(s) de cenário de projeto enviados pelo usuário e produzir um Documento de Especificação de Requisitos de Software (SRS) completo, coerente e tecnicamente rigoroso, em formato JSON estruturado.

FONTES DE INFORMAÇÃO
Você tem acesso a duas fontes, com papéis diferentes e complementares — não os confunda:

1. DOCUMENTO(S) DE CENÁRIO — transcritos por completo na mensagem do usuário, logo abaixo destas instruções. É a fonte de CONTEÚDO: tudo o que o sistema deve fazer, suas regras de negócio, seus stakeholders, restrições e objetivos vêm exclusivamente daqui (ou de inferência justificada a partir daqui, marcada como tal). Esse texto já está disponível diretamente na conversa — não é preciso (nem deve ser a via principal) usar file_search para lê-lo; use file_search sobre o Vector Store do usuário só como apoio pontual, se precisar confirmar uma citação exata ou revisitar um trecho específico.
2. BASE DE CONHECIMENTO FIXA — material de referência reutilizado em todo atendimento (templates, normas, guia de identificação de artefatos, exemplos de escrita de RF/RNF/HU/UC/CA), acessível via file_search. É a fonte de ESTRUTURA E QUALIDADE: define como cada artefato deve ser formatado, redigido e detalhado — nunca o conteúdo do projeto em si.

PROCESSO DE TRABALHO — siga estas etapas:
1. Leia o(s) documento(s) de cenário transcritos na mensagem do usuário por completo antes de gerar qualquer artefato. Identifique o sistema, seus objetivos, usuários, restrições e qualquer requisito já explícito no texto.
2. Faça pelo menos uma busca dedicada na base de conhecimento por templates, exemplos e critérios de qualidade para CADA um dos tipos de artefato abaixo, antes de escrever aquele artefato. Não se baseie em uma única busca genérica para tudo — buscas específicas por tipo trazem exemplos mais relevantes e elevam a qualidade da escrita.
   [ ] Stakeholders
   [ ] Regras de negócio
   [ ] Requisitos funcionais
   [ ] Requisitos não funcionais
   [ ] Histórias de usuário
   [ ] Casos de uso
   [ ] Critérios de aceite
3. Extraia da base de conhecimento as definições e categorias oficiais necessárias (ex.: as categorias da ISO/IEC 25010:2023, a estrutura BDD, o formato Connextra) em vez de confiar apenas em conhecimento prévio — a base de conhecimento é a referência de verdade para terminologia e estrutura deste projeto.
4. Gere os artefatos respeitando a ordem de dependência: stakeholders e escopo primeiro; depois regras de negócio; depois requisitos funcionais e não funcionais; depois histórias de usuário e casos de uso (que referenciam RFs); por último os critérios de aceite (que referenciam RFs/HUs).
5. Verifique a rastreabilidade entre artefatos antes de finalizar: toda HU deve referenciar um RF existente; todo UC deve referenciar uma HU existente; todo CA deve referenciar um RF ou HU existente; toda RF associada a uma RN deve citá-la corretamente.
6. Releia o conjunto final em busca de redundâncias, contradições, lacunas de cobertura ou artefatos vagos antes de retornar o JSON — corrija o que encontrar. Confirme também que fez pelo menos uma busca dedicada para cada item do checklist do passo 2; se algum item ainda não foi pesquisado, faça a busca antes de prosseguir.

Atenção: quaisquer exemplos completos de projeto que aparecerem na base de conhecimento (sistemas fictícios usados para ilustrar formato, nível de detalhe e estilo de escrita de RF/RNF/HU/UC/CA) existem só para isso — nunca como fonte de conteúdo. Isso não reduz a exigência de busca do passo 2: continue consultando a base normalmente para templates, critérios de qualidade e categorias oficiais. O que não deve acontecer, em nenhuma hipótese, é copiar o nome do sistema, valores numéricos, papéis de stakeholder, integrações (ex.: SAP, LGPD) ou regras de negócio de um exemplo da base para o SRS gerado — o conteúdo do SRS vem exclusivamente do(s) documento(s) de cenário transcritos na mensagem do usuário (fonte 1 de FONTES DE INFORMAÇÃO), nunca de um exemplo da base de conhecimento, mesmo que o documento de cenário esteja incompleto ou pouco desenvolvido nesse ponto — nesse caso, use [INFERIDO]/[TBD] em vez de preencher com conteúdo de exemplo.

REGRAS DE QUALIDADE OBRIGATÓRIAS:
1. Todo RF deve usar o verbo "deve" e descrever UMA única funcionalidade verificável.
2. Todo RNF deve ter categoria ISO/IEC 25010:2023, métrica de aceitação numérica e método de verificação.
3. Todo RNF sem métrica explícita no documento deve ter uma métrica razoável proposta e marcada com [TBD].
4. Toda HU deve seguir o formato Connextra: "Como [persona], quero [ação], para [benefício]."
5. Todo CA deve seguir o formato BDD: Dado / Quando / Então — com resultado verificável no "Então".
6. Nunca usar termos subjetivos sem quantificação: rápido, fácil, amigável, seguro, eficiente.
7. IDs sequenciais e únicos: STK-01, RN-001, RF-001, RNF-001, HU-001, UC-001, CA-001.
8. Se informações estiverem ausentes no documento, inferir com base no contexto e marcar com [INFERIDO].
9. Todo o conteúdo do JSON — resumo executivo, descrições, títulos, fluxos, critérios de aceite, glossário e qualquer texto livre — deve ser escrito no mesmo idioma do documento de cenário do usuário (identifique esse idioma antes de começar a escrever). Exceção: termos técnicos padronizados internacionalmente permanecem como estão, no idioma original deles, independentemente do idioma do restante do documento — as categorias do MoSCoW ("Must have", "Should have", "Could have", "Won't have") e as categorias da ISO/IEC 25010 (ex.: "Performance Efficiency", "Security").

Retorne SOMENTE o JSON abaixo, sem texto antes ou depois, sem blocos de código markdown:

{
  "sistema": "Nome do sistema identificado no documento",
  "versao": "v0.1",
  "data": "Data de hoje no formato DD/MM/AAAA",
  "resumo_executivo": "Parágrafo descrevendo o sistema, o problema que resolve e o valor entregue.",
  "escopo": {
    "descricao": "Descrição em uma frase do que o sistema faz.",
    "em_escopo": ["funcionalidade ou módulo A", "funcionalidade ou módulo B"],
    "fora_de_escopo": ["funcionalidade excluída A — motivo", "funcionalidade excluída B — motivo"],
    "premissas": ["PA-01: texto da premissa"],
    "restricoes": ["REST-01 (Tipo): texto da restrição"]
  },
  "stakeholders": [
    {
      "id": "STK-01",
      "nome": "Nome ou papel",
      "tipo": "Usuário primário | Usuário secundário | Stakeholder externo",
      "nivel_acesso": "Total | Parcial | Nenhum",
      "necessidades": "Principais necessidades deste perfil"
    }
  ],
  "regras_de_negocio": [
    {
      "id": "RN-001",
      "titulo": "Título curto da regra",
      "descricao": "Descrição da política ou condição de negócio, sem mencionar software.",
      "fonte": "Área ou lei de origem",
      "excecoes": "Casos em que a regra não se aplica, ou 'Nenhuma'"
    }
  ],
  "requisitos_funcionais": [
    {
      "id": "RF-001",
      "titulo": "Título curto",
      "descricao": "O sistema deve [verbo] [complemento verificável].",
      "prioridade": "Must have | Should have | Could have | Won't have",
      "stakeholder_origem": "STK-01",
      "rn_associada": "RN-001 ou N/A"
    }
  ],
  "requisitos_nao_funcionais": [
    {
      "id": "RNF-001",
      "titulo": "Título curto",
      "categoria_iso25010": "Performance Efficiency | Security | Reliability | Compatibility | Interaction Capability | Maintainability | Flexibility | Functional Suitability | Safety",
      "descricao": "O sistema deve [atributo de qualidade] [métrica objetiva].",
      "metrica_aceitacao": "Valor numérico, percentual ou condição testável objetiva.",
      "metodo_verificacao": "Teste de carga | Auditoria de código | Teste de penetração | Revisão manual | etc."
    }
  ],
  "historias_de_usuario": [
    {
      "id": "HU-001",
      "como": "perfil de usuário / persona",
      "quero": "ação ou funcionalidade desejada",
      "para": "benefício de negócio ou objetivo atingido",
      "rf_associado": "RF-001",
      "prioridade": "Must have | Should have | Could have | Won't have"
    }
  ],
  "casos_de_uso": [
    {
      "id": "UC-001",
      "nome": "Nome do caso de uso",
      "ator_principal": "Nome do ator",
      "hu_relacionada": "HU-001",
      "pre_condicao": "O que deve ser verdade antes do início",
      "pos_condicao_sucesso": "Estado do sistema após conclusão bem-sucedida",
      "pos_condicao_falha": "Estado do sistema após falha",
      "fluxo_principal": [
        "1. O ator faz X.",
        "2. O sistema responde Y.",
        "3. O sistema conclui Z."
      ],
      "fluxos_alternativos": ["2a. Condição → o sistema faz W; retorna ao passo 1."],
      "fluxos_excecao": ["2b. Erro → o sistema exibe mensagem M (ref. RN-001, RF-001)."]
    }
  ],
  "criterios_de_aceite": [
    {
      "id": "CA-001",
      "rf_hu_ref": "RF-001 / HU-001",
      "titulo": "Título curto do critério",
      "dado": "contexto ou pré-condição do sistema/usuário",
      "quando": "ação do usuário ou evento que dispara o comportamento",
      "entao": "resultado esperado e verificável — valor, status, mensagem, tempo máximo",
      "metodo_verificacao": "Teste automatizado E2E | Teste funcional manual | Teste de integração"
    }
  ],
  "glossario": [
    {
      "termo": "Termo do domínio",
      "definicao": "Definição precisa no contexto deste projeto"
    }
  ],
  "idioma": "pt ou en, conforme o idioma do cenário"
}

O campo "idioma" deve conter "pt" se o documento de cenário estiver em português, ou "en" para qualquer outro idioma (inglês inclusive) — os rótulos fixos do documento final (títulos de seção como "Requisitos Funcionais") só existem prontos nesses dois idiomas. Já o conteúdo livre do restante do JSON deve sempre seguir o idioma real do cenário, mesmo nos casos em que esse idioma não seja nem português nem inglês."""


# ---------------------------------------------------------------------------
# Funções de negócio
# ---------------------------------------------------------------------------
def extrair_texto_cenario(arquivos) -> str:
    """Extrai o texto bruto dos documentos de cenário enviados pelo usuário.

    Usado só para compor o campo "pergunta" do export de avaliação RAGAS
    (ver gerar_json_ragas) — não participa do fluxo de elicitação em si,
    que usa o Vector Store A via file_search. Falha em um arquivo não deve
    derrubar a extração dos demais: PDFs escaneados sem camada de texto,
    por exemplo, retornam string vazia do pypdf em vez de erro.
    """
    partes = []
    for arquivo in arquivos:
        nome = arquivo.name.lower()
        raw = arquivo.getvalue()
        try:
            if nome.endswith(".txt"):
                texto = raw.decode("utf-8", errors="ignore")
            elif nome.endswith(".docx"):
                doc = Document(BytesIO(raw))
                texto = "\n".join(p.text for p in doc.paragraphs)
            elif nome.endswith(".pdf"):
                leitor = PdfReader(BytesIO(raw))
                texto = "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)
            else:
                continue
        except Exception:
            continue
        if texto.strip():
            partes.append(f"--- {arquivo.name} ---\n{texto.strip()}")
    return "\n\n".join(partes)


def criar_vector_store_usuario(client: OpenAI, arquivos) -> str:
    # Nome com timestamp + uuid deixa óbvio, no dashboard da OpenAI, que este
    # Vector Store é descartável — nunca deve ser confundido com VS_B (base
    # de conhecimento fixa, criada uma única vez com os documentos da base; ver README).
    nome = f"tmp_sessao_usuario_{datetime.utcnow():%Y%m%dT%H%M%S}_{uuid.uuid4().hex[:8]}"

    # expires_after é a rede de segurança: se a sessão for interrompida antes
    # de descartar_vector_store_sessao() rodar (aba fechada, processo morto),
    # a própria OpenAI apaga este Vector Store sozinha depois de 1 dia sem uso.
    vs = client.vector_stores.create(
        name=nome,
        expires_after={"anchor": "last_active_at", "days": 1},
    )

    file_streams = [(arquivo.name, BytesIO(arquivo.getvalue())) for arquivo in arquivos]

    batch = client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vs.id,
        files=file_streams,
    )

    if batch.status != "completed":
        raise RuntimeError(
            f"Falha no processamento dos arquivos. Status: {batch.status}. "
            f"Falhos: {batch.file_counts.failed}"
        )

    return vs.id


def descartar_vector_store_sessao(client: OpenAI, vs_a_id: str, on_warning=None) -> None:
    """Apaga o Vector Store A (e os File objects que ele contém) ao final da execução.

    Único ponto do código autorizado a chamar vector_stores.delete()/files.delete().
    Só pode operar sobre um ID retornado por criar_vector_store_usuario() na
    própria execução corrente — nunca sobre VS_B_ID (base de conhecimento fixa,
    compartilhada entre todas as sessões) nem sobre qualquer ID vindo de
    configuração ou de uma varredura geral da conta. Isso é verificado, não só
    presumido: a guarda abaixo recusa explicitamente VS_B_ID como alvo.

    Falhas aqui nunca devem interromper o fluxo — os resultados da elicitação
    já foram extraídos antes desta chamada. Problemas são reportados via
    on_warning (ex.: st.warning), não propagados como exceção.
    """
    if not vs_a_id or vs_a_id == VS_B_ID:
        return

    def _avisar(msg: str) -> None:
        if on_warning:
            on_warning(msg)

    try:
        arquivos = client.vector_stores.files.list(vector_store_id=vs_a_id)
        for arquivo in arquivos.data:
            try:
                client.files.delete(arquivo.id)
            except Exception as e:
                _avisar(f"Não foi possível apagar o arquivo temporário {arquivo.id}: {e}")
    except Exception as e:
        _avisar(f"Não foi possível listar os arquivos do Vector Store temporário: {e}")

    try:
        client.vector_stores.delete(vs_a_id)
    except Exception as e:
        _avisar(f"Não foi possível apagar o Vector Store temporário {vs_a_id}: {e}")


def calcular_rag_score(response) -> float:
    scores = []
    for item in response.output:
        if hasattr(item, "type") and item.type == "file_search_call":
            resultados = getattr(item, "results", None) or []
            for r in resultados:
                s = getattr(r, "score", None)
                if s is not None:
                    scores.append(float(s))
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def extrair_contextos(response) -> list[str]:
    """Extrai o texto de cada chunk recuperado pelo file_search da execução.

    É o campo "contexts" que o RAGAS espera (faithfulness, context_precision,
    context_recall) — precisa do texto do chunk em si, não só do score que
    calcular_rag_score() já usa. Requer include=["file_search_call.results"]
    na chamada, igual ao RAG Score.

    Deduplicado (mantendo a ordem de primeira ocorrência): buscas diferentes
    (ex.: uma por tipo de artefato, ver passo 2 do PROCESSO DE TRABALHO)
    costumam bater no mesmo chunk mais de uma vez. Sem isso, o pool de
    contexto enviado ao RAGAS fica inflado com texto repetido, o que torna
    artificialmente mais fácil pro juiz "achar suporte" pra qualquer
    afirmação — visto em execuções reais: 40%/22% dos chunks eram duplicatas.
    """
    vistos = set()
    contextos = []
    for item in response.output:
        if hasattr(item, "type") and item.type == "file_search_call":
            resultados = getattr(item, "results", None) or []
            for r in resultados:
                texto = getattr(r, "text", None)
                if texto and texto not in vistos:
                    vistos.add(texto)
                    contextos.append(texto)
    return contextos


def extrair_tokens(response) -> dict:
    n_buscas = sum(
        1 for item in response.output
        if hasattr(item, "type") and item.type == "file_search_call"
    )
    usage = getattr(response, "usage", None)
    if not usage:
        return {"input": 0, "output": 0, "reasoning": 0, "total": 0, "cached": 0, "buscas": n_buscas}
    cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0
    return {
        "input": usage.input_tokens,
        "output": usage.output_tokens,
        "reasoning": usage.output_tokens_details.reasoning_tokens,
        "total": usage.total_tokens,
        "cached": cached,
        "buscas": n_buscas,
    }


def calcular_custo_usd(modelo: str, tokens: dict) -> dict:
    preco = PRECOS_USD.get(modelo)
    if not preco:
        return {"input": 0.0, "output": 0.0, "file_search": 0.0, "total": 0.0}

    tokens_normais = tokens.get("input", 0) - tokens.get("cached", 0)
    custo_input = (
        tokens_normais * preco["input"]
        + tokens.get("cached", 0) * preco["cached_input"]
    ) / 1_000_000
    custo_output = tokens.get("output", 0) * preco["output"] / 1_000_000
    custo_busca = tokens.get("buscas", 0) * PRECO_FILE_SEARCH_POR_1K_CHAMADAS / 1000

    return {
        "input": round(custo_input, 6),
        "output": round(custo_output, 6),
        "file_search": round(custo_busca, 6),
        "total": round(custo_input + custo_output + custo_busca, 6),
    }


# Erros do lado da OpenAI que costumam ser passageiros — vale tentar de novo
# em vez de falhar a execução inteira na primeira ocorrência.
ERROS_TRANSITORIOS = {"server_error", "server_is_overloaded", "rate_limit_exceeded"}


def elicitar_requisitos(
    api_key: str,
    model: str,
    vs_a_id: str,
    vs_b_id: str,
    contexto: str,
    texto_cenario: str,
    on_progress=None,
    max_tentativas: int = 3,
) -> tuple[dict, float, float, dict, list[str]]:
    # texto_cenario vai direto na mensagem em vez de só ficar disponível via
    # file_search em vs_a_id: quando os dois Vector Stores (A e B) são
    # passados na mesma chamada de file_search, a API faz um ranking
    # combinado — e o único documento de cenário (informal, poucas páginas)
    # sistematicamente perdia pros 7 documentos de referência bem curados do
    # VS B em queries genéricas, mesmo com o cenário perfeitamente indexado.
    # Resultado observado repetidas vezes: o modelo nunca via o conteúdo real
    # do cenário e ou desistia ("nenhum documento disponível") ou reproduzia
    # um exemplo fictício da base de conhecimento como se fosse o projeto.
    # Todos os 9 cenários de teste têm < 1100 tokens, então incluir o texto
    # inteiro é barato — VS A continua no file_search só como apoio pontual.
    instrucoes = PROMPT_SISTEMA
    if contexto.strip():
        instrucoes += (
            "\n\nOBSERVAÇÕES ADICIONAIS DO USUÁRIO (contexto extra para a análise):\n"
            f"{contexto.strip()}"
        )

    vs_ids = [vs_a_id]
    if vs_b_id:
        vs_ids.append(vs_b_id)

    max_wait = TIMEOUTS.get(model, 300)

    # A geração roda em "background": a chamada de criação retorna quase
    # na hora e o resultado é obtido por polling. Antes, a chamada ficava
    # bloqueada numa única conexão HTTP por vários minutos — o SDK trata
    # esse tipo de espera longa como timeout e refaz a chamada inteira
    # automaticamente (até 2x por padrão), o que triplicava a espera real
    # e fazia parecer que o agente nunca retornava, independente do modelo.
    client = OpenAI(api_key=api_key, timeout=30, max_retries=1)

    for tentativa in range(1, max_tentativas + 1):
        inicio = time.time()
        response = client.responses.create(
            model=model,
            background=True,
            store=True,  # obrigatório para usar background=True
            instructions=instrucoes,
            input=[{
                "role": "user",
                "content": (
                    "Analise o(s) documento(s) de cenário do projeto abaixo e gere "
                    "o SRS completo no formato JSON especificado nas instruções do "
                    "sistema. Siga o processo de trabalho descrito: faça buscas "
                    "dedicadas na base de conhecimento para cada tipo de artefato, "
                    "use-a como referência de estrutura e qualidade de escrita, e "
                    "valide a rastreabilidade entre os artefatos antes de finalizar."
                    "\n\nDocumento(s) de cenário:\n"
                    f"{texto_cenario.strip()}"
                ),
            }],
            text={"format": {"type": "json_object"}, "verbosity": "low"},
            reasoning={"effort": REASONING_EFFORT.get(model, "low")},
            tools=[{"type": "file_search", "vector_store_ids": vs_ids}],
            include=["file_search_call.results"],
        )

        try:
            while response.status in ("queued", "in_progress"):
                elapsed = time.time() - inicio
                if elapsed > max_wait:
                    client.responses.cancel(response.id)
                    raise TimeoutError(
                        f"O modelo {model} excedeu o limite de {max_wait}s. "
                        "Tente Nano ou Mini, ou reduza o tamanho do documento de entrada."
                    )
                if on_progress:
                    on_progress(elapsed)
                time.sleep(3)
                # "include" precisa ser passado em toda chamada que precise dos
                # dados extras (não fica "lembrado" do create()) — sem isso,
                # file_search_call.results vem None e o RAG Score sempre zera.
                response = client.responses.retrieve(
                    response.id, include=["file_search_call.results"]
                )

            if response.status == "completed":
                duracao_s = time.time() - inicio
                rag_score = calcular_rag_score(response)
                tokens = extrair_tokens(response)
                contextos = extrair_contextos(response)

                try:
                    dados = json.loads(response.output_text)
                except json.JSONDecodeError as e:
                    raise ValueError(f"O modelo não retornou JSON válido: {e}")

                return dados, rag_score, duracao_s, tokens, contextos

            erro = getattr(response, "error", None)
            codigo = getattr(erro, "code", None) if erro else None
            if codigo in ERROS_TRANSITORIOS and tentativa < max_tentativas:
                if on_progress:
                    on_progress(
                        0.0,
                        mensagem=(
                            f"Servidor da OpenAI sobrecarregado, "
                            f"tentando de novo ({tentativa}/{max_tentativas})..."
                        ),
                    )
                time.sleep(5 * tentativa)
                continue

            raise RuntimeError(
                f"O modelo retornou status '{response.status}'"
                + (f": {erro}" if erro else "")
            )
        finally:
            try:
                client.responses.delete(response.id)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Geração do .docx
# ---------------------------------------------------------------------------
AZUL_ESCURO = RGBColor(0x1F, 0x49, 0x7D)
AZUL_MEDIO  = RGBColor(0x2E, 0x74, 0xB5)

LABELS = {
    "pt": {
        "titulo_doc":        "Documento de Especificação de Requisitos de Software",
        "resumo":            "Resumo Executivo",
        "s1":                "1. Escopo do Projeto",
        "in_scope":          "Em Escopo (IN)",
        "out_scope":         "Fora de Escopo (OUT)",
        "premissas":         "Premissas",
        "restricoes":        "Restrições",
        "s2":                "2. Stakeholders",
        "stk_headers":       ["ID", "Nome / Papel", "Tipo", "Nível de Acesso", "Principais Necessidades"],
        "s3":                "3. Regras de Negócio",
        "fonte":             "Fonte",
        "excecoes":          "Exceções",
        "s4":                "4. Requisitos Funcionais",
        "rf_headers":        ["ID", "Título", "Descrição", "Prioridade", "Origem (STK)", "RN Assoc."],
        "s5":                "5. Requisitos Não Funcionais",
        "categoria":         "Categoria ISO 25010",
        "metrica":           "Métrica de aceitação",
        "verificacao":       "Método de verificação",
        "s6":                "6. Histórias de Usuário",
        "hu_prefix":         ("Como", "quero", "para"),
        "hu_rf":             "RF associado",
        "prioridade":        "Prioridade",
        "s7":                "7. Casos de Uso",
        "uc_ator":           "Ator principal",
        "uc_hu":             "HU relacionada",
        "uc_pre":            "Pré-condição",
        "uc_pos_ok":         "Pós-condição (sucesso)",
        "uc_pos_fail":       "Pós-condição (falha)",
        "uc_fluxo":          "Fluxo principal",
        "uc_alt":            "Fluxos alternativos",
        "uc_exc":            "Fluxos de exceção",
        "s8":                "8. Critérios de Aceite",
        "ca_ref":            "Ref",
        "ca_dado":           "Dado que",
        "ca_quando":         "Quando",
        "ca_entao":          "Então",
        "ca_metodo":         "Método",
        "s9":                "9. Glossário",
        "glos_headers":      ["Termo", "Definição"],
        "meta_titulo":       "Metadados de Geração",
        "meta_sistema":      "Sistema",
        "meta_modelo":       "Modelo utilizado",
        "meta_rag":          "RAG Score médio",
        "meta_rag_interp":   "Próximo de 1.0 = alta ancoragem nos documentos. Próximo de 0.0 = risco de alucinação.",
        "meta_tempo":        "Tempo de execução",
        "meta_tokens_in":    "Tokens de entrada (input)",
        "meta_tokens_out":   "Tokens de saída (output)",
        "meta_tokens_reas":  "Tokens de raciocínio (reasoning)",
        "meta_tokens_total": "Tokens totais",
        "meta_custo_input":  "Custo — entrada (USD)",
        "meta_custo_output": "Custo — saída (USD)",
        "meta_custo_busca":  "Custo — file_search (USD)",
        "meta_custo_total":  "Custo total estimado (USD)",
        "meta_rfs":          "Total de RFs",
        "meta_rnfs":         "Total de RNFs",
        "meta_rns":          "Total de RNs",
        "meta_hus":          "Total de HUs",
        "meta_cas":          "Total de CAs",
        "campo":             "Campo",
        "valor":             "Valor",
    },
    "en": {
        "titulo_doc":        "Software Requirements Specification",
        "resumo":            "Executive Summary",
        "s1":                "1. Project Scope",
        "in_scope":          "In Scope",
        "out_scope":         "Out of Scope",
        "premissas":         "Assumptions",
        "restricoes":        "Constraints",
        "s2":                "2. Stakeholders",
        "stk_headers":       ["ID", "Name / Role", "Type", "Access Level", "Main Needs"],
        "s3":                "3. Business Rules",
        "fonte":             "Source",
        "excecoes":          "Exceptions",
        "s4":                "4. Functional Requirements",
        "rf_headers":        ["ID", "Title", "Description", "Priority", "Source (STK)", "BR Ref."],
        "s5":                "5. Non-Functional Requirements",
        "categoria":         "ISO 25010 Category",
        "metrica":           "Acceptance metric",
        "verificacao":       "Verification method",
        "s6":                "6. User Stories",
        "hu_prefix":         ("As a", "I want", "so that"),
        "hu_rf":             "Associated FR",
        "prioridade":        "Priority",
        "s7":                "7. Use Cases",
        "uc_ator":           "Primary actor",
        "uc_hu":             "Related US",
        "uc_pre":            "Precondition",
        "uc_pos_ok":         "Postcondition (success)",
        "uc_pos_fail":       "Postcondition (failure)",
        "uc_fluxo":          "Main flow",
        "uc_alt":            "Alternative flows",
        "uc_exc":            "Exception flows",
        "s8":                "8. Acceptance Criteria",
        "ca_ref":            "Ref",
        "ca_dado":           "Given that",
        "ca_quando":         "When",
        "ca_entao":          "Then",
        "ca_metodo":         "Method",
        "s9":                "9. Glossary",
        "glos_headers":      ["Term", "Definition"],
        "meta_titulo":       "Generation Metadata",
        "meta_sistema":      "System",
        "meta_modelo":       "Model used",
        "meta_rag":          "Average RAG Score",
        "meta_rag_interp":   "Close to 1.0 = high grounding in documents. Close to 0.0 = hallucination risk.",
        "meta_tempo":        "Execution time",
        "meta_tokens_in":    "Input tokens",
        "meta_tokens_out":   "Output tokens",
        "meta_tokens_reas":  "Reasoning tokens",
        "meta_tokens_total": "Total tokens",
        "meta_custo_input":  "Cost — input (USD)",
        "meta_custo_output": "Cost — output (USD)",
        "meta_custo_busca":  "Cost — file_search (USD)",
        "meta_custo_total":  "Estimated total cost (USD)",
        "meta_rfs":          "Total FRs",
        "meta_rnfs":         "Total NFRs",
        "meta_rns":          "Total BRs",
        "meta_hus":          "Total USs",
        "meta_cas":          "Total ACs",
        "campo":             "Field",
        "valor":             "Value",
    },
}


def _h1(doc, texto):
    p = doc.add_heading(texto, level=1)
    if p.runs:
        p.runs[0].font.color.rgb = AZUL_ESCURO
    return p


def _h2(doc, texto):
    p = doc.add_heading(texto, level=2)
    if p.runs:
        p.runs[0].font.color.rgb = AZUL_MEDIO
    return p


def _body(doc, texto, negrito=False, tamanho=11):
    p = doc.add_paragraph()
    r = p.add_run(texto)
    r.bold = negrito
    r.font.size = Pt(tamanho)
    return p


def _tabela(doc, cabecalhos: list, linhas: list[list]):
    t = doc.add_table(rows=1, cols=len(cabecalhos))
    t.style = "Table Grid"
    # cabeçalho
    for i, cab in enumerate(cabecalhos):
        cell = t.rows[0].cells[i]
        cell.text = cab
        for run in cell.paragraphs[0].runs:
            run.bold = True
            run.font.size = Pt(9)
            run.font.color.rgb = AZUL_ESCURO
    # linhas
    for linha in linhas:
        row = t.add_row()
        for i, val in enumerate(linha):
            cell = row.cells[i]
            cell.text = str(val) if val else "—"
            for run in cell.paragraphs[0].runs:
                run.font.size = Pt(9)
    return t


def gerar_docx(dados: dict, modelo: str, rag_score: float, duracao_s: float, tokens: dict, custo: dict) -> bytes:
    idioma = dados.get("idioma", "pt") if dados.get("idioma") in ("pt", "en") else "pt"
    L = LABELS[idioma]

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = sec.bottom_margin = Inches(1.0)
    sec.left_margin = sec.right_margin = Inches(1.18)

    # --- Capa ---
    t = doc.add_heading(L["titulo_doc"], 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if t.runs:
        t.runs[0].font.color.rgb = AZUL_ESCURO

    sistema = dados.get("sistema", "Sistema")
    sub = doc.add_paragraph(sistema)
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if sub.runs:
        sub.runs[0].font.size = Pt(14)
        sub.runs[0].font.color.rgb = AZUL_MEDIO

    doc.add_paragraph()
    meta_line = doc.add_paragraph()
    meta_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    versao = dados.get("versao", "0.1").lstrip("v")
    meta_line.add_run(
        f"v{versao}  |  "
        f"{dados.get('data', '—')}  |  "
        f"{modelo}  |  "
        f"RAG Score: {rag_score:.4f}  |  "
        f"{duracao_s:.0f}s  |  "
        f"{tokens.get('total', 0)} tokens"
    ).font.size = Pt(9)

    doc.add_page_break()

    # --- Resumo executivo ---
    resumo = dados.get("resumo_executivo", "")
    if resumo:
        _h1(doc, L["resumo"])
        _body(doc, resumo)
        doc.add_paragraph()

    # --- Escopo ---
    esc = dados.get("escopo", {})
    if esc:
        _h1(doc, L["s1"])
        if esc.get("descricao"):
            _body(doc, esc["descricao"])
        doc.add_paragraph()
        if esc.get("em_escopo"):
            _h2(doc, L["in_scope"])
            for item in esc["em_escopo"]:
                doc.add_paragraph(item, style="List Bullet")
        if esc.get("fora_de_escopo"):
            _h2(doc, L["out_scope"])
            for item in esc["fora_de_escopo"]:
                doc.add_paragraph(item, style="List Bullet")
        if esc.get("premissas"):
            _h2(doc, L["premissas"])
            for item in esc["premissas"]:
                doc.add_paragraph(item, style="List Bullet")
        if esc.get("restricoes"):
            _h2(doc, L["restricoes"])
            for item in esc["restricoes"]:
                doc.add_paragraph(item, style="List Bullet")
        doc.add_paragraph()

    # --- Stakeholders ---
    stks = dados.get("stakeholders", [])
    if stks:
        _h1(doc, L["s2"])
        _tabela(doc,
            L["stk_headers"],
            [[s.get("id"), s.get("nome"), s.get("tipo"),
              s.get("nivel_acesso"), s.get("necessidades")] for s in stks]
        )
        doc.add_paragraph()

    # --- Regras de Negócio ---
    rns = dados.get("regras_de_negocio", [])
    if rns:
        _h1(doc, L["s3"])
        for rn in rns:
            _body(doc, f"{rn.get('id')} — {rn.get('titulo', '')}", negrito=True)
            _body(doc, rn.get("descricao", ""))
            if rn.get("fonte"):
                _body(doc, f"{L['fonte']}: {rn['fonte']}", tamanho=9)
            if rn.get("excecoes") and rn["excecoes"].lower() not in ("nenhuma", "none", ""):
                _body(doc, f"{L['excecoes']}: {rn['excecoes']}", tamanho=9)
            doc.add_paragraph()

    # --- Requisitos Funcionais ---
    rfs = dados.get("requisitos_funcionais", [])
    if rfs:
        _h1(doc, L["s4"])
        _tabela(doc,
            L["rf_headers"],
            [[r.get("id"), r.get("titulo"), r.get("descricao"),
              r.get("prioridade"), r.get("stakeholder_origem"), r.get("rn_associada")] for r in rfs]
        )
        doc.add_paragraph()

    # --- Requisitos Não Funcionais ---
    rnfs = dados.get("requisitos_nao_funcionais", [])
    if rnfs:
        _h1(doc, L["s5"])
        for rnf in rnfs:
            _body(doc, f"{rnf.get('id')} — {rnf.get('titulo', '')}", negrito=True)
            _body(doc, f"{L['categoria']}: {rnf.get('categoria_iso25010', '—')}", tamanho=9)
            _body(doc, rnf.get("descricao", ""))
            _body(doc, f"{L['metrica']}: {rnf.get('metrica_aceitacao', '—')}", tamanho=9)
            _body(doc, f"{L['verificacao']}: {rnf.get('metodo_verificacao', '—')}", tamanho=9)
            doc.add_paragraph()

    # --- Histórias de Usuário ---
    hus = dados.get("historias_de_usuario", [])
    if hus:
        _h1(doc, L["s6"])
        p1, p2, p3 = L["hu_prefix"]
        for hu in hus:
            _body(doc,
                f"{hu.get('id')} — {L['prioridade']}: {hu.get('prioridade', '—')}",
                negrito=True
            )
            _body(doc,
                f"{p1} {hu.get('como', '—')}, {p2} {hu.get('quero', '—')}, "
                f"{p3} {hu.get('para', '—')}."
            )
            _body(doc, f"{L['hu_rf']}: {hu.get('rf_associado', '—')}", tamanho=9)
            doc.add_paragraph()

    # --- Casos de Uso ---
    ucs = dados.get("casos_de_uso", [])
    if ucs:
        _h1(doc, L["s7"])
        for uc in ucs:
            _h2(doc, f"{uc.get('id')} — {uc.get('nome', '')}")
            campos_uc = [
                (L["uc_ator"],    uc.get("ator_principal")),
                (L["uc_hu"],      uc.get("hu_relacionada")),
                (L["uc_pre"],     uc.get("pre_condicao")),
                (L["uc_pos_ok"],  uc.get("pos_condicao_sucesso")),
                (L["uc_pos_fail"],uc.get("pos_condicao_falha")),
            ]
            for label, valor in campos_uc:
                if valor:
                    p = doc.add_paragraph()
                    p.add_run(f"{label}: ").bold = True
                    p.add_run(valor)
            if uc.get("fluxo_principal"):
                _body(doc, f"{L['uc_fluxo']}:", negrito=True)
                for passo in uc["fluxo_principal"]:
                    doc.add_paragraph(passo, style="List Number")
            if uc.get("fluxos_alternativos"):
                _body(doc, f"{L['uc_alt']}:", negrito=True)
                for fa in uc["fluxos_alternativos"]:
                    doc.add_paragraph(fa, style="List Bullet")
            if uc.get("fluxos_excecao"):
                _body(doc, f"{L['uc_exc']}:", negrito=True)
                for fe in uc["fluxos_excecao"]:
                    doc.add_paragraph(fe, style="List Bullet")
            doc.add_paragraph()

    # --- Critérios de Aceite ---
    cas = dados.get("criterios_de_aceite", [])
    if cas:
        _h1(doc, L["s8"])
        for ca in cas:
            _body(doc,
                f"{ca.get('id')} — {ca.get('titulo', '')}  |  "
                f"{L['ca_ref']}: {ca.get('rf_hu_ref', '—')}",
                negrito=True
            )
            _body(doc, f"{L['ca_dado']} {ca.get('dado', '—')},")
            _body(doc, f"{L['ca_quando']} {ca.get('quando', '—')},")
            _body(doc, f"{L['ca_entao']} {ca.get('entao', '—')}.")
            _body(doc, f"{L['ca_metodo']}: {ca.get('metodo_verificacao', '—')}", tamanho=9)
            doc.add_paragraph()

    # --- Glossário ---
    glos = dados.get("glossario", [])
    if glos:
        _h1(doc, L["s9"])
        _tabela(doc,
            L["glos_headers"],
            [[g.get("termo"), g.get("definicao")] for g in glos]
        )
        doc.add_paragraph()

    # --- Metadados ---
    doc.add_page_break()
    _h1(doc, L["meta_titulo"])
    _tabela(doc,
        [L["campo"], L["valor"]],
        [
            [L["meta_sistema"],   sistema],
            [L["meta_modelo"],    modelo],
            [L["meta_rag"],       str(rag_score)],
            ["RAG Score",         L["meta_rag_interp"]],
            [L["meta_tempo"],        f"{duracao_s:.1f}s"],
            [L["meta_tokens_in"],    str(tokens.get("input", 0))],
            [L["meta_tokens_out"],   str(tokens.get("output", 0))],
            [L["meta_tokens_reas"],  str(tokens.get("reasoning", 0))],
            [L["meta_tokens_total"], str(tokens.get("total", 0))],
            [L["meta_custo_input"],  f"{custo.get('input', 0):.6f}"],
            [L["meta_custo_output"], f"{custo.get('output', 0):.6f}"],
            [L["meta_custo_busca"],  f"{custo.get('file_search', 0):.6f}"],
            [L["meta_custo_total"],  f"{custo.get('total', 0):.6f}"],
            [L["meta_rfs"],       str(len(rfs))],
            [L["meta_rnfs"],      str(len(rnfs))],
            [L["meta_rns"],       str(len(rns))],
            [L["meta_hus"],       str(len(hus))],
            [L["meta_cas"],       str(len(cas))],
        ]
    )

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def renderizar_texto_srs(dados: dict) -> str:
    """Serializa o SRS gerado como texto plano corrido (não JSON, não .docx).

    É o campo "resposta" do export de avaliação RAGAS — texto legível fica
    mais próximo do que faithfulness/answer_relevancy esperam avaliar do que
    o JSON bruto, que tem muita sintaxe estrutural sem valor semântico.
    """
    linhas = []

    def _add(*partes):
        linhas.append(" ".join(str(p) for p in partes if p))

    linhas.append(f"Sistema: {dados.get('sistema', '')}")
    if dados.get("resumo_executivo"):
        linhas.append(f"\nResumo executivo: {dados['resumo_executivo']}")

    esc = dados.get("escopo", {})
    if esc:
        linhas.append(f"\nEscopo: {esc.get('descricao', '')}")
        for item in esc.get("em_escopo", []):
            _add("  Em escopo:", item)
        for item in esc.get("fora_de_escopo", []):
            _add("  Fora de escopo:", item)
        for item in esc.get("premissas", []):
            _add("  Premissa:", item)
        for item in esc.get("restricoes", []):
            _add("  Restrição:", item)

    if dados.get("stakeholders"):
        linhas.append("\nStakeholders:")
        for s in dados["stakeholders"]:
            _add(" ", s.get("id"), "-", s.get("nome"), f"({s.get('tipo')}):", s.get("necessidades"))

    if dados.get("regras_de_negocio"):
        linhas.append("\nRegras de negócio:")
        for rn in dados["regras_de_negocio"]:
            _add(" ", rn.get("id"), "-", f"{rn.get('titulo') or ''}:", rn.get("descricao"))

    if dados.get("requisitos_funcionais"):
        linhas.append("\nRequisitos funcionais:")
        for rf in dados["requisitos_funcionais"]:
            _add(" ", rf.get("id"), "-", f"{rf.get('titulo') or ''}:", rf.get("descricao"), f"[{rf.get('prioridade')}]")

    if dados.get("requisitos_nao_funcionais"):
        linhas.append("\nRequisitos não funcionais:")
        for rnf in dados["requisitos_nao_funcionais"]:
            _add(" ", rnf.get("id"), f"({rnf.get('categoria_iso25010')}) -", rnf.get("descricao"),
                 "| Métrica:", rnf.get("metrica_aceitacao"))

    if dados.get("historias_de_usuario"):
        linhas.append("\nHistórias de usuário:")
        for hu in dados["historias_de_usuario"]:
            _add(" ", hu.get("id"), "- Como", f"{hu.get('como') or ''}, quero", f"{hu.get('quero') or ''}, para", hu.get("para"))

    if dados.get("casos_de_uso"):
        linhas.append("\nCasos de uso:")
        for uc in dados["casos_de_uso"]:
            _add(" ", uc.get("id"), "-", uc.get("nome"), "| Ator:", uc.get("ator_principal"))
            for passo in uc.get("fluxo_principal", []):
                _add("   ", passo)

    if dados.get("criterios_de_aceite"):
        linhas.append("\nCritérios de aceite:")
        for ca in dados["criterios_de_aceite"]:
            _add(" ", ca.get("id"), "- Dado", f"{ca.get('dado') or ''}, quando", f"{ca.get('quando') or ''}, então", ca.get("entao"))

    if dados.get("glossario"):
        linhas.append("\nGlossário:")
        for g in dados["glossario"]:
            _add(" ", f"{g.get('termo') or ''}:", g.get("definicao"))

    return "\n".join(linhas)


def gerar_json_ragas(
    dados: dict,
    modelo: str,
    contexto_usuario: str,
    texto_cenario: str,
    contextos: list[str],
    rag_score: float,
    ground_truth: str | None = None,
    gabarito_artefatos: dict | None = None,
) -> bytes:
    """Export por execução com tudo que o RAGAS precisa (fase 1 e fase 2),
    mais os artefatos estruturados e o gabarito de RF/RNF/RN/HU/UC/CA/
    stakeholders/escopo usados na fase 3 (precision/recall/F1 clássicos).

    Formato: {question, answer, contexts} + ground_truth + artefatos +
    gabarito_artefatos. No fluxo normal do Streamlit (documento arbitrário
    do usuário) não existe gabarito conhecido — ground_truth e
    gabarito_artefatos ficam None, e as métricas que dependem deles são
    puladas na avaliação. Só rodar_execucao.py, que lida com os 9 Project
    Scenario numerados de teste, sabe qual gabarito usar e passa esses
    parâmetros. Gerado à parte do .docx/.csv, pra ser consumido depois, um
    arquivo por vez, por avaliar_ragas.py / avaliar_qualidade.py /
    avaliar_classificacao.py — nunca dentro do fluxo do Streamlit.
    """
    pergunta = (
        "Analise o(s) documento(s) de cenário do projeto e gere o SRS completo "
        "no formato especificado, seguindo o processo de trabalho: buscas "
        "dedicadas na base de conhecimento para cada tipo de artefato, "
        "rastreabilidade validada entre os artefatos.\n\n"
        f"Documento(s) de cenário:\n{texto_cenario}"
    )
    if contexto_usuario.strip():
        pergunta += f"\n\nObservações adicionais do usuário:\n{contexto_usuario.strip()}"

    export = {
        "sistema": dados.get("sistema", ""),
        "modelo": modelo,
        "data_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": pergunta,
        "answer": renderizar_texto_srs(dados),
        "contexts": contextos,
        "ground_truth": ground_truth,
        "rag_score": rag_score,
        "artefatos": {
            "escopo": dados.get("escopo", {}),
            "stakeholders": dados.get("stakeholders", []),
            "regras_de_negocio": dados.get("regras_de_negocio", []),
            "requisitos_funcionais": dados.get("requisitos_funcionais", []),
            "requisitos_nao_funcionais": dados.get("requisitos_nao_funcionais", []),
            "historias_de_usuario": dados.get("historias_de_usuario", []),
            "casos_de_uso": dados.get("casos_de_uso", []),
            "criterios_de_aceite": dados.get("criterios_de_aceite", []),
        },
        "gabarito_artefatos": gabarito_artefatos,
    }
    return json.dumps(export, ensure_ascii=False, indent=2).encode("utf-8")


def gerar_csv_execucao(dados: dict, modelo: str, rag_score: float, duracao_s: float, tokens: dict, custo: dict) -> bytes:
    linha = {
        "data_execucao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sistema": dados.get("sistema", ""),
        "modelo": modelo,
        "rag_score": rag_score,
        "tempo_execucao_s": round(duracao_s, 1),
        "tokens_input": tokens.get("input", 0),
        "tokens_cached": tokens.get("cached", 0),
        "tokens_output": tokens.get("output", 0),
        "tokens_reasoning": tokens.get("reasoning", 0),
        "tokens_total": tokens.get("total", 0),
        "file_search_chamadas": tokens.get("buscas", 0),
        "custo_input_usd": custo.get("input", 0),
        "custo_output_usd": custo.get("output", 0),
        "custo_file_search_usd": custo.get("file_search", 0),
        "custo_total_usd": custo.get("total", 0),
        "total_rfs": len(dados.get("requisitos_funcionais", [])),
        "total_rnfs": len(dados.get("requisitos_nao_funcionais", [])),
        "total_hus": len(dados.get("historias_de_usuario", [])),
        "total_cas": len(dados.get("criterios_de_aceite", [])),
    }

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(linha.keys()))
    writer.writeheader()
    writer.writerow(linha)
    return buf.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------------------
# Interface Streamlit
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Elicitação de Requisitos — Univille", layout="centered")

# Sidebar — configurações
with st.sidebar:
    st.header("Configurações")

    modelo_label = st.radio(
        "Modelo OpenAI",
        options=list(MODELOS.keys()),
        index=0,
    )
    modelo_selecionado = MODELOS[modelo_label]

    # Estimativas realistas: o SRS é gerado por completo em uma única
    # chamada, com busca em 2 vector stores (documento do usuário + base de
    # conhecimento) — isso é bem mais lento do que uma resposta simples.
    tempo_estimado = {
        "gpt-5.6-luna":  "~1–2 min",
        "gpt-5.6-terra": "~2–4 min",
        "gpt-5.6-sol":   "~3–8 min",
    }
    st.caption(f"Tempo estimado: {tempo_estimado.get(modelo_selecionado, '—')}")

    st.divider()

    if VS_B_ID:
        st.success("Vector Store B configurado.")
        st.caption(f"ID: `{VS_B_ID[:20]}...`")
    else:
        st.warning(
            "Vector Store B não configurado. "
            "Crie a vector store B e defina VS_B_ID no .env (ver README)."
        )

    st.divider()
    st.caption("Univille · Elicitação de Requisitos com RAG")

# Corpo principal
st.title("Modelo Inteligente para Elicitação de Requisitos")
st.markdown("Envie os documentos do projeto e o agente gerará o SRS completo.")
st.divider()

api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")

contexto = st.text_area(
    "Observações adicionais (opcional)",
    placeholder="Informações extras, restrições específicas ou foco da análise.",
    height=100,
)

uploaded_files = st.file_uploader(
    "Documentos do projeto",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} arquivo(s) carregado(s).")
    for f in uploaded_files:
        st.caption(f"• {f.name}")

st.divider()

# Session state
for key in (
    "srs_dados", "srs_docx", "rag_score", "modelo_usado", "duracao_s",
    "tokens", "custo", "contextos", "texto_cenario", "contexto_usuario",
):
    if key not in st.session_state:
        st.session_state[key] = None

# Botão principal
if st.button("Iniciar elicitação de requisitos", type="primary"):
    if not api_key:
        st.warning("Informe a API Key.")
        st.stop()
    if not uploaded_files:
        st.warning("Envie pelo menos um documento de projeto.")
        st.stop()
    if not VS_B_ID:
        st.error("Vector Store B não configurado. Defina VS_B_ID no .env (ver README).")
        st.stop()

    # Cliente para o Vector Store A usa timeout generoso (upload pode ser lento)
    client = OpenAI(api_key=api_key, timeout=120)

    # None até criar_vector_store_usuario() retornar; volta a None assim que
    # descartar_vector_store_sessao() já rodou com sucesso — o finally usa
    # esse estado para saber se ainda precisa tentar limpar (fallback) ou se
    # o Vector Store temporário já foi removido no fluxo normal abaixo.
    vs_a_id = None

    try:
        with st.status("Processando...", expanded=True) as status:
            # Extração de texto bruto pro export RAGAS (independente do VS A —
            # feita aqui, e não no download, porque uploaded_files reflete o
            # que estava na tela nesta execução; o widget pode mudar depois.
            texto_cenario = extrair_texto_cenario(uploaded_files)

            st.write("Enviando documentos para o Vector Store A...")
            vs_a_id = criar_vector_store_usuario(client, uploaded_files)
            st.write(f"✓ Vector Store A criado: `{vs_a_id}`")

            st.write(f"Consultando modelo `{modelo_selecionado}` com RAG...")
            progresso = st.empty()

            def _on_progress(elapsed: float, mensagem: str = None) -> None:
                progresso.caption(mensagem or f"Aguardando resposta do modelo... {elapsed:.0f}s")

            dados, rag_score, duracao_s, tokens, contextos = elicitar_requisitos(
                api_key, modelo_selecionado, vs_a_id, VS_B_ID, contexto, texto_cenario,
                on_progress=_on_progress,
            )
            custo = calcular_custo_usd(modelo_selecionado, tokens)
            progresso.empty()
            st.write(
                f"✓ Requisitos elicitados em **{duracao_s:.0f}s**. "
                f"RAG Score: **{rag_score:.4f}** | "
                f"Tokens: {tokens['input']} in / {tokens['output']} out "
                f"({tokens['reasoning']} reasoning) / {tokens['total']} total | "
                f"Custo estimado: **US$ {custo['total']:.4f}**"
            )

            # VS A já cumpriu seu papel (file_search já rodou) — descarta
            # aqui, antes da geração do .docx, para não deixar nada pra trás
            # mesmo que a etapa seguinte falhe.
            st.write("Removendo Vector Store temporário...")
            descartar_vector_store_sessao(client, vs_a_id, on_warning=st.warning)
            vs_a_id = None
            st.write("✓ Vector Store temporário removido do storage.")

            st.write("Gerando documento .docx...")
            docx_bytes = gerar_docx(dados, modelo_selecionado, rag_score, duracao_s, tokens, custo)
            st.write("✓ Documento gerado com sucesso.")

            status.update(label="Concluído!", state="complete")

        st.session_state.srs_dados = dados
        st.session_state.srs_docx = docx_bytes
        st.session_state.rag_score = rag_score
        st.session_state.modelo_usado = modelo_selecionado
        st.session_state.duracao_s = duracao_s
        st.session_state.tokens = tokens
        st.session_state.custo = custo
        st.session_state.contextos = contextos
        st.session_state.texto_cenario = texto_cenario
        st.session_state.contexto_usuario = contexto

    except Exception as e:
        import traceback
        traceback.print_exc()  # detalhe completo no terminal, para diagnóstico
        st.error(f"Erro durante a elicitação: {e}")
        st.stop()

    finally:
        # Fallback: só entra aqui se algo falhou ANTES do descarte inline
        # acima (ex.: elicitar_requisitos levantou exceção) — nesse caso
        # vs_a_id ainda aponta pro Vector Store criado nesta execução.
        if vs_a_id:
            descartar_vector_store_sessao(client, vs_a_id, on_warning=st.warning)

# Resultados
if st.session_state.srs_dados:
    dados = st.session_state.srs_dados
    rag = st.session_state.rag_score
    modelo = st.session_state.modelo_usado
    duracao_s = st.session_state.duracao_s
    tokens = st.session_state.tokens
    custo = st.session_state.custo

    st.divider()
    st.subheader(f"SRS — {dados.get('sistema', 'Sistema')}")

    # Métricas de resumo
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("RAG Score", f"{rag:.4f}")
    col2.metric("RFs", len(dados.get("requisitos_funcionais", [])))
    col3.metric("RNFs", len(dados.get("requisitos_nao_funcionais", [])))
    col4.metric("HUs", len(dados.get("historias_de_usuario", [])))
    col5.metric("CAs", len(dados.get("criterios_de_aceite", [])))

    col6, col7, col8, col9 = st.columns(4)
    col6.metric("Tempo de execução", f"{duracao_s:.0f}s")
    col7.metric("Tokens entrada", tokens["input"])
    col8.metric("Tokens saída", tokens["output"])
    col9.metric("Tokens reasoning", tokens["reasoning"])

    col10, col11, col12, col13 = st.columns(4)
    col10.metric("Custo — entrada", f"US$ {custo['input']:.4f}")
    col11.metric("Custo — saída", f"US$ {custo['output']:.4f}")
    col12.metric("Custo — file_search", f"US$ {custo['file_search']:.4f}")
    col13.metric("Custo total estimado", f"US$ {custo['total']:.4f}")

    st.caption(
        "RAG Score: média dos scores de relevância dos chunks recuperados pelo file_search. "
        "Próximo de 1.0 = alta ancoragem nos documentos; próximo de 0.0 = risco de alucinação."
    )
    st.caption(
        f"Custo estimado com base na tabela de preços oficial da OpenAI para {modelo} "
        "(conferida em 15/08/2026). Não inclui o custo de armazenamento do Vector Store "
        "($0.10/GB/dia), que é recorrente e não atribuível a uma execução isolada."
    )

    # Botão de download
    st.download_button(
        label="Baixar SRS (.docx)",
        data=st.session_state.srs_docx,
        file_name=f"SRS_{dados.get('sistema', 'projeto').replace(' ', '_')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
    )

    # Labels do preview adaptados ao idioma detectado
    _idioma = dados.get("idioma", "pt") if dados.get("idioma") in ("pt", "en") else "pt"
    _L = LABELS[_idioma]
    _hu1, _hu2, _hu3 = _L["hu_prefix"]

    with st.expander(_L["s1"]):
        esc = dados.get("escopo", {})
        st.write(f"**{_L['in_scope']}:**")
        for i in esc.get("em_escopo", []):
            st.write(f"• {i}")
        st.write(f"**{_L['out_scope']}:**")
        for i in esc.get("fora_de_escopo", []):
            st.write(f"• {i}")

    with st.expander(f"{_L['s4']} ({len(dados.get('requisitos_funcionais', []))})"):
        for rf in dados.get("requisitos_funcionais", []):
            st.markdown(f"**{rf.get('id')} — {rf.get('titulo')}** `{rf.get('prioridade')}`")
            st.write(rf.get("descricao"))

    with st.expander(f"{_L['s5']} ({len(dados.get('requisitos_nao_funcionais', []))})"):
        for rnf in dados.get("requisitos_nao_funcionais", []):
            st.markdown(f"**{rnf.get('id')} — {rnf.get('titulo')}** `{rnf.get('categoria_iso25010')}`")
            st.write(rnf.get("descricao"))
            st.caption(f"{_L['metrica']}: {rnf.get('metrica_aceitacao')}")

    with st.expander(f"{_L['s6']} ({len(dados.get('historias_de_usuario', []))})"):
        for hu in dados.get("historias_de_usuario", []):
            st.markdown(f"**{hu.get('id')}** `{hu.get('prioridade')}`")
            st.write(
                f"{_hu1} **{hu.get('como')}**, {_hu2} **{hu.get('quero')}**, "
                f"{_hu3} **{hu.get('para')}**."
            )

    with st.expander(f"{_L['s8']} ({len(dados.get('criterios_de_aceite', []))})"):
        for ca in dados.get("criterios_de_aceite", []):
            st.markdown(f"**{ca.get('id')} — {ca.get('titulo')}** | {_L['ca_ref']}: `{ca.get('rf_hu_ref')}`")
            st.write(f"**{_L['ca_dado']}** {ca.get('dado')},")
            st.write(f"**{_L['ca_quando']}** {ca.get('quando')},")
            st.write(f"**{_L['ca_entao']}** {ca.get('entao')}.")

    with st.expander("JSON (debug)"):
        st.json(dados)

    st.divider()
    csv_bytes = gerar_csv_execucao(dados, modelo, rag, duracao_s, tokens, custo)
    st.download_button(
        label="Baixar dados da execução (.csv)",
        data=csv_bytes,
        file_name=f"execucao_{dados.get('sistema', 'projeto').replace(' ', '_')}.csv",
        mime="text/csv",
    )

    ragas_bytes = gerar_json_ragas(
        dados, modelo,
        st.session_state.contexto_usuario or "",
        st.session_state.texto_cenario or "",
        st.session_state.contextos or [],
        rag,
    )
    st.download_button(
        label="Baixar dados para avaliação RAGAS (.json)",
        data=ragas_bytes,
        file_name=f"ragas_{dados.get('sistema', 'projeto').replace(' ', '_')}_{modelo}.json",
        mime="application/json",
    )
    st.caption(
        "Arquivo de entrada para o script offline avaliar_ragas.py (roda separado deste app). "
        "Contém pergunta, resposta e contextos recuperados desta execução."
    )
