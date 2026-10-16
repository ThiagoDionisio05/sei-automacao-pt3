"""Leitura da planilha de casos (720 linhas: 1 por pessoa/processo) usada
pra personalizar os documentos nativos da Parte 3.

Leitura robusta portada de sei-automaçaoPt2/src/validar_pastas.py
(`dtype=str` e `keep_default_na=False` pra nunca deixar o pandas inferir
tipo numérico — é isso que preserva zero à esquerda em CPF/matrícula/
processo; separador auto-detectado; "utf-8-sig" descarta o BOM que o Excel
grava ao exportar "CSV UTF-8").
"""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import config
from .campos_automaticos import mes_ano_por_extenso

# Colunas cujo valor precisa de uma pequena limpeza antes de entrar no
# documento — os templates nativos já têm o "R$" fixo no texto antes do
# campo "Valor_numerico" (ex.: "R$ **Valor_numerico**"), então o valor da
# planilha não pode repetir esse prefixo (senão vira "R$ R$ 57.50").
_COLUNAS_SEM_PREFIXO_RS = {"Valor_numerico"}


def carregar_planilha(caminho: Path | None = None) -> pd.DataFrame:
    # Lido na hora da chamada (não como default do parâmetro), pra respeitar
    # o lote escolhido em config.definir_lote().
    if caminho is None:
        caminho = config.PLANILHA_PESSOAS
    if not caminho.is_file():
        raise FileNotFoundError(f"Planilha não encontrada: {caminho}")

    if caminho.suffix.lower() == ".csv":
        return pd.read_csv(
            caminho,
            dtype=str,
            keep_default_na=False,
            sep=None,
            engine="python",
            encoding="utf-8-sig",
        )
    return pd.read_excel(caminho, dtype=str).fillna("")


def linha_do_processo(
    numero_processo: str,
    df: pd.DataFrame | None = None,
    coluna_processo: str = config.PLANILHA_COLUNA_PROCESSO_SEI,
) -> dict[str, str]:
    """Retorna a linha da planilha cujo `coluna_processo` bate exatamente
    com `numero_processo`, como um dict {nome_da_coluna: valor} — todos os
    valores já em string e sem espaço nas pontas. Levanta erro se achar 0
    ou mais de 1 linha (processo duplicado na planilha é erro de dado, não
    deveria escolher uma das duas silenciosamente).
    """
    if df is None:
        df = carregar_planilha()

    if coluna_processo not in df.columns:
        raise ValueError(
            f"Coluna '{coluna_processo}' não encontrada na planilha. "
            f"Colunas disponíveis: {list(df.columns)}"
        )

    alvo = numero_processo.strip()
    linhas = df[df[coluna_processo].str.strip() == alvo]

    if len(linhas) == 0:
        raise ValueError(f"Nenhuma linha da planilha tem '{coluna_processo}' = '{alvo}'.")
    if len(linhas) > 1:
        raise ValueError(
            f"{len(linhas)} linhas da planilha têm '{coluna_processo}' = '{alvo}' "
            "— processo duplicado na planilha, corrija antes de continuar."
        )

    linha = linhas.iloc[0]
    valores = {coluna: str(linha[coluna]).strip() for coluna in df.columns}

    for coluna in _COLUNAS_SEM_PREFIXO_RS:
        if coluna in valores:
            valores[coluna] = re.sub(r"^\s*R\$\s*", "", valores[coluna]).strip()

    competencias = _competencias_do_processo(valores)
    if competencias:
        valores["Mes_ano"] = ", ".join(competencias)

    return valores


def _competencias_do_processo(valores: dict[str, str]) -> list[str]:
    """Junta as colunas Competencia_1, Competencia_2, ... (ordem numérica,
    não alfabética) de uma pessoa, ignorando as vazias, já formatadas como
    "outubro/2020".
    """
    colunas = [c for c in valores if re.fullmatch(r"Competencia_\d+", c)]
    colunas.sort(key=lambda c: int(c.split("_")[1]))
    return [formatado for formatado in (_formatar_competencia(valores[c]) for c in colunas) if formatado]


def _formatar_competencia(valor: str) -> str:
    """Converte uma data da planilha ("2020-10-01 00:00:00", como o Excel
    entrega) em "outubro/2020". Se já vier em outro formato, devolve como
    está; célula vazia vira string vazia.
    """
    valor = valor.strip()
    if not valor:
        return ""
    try:
        data = datetime.fromisoformat(valor)
    except ValueError:
        return valor
    return mes_ano_por_extenso(data.year, data.month)
