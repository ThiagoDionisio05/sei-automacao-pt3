"""Inclusão de um documento EXTERNO (anexo de PDF já pronto) num processo do
SEI — fluxo genérico, portado de sei-automaçaoPt2/src/documento_pessoal.py
(mesma lógica: Incluir Documento -> Externo -> Tipo do Documento "Anexo" ->
Data de hoje / Nome na Árvore / Nato-digital -> Nível de Acesso -> anexar
arquivo -> Salvar -> recarrega e confirma na árvore).

Suporta tanto Nível de Acesso Público (sem hipótese legal — caso do
"Anexo - Ateste Orçamentário") quanto Restrito/Sigiloso + Hipótese Legal
(mesmo esquema dos documentos pessoais da Pt2), e o anexo em si é
opcional: alguns documentos externos (ex.: "Comprovante de Cadastro do
processo SIAPE") são salvos sem arquivo nenhum.
"""

from datetime import date
from pathlib import Path

from playwright.sync_api import Page

from . import sei_page

TIPO_DOCUMENTO_PADRAO = "Externo"


def incluir_documento_externo(
    page: Page,
    nome_arvore: str,
    arquivo_anexo: Path | None = None,
    tipo_documento_externo: str = "Anexo",
    nivel_acesso: str = "publico",
    hipotese_legal: str | None = None,
) -> None:
    """Inclui, no processo atualmente aberto na tela, um Documento Externo
    com `nome_arvore`. Se `arquivo_anexo` for None, salva sem anexar nada.
    Se `nivel_acesso` for "restrito" ou "sigiloso", `hipotese_legal` é
    obrigatório (mesmo campo que aparece na tela só nesses dois casos).
    Levanta erro se qualquer etapa falhar ou se o documento não aparecer
    na árvore depois de salvo.
    """
    if arquivo_anexo is not None and not arquivo_anexo.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo_anexo}")
    if nivel_acesso != "publico" and not hipotese_legal:
        raise ValueError(f'nivel_acesso="{nivel_acesso}" exige informar hipotese_legal.')

    if sei_page.documento_existe_na_arvore(page, nome_arvore):
        print(f"Documento '{nome_arvore}' já existe na árvore — pulando.")
        return

    clicou = sei_page.clicar_por_texto_ou_icone(page, "Incluir Documento")
    sei_page.esperar_carregar(page)
    if not clicou:
        raise RuntimeError('Não encontrei o menu "Incluir Documento".')
    sei_page.marcar_tempo("incluir documento")

    frame = sei_page.frame_conteudo(page)
    sei_page.buscar_e_selecionar(frame, TIPO_DOCUMENTO_PADRAO)
    sei_page.esperar_carregar(page)
    sei_page.marcar_tempo("escolheu tipo Externo")

    frame = sei_page.frame_conteudo(page)

    ok_tipo = sei_page.selecionar_select_por_rotulo(frame, "Tipo do Documento", tipo_documento_externo)

    data_hoje = date.today().strftime("%d/%m/%Y")
    ok_data = sei_page.digitar_por_rotulo_ou_seletor(
        frame, "Data do Documento", sei_page.config.SELECTORS.get("campo_data_documento", ""), data_hoje
    )

    ok_nome_arvore = sei_page.digitar_por_rotulo_ou_seletor(
        frame, "Nome na Árvore", sei_page.config.SELECTORS["campo_nome_arvore"], nome_arvore
    )

    marcou_formato = sei_page.marcar_radio(frame, "Nato-digital")
    sei_page.marcar_tempo("preencheu tipo/data/árvore/formato")

    if not ok_tipo:
        raise RuntimeError(f'Não consegui selecionar "Tipo do Documento" = "{tipo_documento_externo}".')
    if not ok_data:
        raise RuntimeError('Não consegui confirmar o preenchimento de "Data do Documento".')
    if not ok_nome_arvore:
        raise RuntimeError('Não consegui confirmar o preenchimento de "Nome na Árvore".')
    if not marcou_formato:
        raise RuntimeError('Não consegui marcar o Formato "Nato-digital".')

    sei_page.selecionar_nivel_acesso(frame, nivel_acesso)
    sei_page.marcar_tempo("marcou nível de acesso")

    if nivel_acesso != "publico":
        # O SEI carrega as opções de Hipótese Legal via AJAX depois de
        # marcar Restrito/Sigiloso — essa pausa dá tempo desse carregamento
        # terminar antes do polling começar (mesmo ajuste feito na Pt2).
        page.wait_for_timeout(500)
        sei_page.selecionar_hipotese_legal(frame, hipotese_legal, timeout_ms=8000)
        sei_page.marcar_tempo("marcou hipótese legal")

    if arquivo_anexo is not None:
        anexou = sei_page.anexar_arquivo(frame, arquivo_anexo)
        sei_page.marcar_tempo("anexou arquivo")
        if not anexou:
            raise RuntimeError(f"Campos preenchidos, mas não consegui anexar o arquivo ({arquivo_anexo}).")

    sei_page.clicar_botao(frame, "Salvar")
    sei_page.esperar_carregar(page)
    page.wait_for_timeout(400)
    sei_page.marcar_tempo("salvou")

    # A árvore às vezes não atualiza sozinha logo após o Salvar (mesmo
    # comportamento observado na Pt1/Pt2) — recarrega antes de confirmar.
    page.reload()
    sei_page.esperar_carregar(page)
    sei_page.marcar_tempo("recarregou pra verificar")

    if not sei_page.documento_existe_na_arvore(page, nome_arvore):
        raise RuntimeError(
            f"Cliquei em Salvar, mas '{nome_arvore}' não apareceu na árvore depois — o "
            "documento provavelmente NÃO foi anexado de verdade. Confira manualmente no SEI."
        )

    print(f"Documento externo '{nome_arvore}' salvo.")
