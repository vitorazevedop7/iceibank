"""Parte A - configuracao da agencia e particionamento de contas entre as 3 agencias."""

import hashlib
import os

# OFFSET pessoal (dois ultimos digitos da matricula), necessario apenas em maquina
# compartilhada de laboratorio. Pode ser sobrescrito por variavel de ambiente.
OFFSET = int(os.getenv("OFFSET", "0"))

NUMERO_AGENCIAS = 3
PORTA_BASE = 4000 + OFFSET

AGENCIAS = [
    {"id": 0, "url": f"http://localhost:{PORTA_BASE}"},
    {"id": 1, "url": f"http://localhost:{PORTA_BASE + 1}"},
    {"id": 2, "url": f"http://localhost:{PORTA_BASE + 2}"},
]


def agencia_responsavel(id_conta: int) -> int:
    """Retorna o id da agencia dona da conta.

    A particao e por resto da divisao: conta 0 -> Agencia 0, conta 1 -> Agencia 1,
    conta 2 -> Agencia 2, conta 3 -> Agencia 0, e assim por diante. Cada conta
    pertence a exatamente uma agencia (particao, nao replicacao).
    """
    return id_conta % NUMERO_AGENCIAS


def url_da_agencia(id_agencia: int) -> str:
    """Endereco HTTP da agencia informada."""
    return next(a["url"] for a in AGENCIAS if a["id"] == id_agencia)
