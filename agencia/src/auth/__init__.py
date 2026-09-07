"""Parte F - autenticacao JWT: emissao, validacao e protecao das rotas."""

from src.auth.dependencias import (
    exigir_dono_da_conta,
    servico_autenticado,
    usuario_autenticado,
)
from src.auth.jwt_utils import (
    criar_token_servico,
    criar_token_usuario,
    decodificar_token,
)

__all__ = [
    "criar_token_servico",
    "criar_token_usuario",
    "decodificar_token",
    "exigir_dono_da_conta",
    "servico_autenticado",
    "usuario_autenticado",
]
