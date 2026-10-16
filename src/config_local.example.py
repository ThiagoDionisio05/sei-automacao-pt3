"""
Modelo de configuração local.

Copie este arquivo para `src/config_local.py` e preencha com seus dados
reais. O `config_local.py` está no .gitignore — nunca é versionado — e
sobrescreve os valores de exemplo de `src/config.py`.
"""

# Endereço da sua instância do SEI
SEI_URL = "https://sei.seuorgao.gov.br"

# Nomes (ou trechos) dos 4 documentos da Parte 1, como aparecem na árvore
DOCUMENTOS_PADRAO_PARTE1 = [
    "Nota Técnica Nº X/AAAA/UNIDADE",
    "Despacho - Plano de Trabalho",
    "Despacho - Unificação de Planilhas",
    "Despacho - Aprovação do Plano de Trabalho",
]

# Número SEI do Documento Modelo de cada documento nativo
DOCUMENTOS_MODELO = {
    "rpdea": "00000001",
    "checklist": "00000002",
    "nota_tecnica": "00000003",
    "tdea": "00000004",
    "despacho": "00000005",
}
