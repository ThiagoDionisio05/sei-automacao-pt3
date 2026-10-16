"""Status da Parte 3 por processo SEI: o que a automação realmente fez em
cada documento e no PAT. É a fonte da verdade que o painel
(gerar_painel.py) lê — grava logo depois de cada passo, então um erro no
meio de um lote fica registrado mesmo se o script parar.

Status possíveis por documento:
  "confirmado"  — criado/salvo agora
  "ja_existia"  — já estava na árvore, não foi recriado
  "falhou"      — tentou e deu erro (motivo em "erro")
"""

import json
from datetime import datetime, timezone

from . import config

STATUS_FILE = config.BASE_DIR / "status" / "processos_parte3.json"

DOCUMENTOS_PARTE3 = [
    ("rpdea", "RPDEA"),
    ("checklist", "Checklist"),
    ("nota_tecnica", "Nota Técnica"),
    ("ateste", "Ateste Orç."),
    ("tdea", "TDEA"),
    ("comprovante_siape", "Comprovante SIAPE"),
    ("despacho", "Despacho"),
]


def _agora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def carregar_status() -> dict:
    if not STATUS_FILE.is_file():
        return {}
    return json.loads(STATUS_FILE.read_text(encoding="utf-8"))


def _salvar(status: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def _processo(status: dict, numero: str) -> dict:
    return status.setdefault(numero, {"documentos": {}})


def registrar_documento(numero: str, chave: str, situacao: str, erro: str | None = None) -> None:
    status = carregar_status()
    entrada = {"situacao": situacao, "atualizado_em": _agora()}
    if erro:
        entrada["erro"] = erro
    _processo(status, numero)["documentos"][chave] = entrada
    _salvar(status)


def registrar_pat(numero: str, pat: str, situacao: str, erro: str | None = None) -> None:
    status = carregar_status()
    entrada = {"pat": pat, "situacao": situacao, "atualizado_em": _agora()}
    if erro:
        entrada["erro"] = erro
    _processo(status, numero)["pat"] = entrada
    _salvar(status)


def registrar_erro_processo(numero: str, situacao: str, erro: str) -> None:
    """Erro que impede o processo inteiro (ex.: Partes 1/2 incompletas,
    processo não encontrado) — não é de um documento específico."""
    status = carregar_status()
    _processo(status, numero)["erro_geral"] = {
        "situacao": situacao,
        "erro": erro,
        "atualizado_em": _agora(),
    }
    _salvar(status)


def processo_concluido(numero: str, status: dict) -> bool:
    """True se os 7 documentos da Parte 3 já estão registrados como criados
    (ou já existentes) e não há erro geral pendente — usado pelo --limite
    do main.py pra pular o que já foi feito e pegar os próximos."""
    s = status.get(numero, {})
    if s.get("erro_geral"):
        return False
    docs = s.get("documentos", {})
    return all(
        docs.get(chave, {}).get("situacao") in ("confirmado", "ja_existia") for chave, _ in DOCUMENTOS_PARTE3
    )


def limpar_erro_processo(numero: str) -> None:
    status = carregar_status()
    if numero in status:
        status[numero].pop("erro_geral", None)
        _salvar(status)
