"""Gera o painel HTML (só leitura) da Parte 3: uma linha por processo da
planilha, com cada um dos 7 documentos, o PAT e erros.

Lê a planilha do lote (data/Editaveis_PT1.xlsx por padrão) e o status
gravado pela automação (status/processos_parte3.json). Rode de novo sempre
que quiser atualizar:

    python -m src.gerar_painel              # PT1 -> painel_documentos.html
    python -m src.gerar_painel --lote PT4   # PT4 -> painel_documentos_PT4.html
"""

import argparse
import html

import pandas as pd

from . import config
from .status_processos import DOCUMENTOS_PARTE3, carregar_status

_SITUACAO_DOC = {
    "confirmado": ("ok", "criado"),
    "ja_existia": ("ok", "já existia"),
    "falhou": ("falha", "falhou"),
}


def montar_linhas(df: pd.DataFrame, status: dict) -> list[dict]:
    linhas = []
    for _, row in df.iterrows():
        numero = str(row.get(config.PLANILHA_COLUNA_PROCESSO_SEI, "")).strip()
        if not numero:
            continue

        s = status.get(numero, {})
        docs = s.get("documentos", {})
        pat_info = None
        erro_geral = s.get("erro_geral")

        cel_docs = []
        erros = []
        for chave, rotulo in DOCUMENTOS_PARTE3:
            info = docs.get(chave)
            if info is None:
                cel_docs.append(("pendente", "—", rotulo))
                continue
            classe, texto = _SITUACAO_DOC.get(info["situacao"], ("pendente", info["situacao"]))
            cel_docs.append((classe, texto, rotulo))
            if info.get("erro"):
                erros.append(f"{rotulo}: {info['erro']}")

        # O PAT saiu do fluxo do main.py (vai ser feito à parte) — a coluna
        # continua no painel só como informação, sem pesar na situação.
        docs_ok = sum(1 for c, _, _ in cel_docs if c == "ok")
        tem_falha = any(c == "falha" for c, _, _ in cel_docs)

        if erro_geral:
            erros.insert(0, f"Processo: {erro_geral.get('erro', '')}")

        if docs_ok == len(DOCUMENTOS_PARTE3) and not tem_falha:
            situacao = "concluido"
        elif tem_falha or erro_geral:
            situacao = "erro"
        elif docs_ok:
            situacao = "parcial"
        else:
            situacao = "pendente"

        linhas.append(
            {
                "processo": numero,
                "nome": str(row.get("Nome", "")).strip(),
                "matricula": str(row.get("Matrícula", "")).strip(),
                "pat": (pat_info or {}).get("pat") or str(row.get("PAT", "")).strip(),
                "pat_situacao": (pat_info or {}).get("situacao", "pendente"),
                "docs": cel_docs,
                "docs_ok": docs_ok,
                "situacao": situacao,
                "erros": erros,
                "atualizado_em": max(
                    [i["atualizado_em"] for i in docs.values()]
                    + ([pat_info["atualizado_em"]] if pat_info else [])
                    + ([erro_geral["atualizado_em"]] if erro_geral else []),
                    default="",
                ),
            }
        )
    return linhas


_ROTULO_SITUACAO = {
    "concluido": "Concluído",
    "parcial": "Em andamento",
    "erro": "Com erro",
    "pendente": "Pendente",
}


def _celula_doc(classe: str, texto: str) -> str:
    return f'<span class="badge {classe}">{html.escape(texto)}</span>'


def gerar_html(linhas: list[dict]) -> str:
    total = len(linhas)
    contagem = {k: sum(1 for l in linhas if l["situacao"] == k) for k in _ROTULO_SITUACAO}

    cabecalhos = "".join(f"<th>{html.escape(r)}</th>" for _, r in DOCUMENTOS_PARTE3)

    corpo = []
    for l in linhas:
        erros_html = (
            "<br>".join(html.escape(e) for e in l["erros"]) if l["erros"] else ""
        )
        celulas_docs = "".join(
            f'<td title="{html.escape(rotulo)}">{_celula_doc(c, t)}</td>' for c, t, rotulo in l["docs"]
        )
        pat_classe = "ok" if l["pat_situacao"] in ("adicionado", "ja_estava") else (
            "falha" if l["pat_situacao"] == "falhou" else "pendente"
        )
        corpo.append(
            f'<tr class="linha-{l["situacao"]}" data-busca="{html.escape((l["nome"] + " " + l["processo"] + " " + l["matricula"]).lower())}">'
            f"<td class='col-processo'>{html.escape(l['processo'])}</td>"
            f"<td>{html.escape(l['nome'])}</td>"
            f"<td>{html.escape(l['matricula'])}</td>"
            f"<td>{html.escape(l['pat'])} {_celula_doc(pat_classe, {'adicionado': 'adicionado', 'ja_estava': 'já estava', 'falhou': 'falhou'}.get(l['pat_situacao'], 'pendente'))}</td>"
            f"{celulas_docs}"
            f'<td><span class="situacao {l["situacao"]}">{_ROTULO_SITUACAO[l["situacao"]]}</span></td>'
            f'<td class="col-erro">{erros_html}</td>'
            f"<td class='col-data'>{html.escape(l['atualizado_em'])}</td>"
            "</tr>"
        )

    return _TEMPLATE.format(
        total=total,
        concluidos=contagem["concluido"],
        parciais=contagem["parcial"],
        erros=contagem["erro"],
        pendentes=contagem["pendente"],
        cabecalhos=cabecalhos,
        corpo="\n".join(corpo),
        lote=html.escape(config.LOTE),
        planilha=html.escape(f"data/{config.PLANILHA_PESSOAS.name}"),
    )


_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="20">
<title>Painel — Parte 3 ({lote})</title>
<style>
  :root {{ --bg:#f4f6f8; --card:#fff; --border:#dde2e7; --text:#1f2933; --muted:#6b7684;
          --ok:#0b6e4f; --ok-bg:#eafaf1; --danger:#c0392b; --danger-bg:#fdecea;
          --warn:#8a6d00; --warn-bg:#fff6d6; --header:#eef2f4; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:28px 20px 60px; background:var(--bg); color:var(--text);
         font-family:"Segoe UI",Tahoma,Verdana,Arial,sans-serif; font-size:13px; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  .sub {{ color:var(--muted); margin-bottom:16px; }}
  .stats {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px; }}
  .stat {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:10px 14px; min-width:120px; }}
  .stat b {{ display:block; font-size:18px; }}
  .stat.erro b {{ color:var(--danger); }}
  .stat.ok b {{ color:var(--ok); }}
  .toolbar {{ margin-bottom:10px; }}
  .toolbar input {{ font:inherit; padding:7px 10px; border:1px solid var(--border); border-radius:7px; width:320px; }}
  .wrap {{ overflow-x:auto; background:var(--card); border:1px solid var(--border); border-radius:10px; }}
  table {{ border-collapse:collapse; width:100%; }}
  th {{ text-align:left; font-size:11.5px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted);
        padding:9px 10px; background:var(--header); border-bottom:1px solid var(--border); position:sticky; top:0; white-space:nowrap; }}
  td {{ padding:8px 10px; border-bottom:1px solid var(--border); vertical-align:middle; white-space:nowrap; }}
  td.col-erro {{ white-space:normal; color:var(--danger); font-size:12px; max-width:320px; }}
  td.col-data {{ color:var(--muted); font-size:12px; }}
  tr.linha-erro {{ background:var(--danger-bg); }}
  tr.linha-parcial {{ background:var(--warn-bg); }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:11.5px; font-weight:600; }}
  .badge.ok {{ background:var(--ok-bg); color:var(--ok); }}
  .badge.falha {{ background:var(--danger-bg); color:var(--danger); }}
  .badge.pendente {{ background:var(--header); color:var(--muted); }}
  .situacao {{ font-weight:600; }}
  .situacao.concluido {{ color:var(--ok); }}
  .situacao.erro {{ color:var(--danger); }}
  .situacao.parcial {{ color:var(--warn); }}
  .situacao.pendente {{ color:var(--muted); }}
</style>
</head>
<body>
  <h1>Painel — Parte 3 ({lote})</h1>
  <div class="sub">Gerado a partir de <code>{planilha}</code> e <code>status/processos_parte3.json</code> (o que a automação fez no SEI). Pra atualizar: <code>python -m src.gerar_painel --lote {lote}</code>.</div>

  <div class="stats">
    <div class="stat"><span>Total</span><b>{total}</b></div>
    <div class="stat ok"><span>Concluídos</span><b>{concluidos}</b></div>
    <div class="stat"><span>Em andamento</span><b>{parciais}</b></div>
    <div class="stat erro"><span>Com erro</span><b>{erros}</b></div>
    <div class="stat"><span>Pendentes</span><b>{pendentes}</b></div>
  </div>

  <div class="toolbar"><input id="busca" type="search" placeholder="Filtrar por nome, matrícula ou processo…"></div>

  <div class="wrap">
    <table>
      <thead>
        <tr>
          <th>Processo SEI</th><th>Nome</th><th>Matrícula</th><th>PAT</th>
          {cabecalhos}
          <th>Situação</th><th>Erros</th><th>Atualizado em</th>
        </tr>
      </thead>
      <tbody id="corpo">
{corpo}
      </tbody>
    </table>
  </div>

<script>
  document.getElementById("busca").addEventListener("input", (e) => {{
    const termo = e.target.value.trim().toLowerCase();
    document.querySelectorAll("#corpo tr").forEach((tr) => {{
      tr.hidden = termo && !tr.dataset.busca.includes(termo);
    }});
  }});
</script>
</body>
</html>
"""


def atualizar_painel() -> None:
    """Regenera o HTML a partir da planilha e do status atual. Chamada pela
    automação depois de cada processo, então o painel acompanha o lote.
    Planilha e arquivo de saída vêm do lote atual (config.definir_lote)."""
    df = pd.read_excel(config.PLANILHA_PESSOAS, dtype=str).fillna("")
    linhas = montar_linhas(df, carregar_status())
    config.PAINEL_HTML.write_text(gerar_html(linhas), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lote", default="PT1", help="Lote/planilha do painel (ex.: PT4). Padrão: PT1.")
    config.definir_lote(parser.parse_args().lote)

    if not config.PLANILHA_PESSOAS.is_file():
        raise SystemExit(f"Planilha não encontrada: {config.PLANILHA_PESSOAS}")

    atualizar_painel()
    print(f"Painel gerado em {config.PAINEL_HTML}.")


if __name__ == "__main__":
    main()
