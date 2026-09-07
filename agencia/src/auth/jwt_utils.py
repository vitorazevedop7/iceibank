"""Emissao e validacao dos tokens JWT usados pelo ICEIBank.

Existem dois tipos de token, distinguidos pela claim `tipo`:

- `usuario`  : emitido no login, representa uma pessoa dona de contas. Carrega a
               claim `contas` com os ids que ela pode operar, o que permite
               verificar autorizacao sem consultar nenhuma base a cada requisicao.
- `servico`  : emitido por uma agencia para chamar outra agencia (creditar-remoto).
               Nao pertence a nenhuma pessoa e vive apenas alguns segundos.
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


def criar_token_servico(id_agencia: int) -> str:
    """Token que uma agencia usa para se identificar perante outra agencia."""
    payload = {
        "sub": f"agencia-{id_agencia}",
        "tipo": "servico",
        "agencia": id_agencia,
        "iat": _agora(),
        "exp": _agora()
        + timedelta(seconds=config.EXPIRACAO_TOKEN_SERVICO_SEGUNDOS),
    }
    return jwt.encode(payload, config.JWT_SEGREDO, algorithm=config.JWT_ALGORITMO)


def decodificar_token(token: str) -> dict:
    """Valida assinatura e expiracao. Levanta jwt.PyJWTError se o token nao servir.

    A validacao e puramente criptografica: a agencia confere a assinatura com a
    chave secreta que ja possui, sem consultar banco de dados nem estado de sessao.
    """
    return jwt.decode(token, config.JWT_SEGREDO, algorithms=[config.JWT_ALGORITMO])
