"""Teste isolado da personalização de documento nativo: cria o RPDEA,
substitui os campos em negrito com os dados da planilha (`data/pessoas.csv`)
pro processo informado, e PARA (não clica em Salvar dentro do editor) — só
tira um screenshot, pra confirmar visualmente que a substituição funcionou
antes de automatizar esse passo final.

Uso:
    python -m src.testar_personalizacao --numero "00000.000000/0000-00"
"""

import argparse
import sys

from playwright.sync_api import sync_playwright

from . import config
from .browser import abrir_sessao
from .documentos_nativos import incluir_documento, usar_documento_modelo
from .personalizar_documento import substituir_campos
from .planilha import linha_do_processo
from .sei_page import (
    clicar_botao,
    frame_conteudo,
    marcar_tempo,
    maximizar_janela,
    numero_processo_atual,
    pesquisar_processo,
    screenshot,
    selecionar_nivel_acesso,
)
from .verificar_documentos_anteriores import verificar_e_reportar

TIPO_DOCUMENTO = "Requerimento de Rec e Pagamento de DEA - RPDEA"
NUMERO_DOCUMENTO_MODELO = config.DOCUMENTOS_MODELO["rpdea"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--numero", required=True, help="Número do processo SEI.")
    args = parser.parse_args()

    print(f"Procurando '{args.numero}' na planilha...")
    valores = linha_do_processo(args.numero)
    print(f"Linha encontrada: {valores}")

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)
        marcar_tempo("conexão")

        print(f"\nPesquisando processo {args.numero}...")
        pesquisar_processo(page, args.numero)
        marcar_tempo("pesquisar processo")

        if not verificar_e_reportar(page):
            print("\nParando aqui — complete os documentos das Partes 1 e 2 primeiro.")
            sys.exit(1)
        marcar_tempo("verificar documentos anteriores")

        valores["Processo_sei"] = numero_processo_atual(page)
        marcar_tempo("leu número do processo da tela")

        print(f'\nIncluindo documento "{TIPO_DOCUMENTO}"...')
        incluir_documento(page, TIPO_DOCUMENTO)
        marcar_tempo("incluir documento (escolher tipo)")

        usar_documento_modelo(page, NUMERO_DOCUMENTO_MODELO)
        marcar_tempo("documento modelo")

        frame = frame_conteudo(page)
        selecionar_nivel_acesso(frame, "publico")
        marcar_tempo("nível de acesso")

        print("Salvando (abre o editor numa janela nova)...")
        with page.expect_popup() as popup_info:
            clicar_botao(frame, "Salvar")
        editor = popup_info.value
        editor.wait_for_load_state()
        marcar_tempo("salvou / abriu editor")

        maximizar_janela(editor)
        marcar_tempo("maximizou janela do editor")

        print(f"\nSubstituindo campos: {list(valores.keys())}")
        resultado = substituir_campos(editor, valores)
        marcar_tempo("substituiu campos")

        screenshot(editor, "personalizacao_01_resultado")

        encontrados = [k for k, v in resultado.items() if v]
        faltando = [k for k, v in resultado.items() if not v]
        print(f"\nEncontrados e substituídos: {encontrados}")
        if faltando:
            print(f"NÃO encontrados no documento (ok se não se aplicam a este documento): {faltando}")

        print(
            "\nParado aqui de propósito (NÃO salvei dentro do editor) — confira "
            "screenshots/personalizacao_01_resultado.png e a janela do editor "
            "antes de eu automatizar o Salvar final."
        )


if __name__ == "__main__":
    main()
