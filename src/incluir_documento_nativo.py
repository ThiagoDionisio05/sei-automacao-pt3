"""Inclui um documento NATIVO do SEI (editor de texto rico) a partir de um
Documento Modelo existente — fluxo genérico, reaproveitado por qualquer um
dos documentos nativos da Parte 3 (RPDEA, Checklist da Composição
Processual, Nota Técnica, TDEA, Despacho).

Confere os 9 documentos das Partes 1/2 antes de incluir qualquer coisa
(trava de segurança), inclui o documento do tipo informado, seleciona
"Documento Modelo" com o número dado, marca o Nível de Acesso e Salva —
o que abre o editor de texto rico numa janela nova. Se `valores` for
passado, personaliza esse documento (substitui os campos em negrito) e
salva dentro do editor antes de fechar a janela — cria, edita e fecha um
documento por vez, em vez de deixar várias janelas de editor abertas.

Uso:
    python -m src.incluir_documento_nativo --numero "00000.000000/0000-00" \\
        --tipo "Requerimento de Rec e Pagamento de DEA - RPDEA" --modelo "00000001"
"""

import argparse
import sys

from playwright.sync_api import Page, sync_playwright

from .browser import abrir_sessao
from .campos_automaticos import campos_de_data
from .documentos_nativos import incluir_documento, usar_documento_modelo
from .personalizar_documento import substituir_campos
from .planilha import linha_do_processo
from .sei_page import (
    clicar_botao,
    esperar_carregar,
    frame_conteudo,
    marcar_tempo,
    maximizar_janela,
    numero_processo_atual,
    numero_sequencial_na_arvore,
    pesquisar_processo,
    screenshot,
    selecionar_nivel_acesso,
)
from .verificar_documentos_anteriores import verificar_e_reportar


def incluir_documento_nativo(
    page: Page,
    tipo_documento: str,
    numero_modelo: str,
    nivel_acesso: str = "publico",
    valores: dict[str, str] | None = None,
    campo_numero_proprio: str | None = None,
) -> str | None:
    """Inclui `tipo_documento` copiando o conteúdo do Documento Modelo
    `numero_modelo`, marca o Nível de Acesso `nivel_acesso` e salva — isso
    abre o editor de texto rico numa janela nova.

    Se `valores` for passado (dict coluna-da-planilha -> valor), personaliza
    o documento nessa janela (substitui os campos em negrito que baterem
    com alguma chave de `valores`, mais "Processo_sei", "data_hoje" e
    "Data_extenso", preenchidos automaticamente), salva dentro do editor e
    fecha a janela antes de retornar. Sem `valores`, só cria o documento
    com o conteúdo genérico do Documento Modelo e deixa a janela do editor
    aberta (comportamento de antes, útil pra teste isolado).

    `campo_numero_proprio`: se o próprio documento precisa citar o número
    SEQUENCIAL dele mesmo (ex.: a árvore mostra "Nota Técnica 123
    (12345678)" — 123 é esse sequencial, diferente do número de protocolo
    entre parênteses), passa o nome desse ID aqui (ex.: "NUMERO_NOTA"). O
    número só existe depois que o SEI cria o documento E a árvore
    atualiza, então é lido nesse momento — a tempo de entrar na
    personalização deste MESMO documento.

    Retorna esse número sequencial quando `campo_numero_proprio` é
    passado — None caso contrário. Usado pra encadear esse número em
    outro documento mais à frente na mesma execução (ex.: "NUMERO_NOTA"
    no Despacho, depois de criar a Nota Técnica).

    Sem checagem de "já existe": tipos curtos/genéricos como "Despacho" ou
    "Nota Técnica" dão falso positivo contra documentos da Parte 1/2 que
    contêm essas palavras no nome (ex.: "Despacho-Plano de Trabalho..."),
    então uma verificação por substring aqui pularia documentos que na
    verdade ainda não foram criados.
    """
    print(f'\nIncluindo documento "{tipo_documento}"...')
    incluir_documento(page, tipo_documento)
    marcar_tempo("incluir documento (escolher tipo)")

    print(f"Selecionando Documento Modelo nº {numero_modelo}...")
    usar_documento_modelo(page, numero_modelo)
    marcar_tempo("documento modelo")

    print(f"Marcando Nível de Acesso '{nivel_acesso.capitalize()}'...")
    frame = frame_conteudo(page)
    selecionar_nivel_acesso(frame, nivel_acesso)
    marcar_tempo("nível de acesso")

    if valores is None:
        print("Salvando...")
        clicar_botao(frame, "Salvar")
        marcar_tempo("salvar")
        return None

    print("Salvando (abre o editor numa janela nova)...")
    with page.expect_popup() as popup_info:
        clicar_botao(frame, "Salvar")
    editor = popup_info.value
    editor.wait_for_load_state()
    marcar_tempo("salvar (abriu editor)")

    maximizar_janela(editor)
    marcar_tempo("maximizou janela do editor")

    valores_completos = dict(valores)
    valores_completos.setdefault("Processo_sei", numero_processo_atual(page))
    valores_completos.update(campos_de_data())

    numero_sequencial = None
    if campo_numero_proprio:
        # A árvore (na janela principal, não no editor) às vezes não
        # atualiza sozinha logo após o Salvar — recarrega antes de ler.
        page.reload()
        esperar_carregar(page)
        numero_sequencial = numero_sequencial_na_arvore(page, tipo_documento)
        print(f"Número sequencial na árvore ({tipo_documento}): {numero_sequencial}")
        valores_completos[campo_numero_proprio] = numero_sequencial

    print(f"Personalizando campos: {list(valores_completos.keys())}")
    resultado = substituir_campos(editor, valores_completos)
    faltando = [chave for chave, achou in resultado.items() if not achou]
    if faltando:
        print(f"(Aviso: campos não encontrados neste documento: {faltando})")
    marcar_tempo("personalizou campos")

    print("Salvando dentro do editor...")
    clicar_botao(editor, "Salvar")
    editor.wait_for_timeout(1000)
    marcar_tempo("salvou dentro do editor")

    try:
        if not editor.is_closed():
            editor.close()
    except Exception:
        pass
    marcar_tempo("fechou janela do editor")

    return numero_sequencial


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--numero", required=True, help="Número do processo SEI.")
    parser.add_argument(
        "--tipo",
        required=True,
        help="Nome do tipo de documento, igual à tela 'Escolha o Tipo de Documento'.",
    )
    parser.add_argument("--modelo", required=True, help="Número do Documento Modelo a copiar.")
    parser.add_argument(
        "--nivel", default="publico", choices=["publico", "restrito", "sigiloso"]
    )
    parser.add_argument(
        "--personalizar",
        action="store_true",
        help="Busca a linha do processo em data/pessoas.csv e personaliza os campos em negrito.",
    )
    args = parser.parse_args()

    valores = linha_do_processo(args.numero) if args.personalizar else None

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)
        marcar_tempo("conexão")

        print(f"\nPesquisando processo {args.numero}...")
        pesquisar_processo(page, args.numero)
        screenshot(page, "incluir_00_processo_aberto")
        marcar_tempo("pesquisar processo")

        if not verificar_e_reportar(page):
            print("\nParando aqui — complete os documentos das Partes 1 e 2 primeiro.")
            sys.exit(1)
        marcar_tempo("verificar documentos anteriores")

        incluir_documento_nativo(page, args.tipo, args.modelo, args.nivel, valores=valores)
        screenshot(page, "incluir_01_salvo")

        print(
            "\nDocumento incluído e salvo. Confira screenshots/incluir_01_salvo.png "
            "e a árvore do processo."
        )


if __name__ == "__main__":
    main()
