"""Parte F - controller de autenticacao."""

from fastapi import HTTPException, status

from src import config
from src.auth import criar_token_usuario
from src.models import LoginRequest, TokenResponse


async def login(dados: LoginRequest) -> TokenResponse:
    """Valida credenciais e devolve um JWT com prazo de validade."""
    if not config.credenciais_validas(dados.usuario, dados.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"erro": "Usuario ou senha invalidos."},
        )
    contas = config.USUARIOS[dados.usuario]["contas"]
    token, expira_em = criar_token_usuario(dados.usuario, contas)
    return TokenResponse(access_token=token, expira_em_segundos=expira_em)
