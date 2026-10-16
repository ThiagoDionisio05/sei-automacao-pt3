"""Inclui o 6º documento da Parte 3 — "Comprovante de Cadastro do processo
SIAPE" — como Documento Externo SEM anexo (só o registro na árvore),
Nível de Acesso Restrito + Hipótese Legal "Informação Pessoal".

Confere os 9 documentos das Partes 1/2 antes (trava de segurança).

Uso:
    python -m src.incluir_comprovante_siape --numero "00000.000000/0000-00"
"""

import argparse
import sys

from playwright.sync_api import sync_playwright

from .browser import abrir_sessao
from .documento_externo import incluir_documento_externo
from .sei_page import marcar_tempo, pesquisar_processo, screenshot
from .verificar_documentos_anteriores import verificar_e_reportar

NOME_ARVORE = "Comprovante de Cadastro do processo SIAPE"
HIPOTESE_LEGAL = "Informação Pessoal"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--numero", required=True, help="Número do processo SEI.")
    args = parser.parse_args()

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)
        marcar_tempo("conexão")

        print(f"\nPesquisando processo {args.numero}...")
        pesquisar_processo(page, args.numero)
        screenshot(page, "siape_00_processo_aberto")
        marcar_tempo("pesquisar processo")

        if not verificar_e_reportar(page):
            print("\nParando aqui — complete os documentos das Partes 1 e 2 primeiro.")
            sys.exit(1)
        marcar_tempo("verificar documentos anteriores")

        incluir_documento_externo(
            page,
            NOME_ARVORE,
            arquivo_anexo=None,
            nivel_acesso="restrito",
            hipotese_legal=HIPOTESE_LEGAL,
        )
        screenshot(page, "siape_01_salvo")

        print(
            "\nDocumento incluído e salvo. Confira screenshots/siape_01_salvo.png "
            "e a árvore do processo."
        )


if __name__ == "__main__":
    main()
