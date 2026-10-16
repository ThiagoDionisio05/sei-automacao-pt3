"""Inclui o 4º documento da Parte 3 — "Anexo - Ateste Orçamentário" — como
Documento Externo (anexo de PDF), igual ao fluxo da Pt1/Pt2.

Confere os 9 documentos das Partes 1/2 antes (trava de segurança).

Uso:
    python -m src.incluir_ateste_orcamentario --numero "00000.000000/0000-00"
"""

import argparse
import sys

from playwright.sync_api import sync_playwright

from . import config
from .browser import abrir_sessao
from .documento_externo import incluir_documento_externo
from .sei_page import marcar_tempo, pesquisar_processo, screenshot
from .verificar_documentos_anteriores import verificar_e_reportar

NOME_ARVORE = "- Ateste Orçamentário"  # o SEI já prefixa "Anexo" sozinho na árvore
ARQUIVO_PDF = config.BASE_DIR / "src" / "PDFs" / "Anexo_Ateste_Orcamentario.pdf"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--numero", required=True, help="Número do processo SEI.")
    args = parser.parse_args()

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)
        marcar_tempo("conexão")

        print(f"\nPesquisando processo {args.numero}...")
        pesquisar_processo(page, args.numero)
        screenshot(page, "ateste_00_processo_aberto")
        marcar_tempo("pesquisar processo")

        if not verificar_e_reportar(page):
            print("\nParando aqui — complete os documentos das Partes 1 e 2 primeiro.")
            sys.exit(1)
        marcar_tempo("verificar documentos anteriores")

        incluir_documento_externo(page, NOME_ARVORE, ARQUIVO_PDF, nivel_acesso="publico")
        screenshot(page, "ateste_01_salvo")

        print(
            "\nDocumento incluído e salvo. Confira screenshots/ateste_01_salvo.png "
            "e a árvore do processo."
        )


if __name__ == "__main__":
    main()
