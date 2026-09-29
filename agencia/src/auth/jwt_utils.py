"""Emissao e validacao dos tokens JWT usados pelo ICEIBank.

O token de usuario e emitido no login e representa uma pessoa dona de contas.
Carrega a claim `contas` com os ids que ela pode operar, o que permite verificar
autorizacao sem consultar nenhuma base a cada requisicao.

No Sprint 1 existia tambem um token de servico, usado por uma agencia para chamar
a rota interna creditar-remoto de outra. Com a mensageria do Sprint 2 essa rota
deixou de existir, e o token de servico saiu junto.
"""

from datetime import datetime, timedelta, timezone

import jwt

from src import config


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def criar_token_usuario(usuario: str, contas: list[int]) -> tuple[str, int]:
    """Token de pessoa. Devolve (token, segundos_ate_expirar)."""
    expiracao = timedelta(minutes=config.EXPIRACAO_TOKEN_MINUTOS)
    payload = {
        "sub": usuario,
        "tipo": "usuario",
        "contas": contas,
        "iat": _agora(),
        "exp": _agora() + expiracao,
    }
    token = jwt.encode(payload, config.JWT_SEGREDO, algorithm=config.JWT_ALGORITMO)
    return token, int(expiracao.total_seconds())


def decodificar_token(token: str) -> dict:
    """Valida assinatura e expiracao. Levanta jwt.PyJWTError se o token nao servir.

    A validacao e puramente criptografica: a agencia confere a assinatura com a
    chave secreta que ja possui, sem consultar banco de dados nem estado de sessao.
    """
    return jwt.decode(token, config.JWT_SEGREDO, algorithms=[config.JWT_ALGORITMO])
