"""Confere se os documentos das partes anteriores (Parte 1: sei-automacao,
Parte 2: sei-automaçaoPt2) estão presentes na árvore de um processo do SEI
— antes de começar a incluir os documentos da Parte 3, confirma que as
partes anteriores realmente rodaram nesse processo.

Uso:
    python -m src.verificar_documentos_anteriores --numero "00000.000000/0000-00"
"""

import argparse

from playwright.sync_api import Page, sync_playwright

from . import config
from .browser import abrir_sessao
from .sei_page import documento_existe_na_arvore, pesquisar_processo, screenshot


def documentos_anteriores_faltando(page: Page) -> list[str]:
    """Retorna os nomes (Parte 1 + Parte 2) que NÃO foram encontrados na
    árvore do processo atualmente aberto na tela — lista vazia se todos
    estiverem presentes. Usado como trava de segurança antes de incluir
    qualquer documento da Parte 3.
    """
    esperados = config.DOCUMENTOS_PADRAO_PARTE1 + config.DOCUMENTOS_PADRAO_PARTE2
    return [nome for nome in esperados if not documento_existe_na_arvore(page, nome)]


def verificar_e_reportar(page: Page) -> bool:
    """Confere os 9 documentos das Partes 1 e 2 na árvore do processo
    atualmente aberto na tela, imprimindo o resultado (OK/FALTANDO) de cada
    um. Retorna True se todos os 9 estiverem presentes.

    Usada tanto pelo script standalone deste módulo quanto pelo main.py da
    Parte 3, como trava de segurança antes de incluir qualquer documento
    novo.
    """
    print("\nConferindo documentos da Parte 1 no processo:\n")
    tudo_ok = True
    for nome in config.DOCUMENTOS_PADRAO_PARTE1:
        achou = documento_existe_na_arvore(page, nome)
        print(f"  [{'OK' if achou else 'FALTANDO'}] {nome}")
        if not achou:
            tudo_ok = False

    print("\nConferindo documentos da Parte 2 no processo:\n")
    for nome in config.DOCUMENTOS_PADRAO_PARTE2:
        achou = documento_existe_na_arvore(page, nome)
        print(f"  [{'OK' if achou else 'FALTANDO'}] {nome}")
        if not achou:
            tudo_ok = False

    print(
        "\n"
        + (
            "TUDO OK — Partes 1 e 2 completas, pode incluir os documentos da Parte 3."
            if tudo_ok
            else "FALTAM documentos — confira a árvore do processo antes de continuar."
        )
    )
    return tudo_ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--numero",
        type=str,
        required=True,
        help="Número do processo SEI a conferir (ex.: 00000.000000/0000-00).",
    )
    args = parser.parse_args()

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)

        print(f"\nPesquisando processo {args.numero}...")
        pesquisar_processo(page, args.numero)
        screenshot(page, "verificacao_documentos_anteriores")

        verificar_e_reportar(page)


if __name__ == "__main__":
    main()
