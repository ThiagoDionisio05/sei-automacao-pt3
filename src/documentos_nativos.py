"""Helpers para incluir documentos NATIVOS do SEI (editor de texto rico
dentro de um iframe) — diferente do fluxo de "Documento Externo" (anexar
PDF) usado na Pt2, e ainda não implementado em nenhuma das partes
anteriores.

Fluxo comum aos documentos nativos da Parte 3 (visto na tela real do SEI):
  1. Clicar em "Incluir Documento".
  2. Escolher o tipo na tela "Escolha o Tipo de Documento" (busca por
     texto, igual às outras telas de busca+lista do SEI).
  3. Na tela "Gerar Documento", escolher o "Texto Inicial" — pro RPDEA,
     sempre "Documento Modelo", copiando o conteúdo de um documento SEI
     existente a partir do número de protocolo.
  4. (ainda pendente) Preencher Descrição / Nome na Árvore / Classificação
     por Assuntos e Salvar — depende de decidir o conteúdo/template de
     cada documento (ver README.md -> "Próximos passos").
"""

from playwright.sync_api import Frame, Page

from .sei_page import buscar_e_selecionar, clicar_por_texto_ou_icone, esperar_carregar, frame_conteudo, marcar_radio


def incluir_documento(page: Page, tipo_documento: str) -> Frame:
    """Clica em "Incluir Documento", escolhe `tipo_documento` na tela
    "Escolha o Tipo de Documento" e retorna o frame já na tela "Gerar
    Documento".

    Tenta duas vezes: pegar o frame de conteúdo bem na hora que o clique
    dispara uma navegação/postback pode pegar o frame ANTIGO, que fica
    "detached" assim que a navegação termina de verdade — visto na
    prática ao encadear vários documentos numa mesma execução (o segundo
    documento em diante tem mais chance de pegar esse instante exato do
    que o primeiro, ainda não se sabe por quê ao certo). Uma pausa curta
    + tentar de novo resolve sem precisar entender a causa exata.
    """
    if not clicar_por_texto_ou_icone(page, "Incluir Documento"):
        raise RuntimeError('Não encontrei o botão/ícone "Incluir Documento".')

    esperar_carregar(page)

    ultimo_erro = None
    for tentativa in range(2):
        try:
            frame = frame_conteudo(page)
            buscar_e_selecionar(frame, tipo_documento)
            return frame_conteudo(page)
        except Exception as e:
            ultimo_erro = e
            page.wait_for_timeout(800)

    raise RuntimeError(
        f"Não consegui escolher o tipo de documento '{tipo_documento}' depois de 2 "
        f"tentativas (frame ficando 'detached' no meio do processo). Último erro: {ultimo_erro}"
    )


def usar_documento_modelo(page: Page, numero_documento: str, timeout_ms: int = 5000) -> None:
    """Na tela "Gerar Documento", marca "Documento Modelo" em Texto Inicial
    e preenche o número do documento SEI (`numero_documento`) a copiar.

    Recebe `page` (não o frame já obtido antes) porque marcar o rádio
    dispara um postback do SEI que recarrega o iframe de conteúdo — um
    `Frame` obtido antes dessa marcação fica "detached" (obsoleto) depois
    dela, e usá-lo trava com "Frame was detached". Por isso o frame é
    buscado de novo (`frame_conteudo`) só depois do rádio marcado.

    O campo do número não tem um <label> associado (é só um <input> ao
    lado do rádio "Documento Modelo") — confirmado contra a tela real que
    o id é fixo: 'txtProtocoloDocumentoTextoBase'.
    """
    frame = frame_conteudo(page)
    if not marcar_radio(frame, "Documento Modelo"):
        raise RuntimeError('Não consegui marcar o rádio "Documento Modelo" em Texto Inicial.')

    page.wait_for_timeout(800)  # postback do SEI recarrega o iframe pra revelar o campo
    frame = frame_conteudo(page)  # frame de antes do postback ficaria "detached"

    try:
        campo = frame.locator("#txtProtocoloDocumentoTextoBase")
        campo.wait_for(state="visible", timeout=timeout_ms)
        campo.click()
        campo.press_sequentially(numero_documento, delay=10)
        return
    except Exception:
        pass

    campos = frame.locator("input[type='text'], input:not([type])")
    total = campos.count()
    print(
        "\nNão consegui achar o campo do número do Documento Modelo pela posição "
        "relativa ao rádio. Campos de texto visíveis na tela:"
    )
    for i in range(total):
        campo = campos.nth(i)
        try:
            if not campo.is_visible():
                continue
            print(
                f"  id={campo.get_attribute('id')!r} name={campo.get_attribute('name')!r} "
                f"placeholder={campo.get_attribute('placeholder')!r}"
            )
        except Exception:
            continue

    raise RuntimeError(
        "Não encontrei o campo para digitar o número do Documento Modelo. Veja o "
        "diagnóstico acima e ajuste usar_documento_modelo()."
    )
