"""Depois de incluir os 7 documentos da Parte 3, abre "Consultar/Alterar
Processo" e adiciona o PAT da pessoa em "Observações desta Unidade".

Tela ainda não explorada antes neste projeto — segue o mesmo padrão
defensivo do resto do código (busca por rótulo, com diagnóstico se não
achar) até confirmar contra a tela real.
"""

from playwright.sync_api import Page

from .sei_page import (
    clicar_botao,
    clicar_por_texto_ou_icone,
    esperar_carregar,
    frame_conteudo,
    selecionar_processo_na_arvore,
)


def atualizar_pat(page: Page, numero_processo: str, pat: str) -> str:
    """Abre "Consultar/Alterar Processo" e adiciona "PAT: <pat>" no campo
    "Observações desta Unidade" — numa linha nova, sem apagar o que já
    estava escrito ali (o campo pode ter outras observações).

    Retorna "adicionado" ou "ja_estava" (se o PAT já estava lá, não grava
    de novo).
    """
    selecionar_processo_na_arvore(page, numero_processo)
    if not clicar_por_texto_ou_icone(page, "Consultar/Alterar Processo"):
        raise RuntimeError('Não encontrei "Consultar/Alterar Processo".')
    esperar_carregar(page)

    frame = frame_conteudo(page)

    try:
        campo = frame.get_by_label("Observações desta Unidade", exact=False)
        campo.wait_for(state="visible", timeout=5000)
    except Exception:
        campos = frame.locator("textarea, input[type='text']")
        total = campos.count()
        print(
            '\nNão achei o campo "Observações desta Unidade" pelo rótulo. '
            "Campos de texto/textarea visíveis na tela:"
        )
        for i in range(total):
            c = campos.nth(i)
            try:
                if not c.is_visible():
                    continue
                print(f"  id={c.get_attribute('id')!r} name={c.get_attribute('name')!r}")
            except Exception:
                continue
        raise RuntimeError(
            'Não encontrei "Observações desta Unidade". Veja o diagnóstico acima e '
            "ajuste atualizar_pat()."
        )

    texto_atual = (campo.input_value() or "").strip()

    if f"PAT: {pat}" in texto_atual:
        print(f'PAT "{pat}" já estava em "Observações desta Unidade" — pulando.')
        return "ja_estava"

    prefixo = "\n" if texto_atual else ""

    campo.click()
    campo.press("Control+End")
    campo.press_sequentially(f"{prefixo}PAT: {pat}", delay=10)

    clicar_botao(frame, "Salvar")
    esperar_carregar(page)

    print(f'PAT "{pat}" adicionado em "Observações desta Unidade".')
    return "adicionado"
