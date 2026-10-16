"""Campos usados na personalização dos documentos nativos que NÃO vêm da
planilha — data de hoje (dois formatos) e números de documentos gerados
durante a própria execução (Nota Técnica, TDEA), que só existem depois que
o SEI cria o documento correspondente.
"""

from datetime import date

_MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def mes_ano_por_extenso(ano: int, mes: int) -> str:
    """"outubro/2020" — formato usado no campo Mes_ano dos documentos."""
    return f"{_MESES_PT[mes - 1].lower()}/{ano}"


def campos_de_data(hoje: date | None = None) -> dict[str, str]:
    """Retorna os campos "data_hoje" (21/09/2026) e "Data_extenso" (21 de
    Setembro de 2026) — mesma data em dois formatos, pros dois IDs.
    """
    hoje = hoje or date.today()
    return {
        "data_hoje": hoje.strftime("%d/%m/%Y"),
        "Data_extenso": f"{hoje.day} de {_MESES_PT[hoje.month - 1]} de {hoje.year}",
    }
