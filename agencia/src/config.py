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


# --- Parte F: autenticacao -------------------------------------------------

# A mesma chave secreta e compartilhada pelas 3 agencias. Isso e proposital: um
# token emitido pela Agencia 0 precisa ser aceito pelas Agencias 1 e 2, porque o
# frontend pode usar qualquer agencia como porta de entrada.
JWT_SEGREDO = os.getenv("JWT_SEGREDO", "iceibank-sprint1-segredo-de-desenvolvimento")
JWT_ALGORITMO = "HS256"

# Expiracao curta: o token nao pode ser eterno (requisito 2 da Parte F).
EXPIRACAO_TOKEN_MINUTOS = int(os.getenv("EXPIRACAO_TOKEN_MINUTOS", "15"))

# Expiracao bem curta para o token de servico entre agencias: ele existe apenas
# pela duracao de uma unica chamada creditar-remoto.
EXPIRACAO_TOKEN_SERVICO_SEGUNDOS = 30


def _hash(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


# Base de usuarios do banco. Cada usuario e dono de um conjunto de contas, o que
# permite verificar AUTORIZACAO (nao apenas autenticacao): um usuario logado nao
# consegue operar uma conta que nao e dele.
#
# Note que as contas de um mesmo usuario podem estar em agencias diferentes,
# ja que a particao e por id_conta % 3.
USUARIOS = {
    "ana": {"senha_hash": _hash("senha123"), "contas": [0, 3]},
    "bruno": {"senha_hash": _hash("senha123"), "contas": [1, 4]},
    "carla": {"senha_hash": _hash("senha123"), "contas": [2, 5]},
}


def credenciais_validas(usuario: str, senha: str) -> bool:
    registro = USUARIOS.get(usuario)
    if registro is None:
        return False
    return registro["senha_hash"] == _hash(senha)
