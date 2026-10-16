"""
Configuração central da automação SEI (Pt3).

Terceira automação sobre os mesmos processos das Partes 1/2 — 7 documentos
novos por processo, a maioria nativa do SEI (editor de texto rico), um
deles anexo (PDF). Reaproveita a mesma conexão/navegação já testada nas
partes anteriores, mas tem status/painel PRÓPRIOS (decisão consciente:
partes separadas, ver conversa — perde a visão unificada entre partes em
troca de isolamento total entre elas).
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

SEI_URL = "https://sei.exemplo.gov.br"  # URL real da sua instância vai em config_local.py

# Porta de depuração remota do Chrome que você abre manualmente antes de
# rodar a automação (veja README.md -> "Conectar num Chrome já logado").
CDP_URL = "http://localhost:9222"

# ---------------------------------------------------------------------------
# Seletores da interface do SEI (mesmos placeholders das partes anteriores —
# a navegação robusta é por rótulo/texto visível nos helpers de
# sei_page.py; estes SELECTORS entram só como fallback).
# ---------------------------------------------------------------------------
SELECTORS = {
    "frame_conteudo": "ifrVisualizacao",  # TODO — nome ou seletor do iframe principal
    "campo_nivel_acesso_publico": "#optPublico",  # TODO
    "campo_nivel_acesso_restrito": "#optRestrito",  # TODO
    "campo_nivel_acesso_sigiloso": "#optSigiloso",  # TODO
    "campo_hipotese_legal": "#selHipoteseLegal",
    "campo_nome_arvore": "#txtNomeArvore",  # TODO
    "campo_data_documento": "#txtDataDocumento",  # TODO
}

# ---------------------------------------------------------------------------
# Comportamento
# ---------------------------------------------------------------------------
TIMEOUT_PADRAO_MS = 15_000

# ---------------------------------------------------------------------------
# Documentos das partes anteriores — trava de segurança
# ---------------------------------------------------------------------------
# Nome (ou trecho) como aparece na árvore do processo — mesmos valores de
# sei-automacao/src/config.py (NOME_ARVORE_*). Antes de incluir qualquer
# documento da Parte 3, confere se os 4 da Parte 1 já estão na árvore.
DOCUMENTOS_PADRAO_PARTE1 = [
    "Nota Técnica Nº X/AAAA/UNIDADE",
    "Despacho - Plano de Trabalho",
    "Despacho - Unificação de Planilhas",
    "Despacho - Aprovação do Plano de Trabalho",
]

# Mesma ideia, mas pros 5 documentos pessoais da Pt2 (valores de
# sei-automaçaoPt2/src/config.py -> NOMES_ARVORE_DOCUMENTOS_PESSOAIS).
DOCUMENTOS_PADRAO_PARTE2 = [
    "Cadastro dados pessoais",
    "Cadastro dados funcionais",
    "Ficha financeira",
    "Declaração de Não Ajuizamento de Ação Judicial",
    "Planilha de Cálculo",
]

# ---------------------------------------------------------------------------
# Documentos da Parte 3 (720 casos) — lista dos 7 confirmada, ver README.md.
# ---------------------------------------------------------------------------

# Número SEI do "Documento Modelo" de onde cada documento nativo copia o
# conteúdo inicial (tela "Gerar Documento" -> Texto Inicial -> Documento
# Modelo). Os números reais ficam em config_local.py.
DOCUMENTOS_MODELO = {
    "rpdea": "00000001",
    "checklist": "00000002",
    "nota_tecnica": "00000003",
    "tdea": "00000004",
    "despacho": "00000005",
}

# Planilha com os dados de cada caso (720 linhas: 1 por pessoa/processo) —
# cada linha tem os dados que entram nos documentos nativos (substituição
# de campo em negrito, ver src/personalizar_documento.py) e o número do
# processo SEI correspondente (não precisa bater com nenhum processo da
# Parte 1/2 por nome — é só a chave de junção planilha <-> SEI).
PLANILHA_PESSOAS = BASE_DIR / "data" / "Editaveis_PT1.xlsx"
PLANILHA_COLUNA_PROCESSO_SEI = "Processo_SEI"

# Painel HTML do lote atual. O lote PT1 mantém o nome original; os outros
# ganham sufixo (ex.: painel_documentos_PT4.html) — ver definir_lote().
LOTE = "PT1"
PAINEL_HTML = BASE_DIR / "painel_documentos.html"


def definir_lote(lote: str) -> None:
    """Troca a planilha e o painel usados pela automação (--lote do
    main.py). O status (status/processos_parte3.json) continua um só pra
    todos os lotes — é indexado pelo número do processo, que não se repete
    entre planilhas."""
    global LOTE, PLANILHA_PESSOAS, PAINEL_HTML
    LOTE = lote.upper()
    PLANILHA_PESSOAS = BASE_DIR / "data" / f"Editaveis_{LOTE}.xlsx"
    PAINEL_HTML = BASE_DIR / ("painel_documentos.html" if LOTE == "PT1" else f"painel_documentos_{LOTE}.html")


# ---------------------------------------------------------------------------
# Overrides locais
# ---------------------------------------------------------------------------
# Os valores acima são exemplos genéricos. Dados reais (URL do SEI, nomes
# dos documentos da Parte 1, números dos Documentos Modelo) ficam em
# src/config_local.py, que não é versionado — veja src/config_local.example.py.
try:
    from .config_local import *  # noqa: F401,F403
except ImportError:
    pass
