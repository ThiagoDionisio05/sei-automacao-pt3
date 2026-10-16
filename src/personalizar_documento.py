"""Personalização de um documento NATIVO do SEI: substitui, no editor de
texto rico (CKEditor, aberto numa janela separada depois de Salvar um
documento nativo), cada ID em negrito (ex.: "**Nome**") pelo valor real
correspondente — mantendo o negrito.

Usa negrito como marcador em vez de um delimitador de texto (tipo
"{{Nome}}") porque é assim que os documentos já foram preparados: cada
campo variável está em negrito, o resto do texto não. Detecta negrito pelo
ESTILO COMPUTADO (`getComputedStyle(...).fontWeight`), não pela tag — cobre
tanto `<b>`/`<strong>` quanto negrito aplicado via `style="font-weight"`.

Dois formatos de campo, cobertos os dois:
  - ID SOZINHO num elemento de negrito próprio (ex.: célula de tabela com
    só "**Nome**") — troca o texto do elemento inteiro.
  - ID como PEDAÇO de um bloco maior de negrito (ex.: "**NOTA TÉCNICA Nº
    NUMERO_NOTA/2026/UNIDADE/ORGAO**", onde só "NUMERO_NOTA" deveria
    virar o número real) — troca só aquele trecho, mantendo o resto do
    texto em negrito intacto ao redor.

A SUBSTITUIÇÃO em si é feita posicionando a seleção real da página (via
JS, só a seleção — não mexe no texto) exatamente sobre o trecho certo, e
digitando por cima com `page.keyboard.type()` — eventos de teclado DE
VERDADE via CDP, exatamente como uma pessoa faria. Duas tentativas
anteriores, mais diretas, NÃO funcionaram e explicam por quê:
  1. `el.textContent = valor` direto no DOM: o CKEditor mantém seu próprio
     modelo de dados e redesenha a tela a partir dele — uma mudança que
     não passa pelos eventos que o editor escuta é revertida no próximo
     redesenho (a troca "colava" só até o editor repintar a tela).
  2. `document.execCommand('insertText', ...)`: dispara os eventos certos
     em teoria, mas na prática não teve efeito visível aqui também —
     possivelmente porque a janela do editor não estava com o foco real
     do sistema operacional no momento. `page.keyboard` via CDP não tem
     essa limitação: os eventos são despachados pro alvo certo
     independente de qual janela está em primeiro plano.
"""

import unicodedata

from playwright.sync_api import Page


def normalizar_id(texto: str) -> str:
    """Remove acento e espaço nas pontas de `texto`, pra comparar nome de
    coluna da planilha (ex.: "Lotação ") com o ID no documento (ex.:
    "Lotacao"), ignorando essas diferenças.
    """
    texto = texto.strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def _frame_editor(page: Page, timeout_ms: int = 8000):
    """Acha o frame (ou a própria página) que contém a área editável do
    CKEditor dentro da janela do editor de texto rico.

    Busca por QUALQUER elemento com `contenteditable="true"` (não só
    `<body>`) — visto na prática que este SEI não usa um `<body
    contenteditable>` dentro de um iframe aninhado (o esperado no
    CKEditor4 "clássico"), a área editável é um elemento comum (ex.: uma
    `<div>`) direto na página, sem iframe extra. Tenta algumas vezes
    porque o editor carrega via JS depois da janela abrir.
    """
    tentativas = max(1, timeout_ms // 400)
    for _ in range(tentativas):
        for fr in page.frames:
            try:
                if fr.locator("[contenteditable='true']").count() > 0:
                    return fr
            except Exception:
                continue
        page.wait_for_timeout(400)

    print("\nNão achei nenhum elemento [contenteditable='true'] nesta janela. Frames encontrados:")
    for fr in page.frames:
        print(f"  name={fr.name!r} url={fr.url!r}")
        try:
            print(f"    body (primeiros 500 chars): {fr.locator('body').inner_html()[:500]!r}")
        except Exception as e:
            print(f"    (não consegui ler o body: {e})")
    raise RuntimeError("Não encontrei a área editável do documento.")


# Acha o primeiro elemento folha em negrito, em qualquer área
# contenteditable da página, que bate com uma chave (elemento inteiro) OU
# que CONTÉM uma chave como pedaço do seu texto. Só busca/retorna posição
# — não muda nada no DOM.
_SCRIPT_PROCURAR_ALVO = """
(chaves) => {
    function normalizar(s) {
        return s.normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '').trim().toLowerCase();
    }
    const raizes = document.querySelectorAll('[contenteditable="true"]');
    for (let r = 0; r < raizes.length; r++) {
        const elementos = Array.from(raizes[r].querySelectorAll('*'));
        for (let i = 0; i < elementos.length; i++) {
            const el = elementos[i];
            // "Folha" pra esse efeito: sem filhos, ou só filhos <br>
            // (quebra de linha dentro do mesmo bloco de negrito não conta
            // como formatação aninhada — várias linhas de um cabeçalho
            // costumam ficar assim, um <p>/<div> só com <br> entre elas).
            const temFilhoRelevante = Array.from(el.children).some((filho) => filho.tagName !== 'BR');
            if (temFilhoRelevante) continue;
            const textoBruto = el.textContent || '';
            if (!textoBruto.trim()) continue;
            const peso = window.getComputedStyle(el).fontWeight;
            const negrito = peso === 'bold' || parseInt(peso, 10) >= 600;
            if (!negrito) continue;

            const textoNormalizado = normalizar(textoBruto);
            if (chaves.includes(textoNormalizado)) {
                return { raizIndice: r, indice: i, chave: textoNormalizado, modo: 'inteiro' };
            }

            const textoMaiusculo = textoBruto.toUpperCase();
            for (const chave of chaves) {
                const posicao = textoMaiusculo.indexOf(chave.toUpperCase());
                if (posicao !== -1) {
                    return {
                        raizIndice: r, indice: i, chave: chave, modo: 'trecho',
                        inicio: posicao, fim: posicao + chave.length,
                    };
                }
            }
        }
    }
    return null;
}
"""


def _procurar_alvo(frame, chaves_restantes: list[str]) -> dict | None:
    """Roda uma busca READ-ONLY (não mexe no DOM) no frame do editor:
    acha o primeiro elemento folha em negrito relacionado a alguma de
    `chaves_restantes`, procurando em TODOS os elementos com
    `contenteditable="true"` da página. Retorna um dict com "modo"
    ("inteiro" ou "trecho") e os dados pra localizar o alvo, ou None se
    não achar mais nada.
    """
    return frame.evaluate(_SCRIPT_PROCURAR_ALVO, chaves_restantes)


# Só posiciona a SELEÇÃO da página num trecho específico de texto dentro
# de um elemento (não digita nada, não muda o DOM) — a digitação em si
# é feita depois, em Python, via page.keyboard.type() (eventos reais).
_SCRIPT_SELECIONAR_TRECHO = """
(args) => {
    const raiz = document.querySelectorAll('[contenteditable="true"]')[args.raizIndice];
    const el = raiz.querySelectorAll('*')[args.indice];

    let no = null;
    let acumulado = 0;
    for (const filho of el.childNodes) {
        if (filho.nodeType === Node.TEXT_NODE) {
            const tamanho = filho.textContent.length;
            if (args.inicio <= acumulado + tamanho) {
                no = filho;
                break;
            }
            acumulado += tamanho;
        }
    }
    if (!no) {
        no = el.firstChild;
        acumulado = 0;
    }

    const inicioRelativo = Math.max(0, args.inicio - acumulado);
    const fimRelativo = Math.min(no.textContent.length, args.fim - acumulado);

    const range = document.createRange();
    range.setStart(no, inicioRelativo);
    range.setEnd(no, fimRelativo);

    const selecao = window.getSelection();
    selecao.removeAllRanges();
    selecao.addRange(range);
    return true;
}
"""


def substituir_campos(page: Page, valores: dict[str, str]) -> dict[str, bool]:
    """Substitui, no editor já aberto em `page`, cada ID em negrito (negrito
    de verdade, pelo estilo computado) — seja um elemento de negrito
    inteiro dedicado ao ID, seja o ID como pedaço de um bloco maior de
    negrito — pelo valor correspondente em `valores` (comparação por
    `normalizar_id`, sem diferenciar caixa).

    Todo valor digitado continua em negrito, como o marcador que substituiu.

    Processa um campo por vez, refazendo a busca a cada iteração (em vez
    de calcular todos os índices de uma vez): digitar por cima pode
    reestruturar o DOM ao redor do campo alterado, o que invalidaria
    índices calculados antes dessa mudança.

    Um mesmo ID pode aparecer MAIS DE UMA VEZ no documento (ex.: "Nome"
    tanto na tabela "Favorecido" quanto solto dentro de um parágrafo) —
    continua procurando o mesmo ID até não achar mais nenhuma ocorrência
    dele, em vez de parar na primeira.

    Retorna, pra cada chave de `valores`, se ela foi encontrada (pelo
    menos uma vez) e substituída — chaves não encontradas ficam False (e
    são avisadas no console), pra não falhar o documento inteiro por
    causa de um campo só.

    Duas chaves de `valores` que normalizam igual (ex.: "Processo_SEI" da
    planilha e "Processo_sei" lido da tela) contam como UMA só — só a
    última delas (na ordem de `valores`) é de fato buscada; sem isso, a
    outra sempre apareceria como "não encontrada" mesmo quando o campo foi
    preenchido de verdade (só que sob o nome da outra).
    """
    frame = _frame_editor(page)
    mapa_normalizado = {normalizar_id(chave).lower(): (chave, valor) for chave, valor in valores.items()}
    encontrados = {chave_original: False for chave_original, _ in mapa_normalizado.values()}

    chaves_busca = list(mapa_normalizado.keys())
    # Cada ID pode se repetir no documento — o teto de tentativas cobre
    # várias ocorrências por campo, não só uma, mas ainda limita um loop
    # infinito se algo ficar preso (ex.: clique falhando sempre no mesmo
    # elemento sem nunca mudar o texto dele).
    protecao = len(chaves_busca) * 6 + 20

    while protecao > 0:
        protecao -= 1
        alvo = _procurar_alvo(frame, chaves_busca)
        if alvo is None:
            break

        chave_normalizada = alvo["chave"]
        chave_original, valor = mapa_normalizado[chave_normalizada]

        try:
            if alvo["modo"] == "inteiro":
                elemento = frame.locator("[contenteditable='true']").nth(alvo["raizIndice"]).locator("*").nth(
                    alvo["indice"]
                )
                elemento.click()
                elemento.select_text()
            else:
                elemento = frame.locator("[contenteditable='true']").nth(alvo["raizIndice"]).locator("*").nth(
                    alvo["indice"]
                )
                elemento.click()
                frame.evaluate(_SCRIPT_SELECIONAR_TRECHO, alvo)

            # O texto digitado sobre a seleção herda o formato dela — como
            # o marcador está em negrito, o valor já nasce em negrito.
            page.keyboard.type(str(valor), delay=15)

            encontrados[chave_original] = True
        except Exception as e:
            print(f"\n(Aviso: achei o campo '{chave_original}' mas não consegui digitar por cima: {e})")
            break  # evita loop preso tentando o mesmo elemento que sempre falha

    faltando = [chave for chave, achou in encontrados.items() if not achou]
    if faltando:
        print(f"\n(Aviso: IDs não encontrados em negrito no documento: {faltando})")

    return encontrados
