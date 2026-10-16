"""Ponto de entrada da automação SEI (Pt3): inclui e personaliza os 7
documentos novos num processo (ou em vários, numa única conexão/login),
depois de confirmar que os 9 documentos das Partes 1 e 2 já estão na
árvore de cada um (trava de segurança). Grava o status de cada passo e
atualiza o painel do lote (painel_documentos.html pra PT1,
painel_documentos_<LOTE>.html pros outros) depois de cada processo.

Uso:
    python main.py --numero "00000.000000/0000-00"   # só esse processo
    python main.py --numero "00000.000000/0000-00" "00000.000000/0000-01"   # vários
    python main.py --limite 2                         # próximos 2 ainda não concluídos
    python main.py --so-erros                         # só os que já deram erro
    python main.py                                    # todos da planilha
    python main.py --lote PT4 --limite 2              # usa data/Editaveis_PT4.xlsx (padrão: PT1)
"""

import argparse
import sys

from playwright.sync_api import Page, sync_playwright

from src import config
from src.browser import abrir_sessao
from src.documento_externo import incluir_documento_externo
from src.gerar_painel import atualizar_painel
from src.incluir_documento_nativo import incluir_documento_nativo
from src.planilha import carregar_planilha, linha_do_processo
from src.sei_page import (
    documento_existe_na_arvore,
    documento_numerado_existe_na_arvore,
    marcar_tempo,
    numero_sequencial_na_arvore,
    pesquisar_processo,
    processo_aberto_confere,
    sair_do_processo,
    screenshot,
)
from src.status_processos import (
    carregar_status,
    limpar_erro_processo,
    processo_concluido,
    registrar_documento,
    registrar_erro_processo,
)
from src.verificar_documentos_anteriores import verificar_e_reportar

ARQUIVO_ATESTE_ORCAMENTARIO = config.BASE_DIR / "src" / "PDFs" / "Anexo_Ateste_Orcamentario.pdf"

_TIPO_NOTA = "Nota Técnica"
_TIPO_TDEA = "Termo de Despesas de Exercícios Anteriores - TDEA"


def _existe_na_arvore(page: Page, chave: str) -> bool:
    """Checagem de existência de UM dos 7 documentos. Tipos genéricos
    ("Nota Técnica", "Despacho") usam a checagem numerada (tipo + espaço +
    número) — a Parte 1 tem "Despacho-Plano..." e "Nota Técnica Nº 2/2024...",
    que colidiriam com substring simples."""
    if chave == "rpdea":
        return documento_existe_na_arvore(page, "Requerimento de Rec e Pagamento de DEA - RPDEA")
    if chave == "checklist":
        return documento_existe_na_arvore(page, "Checklist da Composição Processual - DEA")
    if chave == "nota_tecnica":
        return documento_numerado_existe_na_arvore(page, _TIPO_NOTA)
    if chave == "ateste":
        return documento_existe_na_arvore(page, "Ateste Orçamentário")
    if chave == "tdea":
        return documento_existe_na_arvore(page, "Termo de Despesas de Exercícios Anteriores")
    if chave == "comprovante_siape":
        return documento_existe_na_arvore(page, "Comprovante de Cadastro do processo SIAPE")
    if chave == "despacho":
        return documento_numerado_existe_na_arvore(page, "Despacho")
    raise ValueError(f"Documento desconhecido: {chave}")


def _rodar_documento(page: Page, numero: str, chave: str, fn, tipo_numerado: str | None = None):
    """Roda um passo de inclusão, pulando (e registrando "ja_existia") se o
    documento já estiver na árvore — assim um rerun num processo que caiu no
    meio só cria o que falta, sem duplicar.

    Se `tipo_numerado` for passado, devolve o número sequencial dele (tanto
    quando cria quanto quando pula), pra encadear nos documentos seguintes.
    """
    if _existe_na_arvore(page, chave):
        anterior = carregar_status().get(numero, {}).get("documentos", {}).get(chave, {})
        if anterior.get("situacao") == "falhou":
            # A tentativa anterior criou o documento na árvore mas caiu no
            # meio (ex.: antes de personalizar) — pular aqui deixaria um
            # documento sem conteúdo preenchido passar como "já existia".
            msg = (
                f"'{chave}' está na árvore, mas a tentativa anterior falhou no meio "
                f"({anterior.get('erro', 'sem detalhe')}) — pode ter ficado sem os campos preenchidos. "
                "Confira no SEI; se estiver incompleto, exclua o documento e rode de novo."
            )
            print(f"  {msg}")
            registrar_documento(numero, chave, "falhou", erro=msg)
            raise RuntimeError(msg)
        print(f"  {chave}: já existe na árvore — pulando.")
        registrar_documento(numero, chave, "ja_existia")
        if tipo_numerado:
            try:
                return numero_sequencial_na_arvore(page, tipo_numerado, timeout_ms=3000)
            except RuntimeError as e:
                print(f"  (aviso: não consegui ler o número sequencial de {tipo_numerado}: {e})")
        return None

    try:
        resultado = fn()
    except Exception as e:
        registrar_documento(numero, chave, "falhou", erro=str(e))
        raise
    registrar_documento(numero, chave, "confirmado")
    return resultado


def incluir_documentos_parte3(page: Page, numero: str, valores: dict[str, str]) -> None:
    """Inclui, na ordem, os 7 documentos da Parte 3 que ainda não existem no
    processo atualmente aberto. Cada NATIVO é criado, personalizado e salvo
    dentro do próprio editor antes de passar pro próximo.

    `contexto` começa como uma cópia de `valores` (dados da planilha) e
    cresce conforme os documentos são criados (ou lidos da árvore, se já
    existiam): "NUMERO_NOTA" depois da Nota Técnica, "Numero_termo" depois
    do TDEA.
    """
    contexto = dict(valores)

    _rodar_documento(
        page,
        numero,
        "rpdea",
        lambda: incluir_documento_nativo(
            page, "Requerimento de Rec e Pagamento de DEA - RPDEA", config.DOCUMENTOS_MODELO["rpdea"], valores=contexto
        ),
    )
    _rodar_documento(
        page,
        numero,
        "checklist",
        lambda: incluir_documento_nativo(
            page, "Checklist da Composição Processual - DEA", config.DOCUMENTOS_MODELO["checklist"], valores=contexto
        ),
    )

    numero_nota = _rodar_documento(
        page,
        numero,
        "nota_tecnica",
        lambda: incluir_documento_nativo(
            page,
            _TIPO_NOTA,
            config.DOCUMENTOS_MODELO["nota_tecnica"],
            valores=contexto,
            campo_numero_proprio="NUMERO_NOTA",
        ),
        tipo_numerado=_TIPO_NOTA,
    )
    if numero_nota:
        contexto["NUMERO_NOTA"] = numero_nota

    _rodar_documento(
        page,
        numero,
        "ateste",
        lambda: incluir_documento_externo(
            page, "- Ateste Orçamentário", ARQUIVO_ATESTE_ORCAMENTARIO, nivel_acesso="publico"
        ),
    )

    numero_termo = _rodar_documento(
        page,
        numero,
        "tdea",
        lambda: incluir_documento_nativo(
            page,
            "Termo de Despesas de Exercícios Anteriores - TDEA",
            config.DOCUMENTOS_MODELO["tdea"],
            valores=contexto,
            campo_numero_proprio="Numero_termo",
        ),
        tipo_numerado=_TIPO_TDEA,
    )
    if numero_termo:
        contexto["Numero_termo"] = numero_termo

    _rodar_documento(
        page,
        numero,
        "comprovante_siape",
        lambda: incluir_documento_externo(
            page,
            "Comprovante de Cadastro do processo SIAPE",
            arquivo_anexo=None,
            nivel_acesso="restrito",
            hipotese_legal="Informação Pessoal",
        ),
    )
    _rodar_documento(
        page,
        numero,
        "despacho",
        lambda: incluir_documento_nativo(
            page, "Despacho", config.DOCUMENTOS_MODELO["despacho"], valores=contexto
        ),
        tipo_numerado="Despacho",
    )


def processar_processo(page: Page, numero: str) -> bool:
    """Roda a Parte 3 pra UM processo. NÃO propaga exceção: registra o erro
    no status, imprime e retorna False, pra um processo com problema não
    travar o lote.
    """
    try:
        print(f"\nPesquisando processo {numero}...")
        pesquisar_processo(page, numero)
        screenshot(page, f"conexao_ok_{numero.replace('/', '-')}")
        marcar_tempo("pesquisar processo")

        if not processo_aberto_confere(page, numero):
            msg = f"O processo aberto não é {numero} — nada foi gravado."
            print(f"\n{msg}")
            registrar_erro_processo(numero, "processo_nao_confere", msg)
            return False
        marcar_tempo("conferiu processo aberto")

        if not verificar_e_reportar(page):
            msg = "Partes 1 e 2 incompletas — complete antes de rodar a Parte 3."
            print(f"\nPulando {numero} — {msg}")
            registrar_erro_processo(numero, "partes_1_2_incompletas", msg)
            return False
        marcar_tempo("verificar documentos anteriores")

        valores = linha_do_processo(numero)
        print(f"Dados da planilha pra este processo: {valores}")
        limpar_erro_processo(numero)

        incluir_documentos_parte3(page, numero, valores)

        return True
    except Exception as e:
        print(f"\nERRO no processo {numero}: {e}")
        registrar_erro_processo(numero, "erro", str(e))
        return False


def _atualizar_painel_seguro() -> None:
    try:
        atualizar_painel()
    except Exception as e:
        print(f"(aviso: não consegui atualizar o painel agora: {e})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--numero",
        type=str,
        nargs="+",
        help="Processa só esse(s) processo(s) (ex.: 00000.000000/0000-00, ou vários separados por espaço). "
        "Sem isso, processa TODOS da planilha.",
    )
    parser.add_argument(
        "--limite",
        type=int,
        help="Processa só os próximos N processos da planilha que ainda não estão concluídos "
        "(os 7 documentos OK no status). Ignorado se --numero for passado.",
    )
    parser.add_argument(
        "--so-erros",
        action="store_true",
        help="Processa só os processos da planilha que já foram tentados e não estão concluídos "
        "(deram erro). Pode ser combinado com --limite.",
    )
    parser.add_argument(
        "--lote",
        default="PT1",
        help="Qual planilha usar: data/Editaveis_<LOTE>.xlsx (ex.: PT4). O painel desse lote vai pra "
        "painel_documentos_<LOTE>.html (PT1 continua em painel_documentos.html). Padrão: PT1.",
    )
    args = parser.parse_args()

    config.definir_lote(args.lote)
    print(f"Lote {config.LOTE}: planilha {config.PLANILHA_PESSOAS.name}, painel {config.PAINEL_HTML.name}")

    if args.numero:
        numeros = args.numero
    else:
        df = carregar_planilha()
        numeros = [n.strip() for n in df[config.PLANILHA_COLUNA_PROCESSO_SEI].tolist() if n.strip()]
        if args.so_erros:
            status = carregar_status()
            numeros = [n for n in numeros if n in status and not processo_concluido(n, status)]
            print(f"--so-erros: {len(numeros)} processo(s) com erro: {numeros}")
            if args.limite is not None:
                numeros = numeros[: args.limite]
        elif args.limite is not None:
            status = carregar_status()
            pendentes = [n for n in numeros if not processo_concluido(n, status)]
            print(
                f"{len(numeros) - len(pendentes)} de {len(numeros)} processos da planilha já concluídos — "
                f"processando os próximos {min(args.limite, len(pendentes))}."
            )
            numeros = pendentes[: args.limite]
        else:
            print(f"Nenhum --numero informado — processando todos os {len(numeros)} processos da planilha.")

    if not numeros:
        print("Nada a processar.")
        return

    _atualizar_painel_seguro()

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)
        marcar_tempo("conexão")

        resultados: dict[str, bool] = {}
        for i, numero in enumerate(numeros, start=1):
            print(f"\n{'=' * 70}\n[{i}/{len(numeros)}] Processo {numero}\n{'=' * 70}")
            resultados[numero] = processar_processo(page, numero)
            _atualizar_painel_seguro()

            if i < len(numeros):
                sair_do_processo(page)

        print(f"\n{'=' * 70}\nResumo ({len(numeros)} processo(s)):")
        for numero, ok in resultados.items():
            print(f"  [{'OK' if ok else 'FALHOU'}] {numero}")

        if not all(resultados.values()):
            sys.exit(1)

        # Não fecha o navegador — é o Chrome que você abriu manualmente,
        # continua sob seu controle depois que a automação termina.


if __name__ == "__main__":
    main()
