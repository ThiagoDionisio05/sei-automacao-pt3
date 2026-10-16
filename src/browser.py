"""Conexão com um Chrome que você abre e loga manualmente (via CDP).

Em vez da automação lançar seu próprio navegador, ela se conecta a um
Chrome que você já deixou aberto e logado no SEI. Veja README.md ->
"Conectar num Chrome já logado" para o passo a passo de como abrir esse
Chrome com depuração remota habilitada.
"""

from playwright.sync_api import sync_playwright, BrowserContext, Page

from . import config


def abrir_sessao(playwright) -> tuple[BrowserContext, Page]:
    """Conecta numa janela do Chrome já aberta manualmente (com login feito
    no SEI) via modo de depuração remota. Não lança nem fecha o navegador —
    ele continua sob seu controle.
    """
    try:
        browser = playwright.chromium.connect_over_cdp(config.CDP_URL)
    except Exception as exc:
        raise RuntimeError(
            f"Não consegui conectar ao Chrome em {config.CDP_URL}.\n"
            "Abra o Chrome com depuração remota habilitada e faça login no "
            "SEI manualmente antes de rodar a automação — veja o passo a "
            "passo em README.md -> 'Conectar num Chrome já logado'."
        ) from exc

    context = browser.contexts[0] if browser.contexts else browser.new_context()
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=config.SEI_URL)

    paginas_sei = [p for p in context.pages if config.SEI_URL in p.url]

    pagina_sei = _pagina_visivel(paginas_sei)
    if pagina_sei is None:
        pagina_sei = paginas_sei[0] if paginas_sei else None
    if pagina_sei is None:
        pagina_sei = context.new_page()
        pagina_sei.goto(config.SEI_URL)

    print("\n" + "=" * 70)
    print(f"Conectado ao Chrome em {config.CDP_URL}.")
    print("Confirme que está logado no SEI nessa janela e na tela de")
    print("Controle de Processos, depois volte aqui e pressione ENTER.")
    if len(paginas_sei) > 1:
        print(
            f"(Aviso: há {len(paginas_sei)} abas do SEI abertas — a automação vai "
            "usar a que estiver em foco/visível na hora de conectar. Deixe SÓ a "
            "aba com o processo certo em primeiro plano antes de apertar ENTER.)"
        )
    print("=" * 70)
    input()

    # Reavalia a aba visível depois do ENTER, já que o usuário pode ter
    # trocado de aba enquanto lia o aviso acima.
    pagina_em_foco = _pagina_visivel(paginas_sei)
    if pagina_em_foco is not None:
        pagina_sei = pagina_em_foco

    return context, pagina_sei


def _pagina_visivel(paginas):
    """Retorna a página que está realmente visível/em foco no navegador,
    dentre as passadas em `paginas`, ou None se nenhuma estiver visível
    (ex.: nenhuma aba do SEI aberta ainda).

    Evita o bug de sempre pegar a primeira aba do SEI que existir — com
    várias abas abertas (comum depois de testes repetidos), a primeira nem
    sempre é a que o usuário está olhando.
    """
    for p in paginas:
        try:
            if p.evaluate("() => document.visibilityState") == "visible":
                return p
        except Exception:
            continue
    return None
