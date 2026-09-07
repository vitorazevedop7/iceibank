"""Dependencias do FastAPI que protegem as rotas (Parte F)."""

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.jwt_utils import decodificar_token

# auto_error=False para que a ausencia de cabecalho tambem passe por aqui e
# devolva 401 no nosso formato de erro, e nao 403 do proprio FastAPI.
_esquema_bearer = HTTPBearer(auto_error=False)


def _nao_autorizado(detalhe: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"erro": detalhe},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _payload_valido(credenciais: HTTPAuthorizationCredentials | None) -> dict:
    if credenciais is None:
        raise _nao_autorizado("Token ausente. Envie 'Authorization: Bearer <token>'.")
    try:
        return decodificar_token(credenciais.credentials)
    except jwt.ExpiredSignatureError:
        raise _nao_autorizado("Token expirado. Faca login novamente.")
    except jwt.PyJWTError:
        raise _nao_autorizado("Token invalido.")


def usuario_autenticado(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
) -> dict:
    """Exige um token de pessoa valido. Usada nas rotas vindas do frontend."""
    payload = _payload_valido(credenciais)
    if payload.get("tipo") != "usuario":
        raise _nao_autorizado("Este token nao autoriza operacoes de usuario.")
    return payload


def servico_autenticado(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
) -> dict:
    """Exige um token de servico valido. Usada apenas na rota creditar-remoto.

    A rota interna e protegida, mas por uma credencial diferente: quem chama nao e
    uma pessoa, e outra agencia. Tratar a rede interna como confiavel seria abrir um
    caminho sem autenticacao para creditar qualquer conta.
    """
    payload = _payload_valido(credenciais)
    if payload.get("tipo") != "servico":
        raise _nao_autorizado("Esta rota so aceita token de servico entre agencias.")
    return payload


def exigir_dono_da_conta(payload: dict, id_conta: int) -> None:
    """Autorizacao: o usuario autenticado e dono da conta que quer operar?

    Autenticacao ("quem e voce") ja foi resolvida pelo token. Aqui verificamos
    autorizacao ("voce pode mexer nesta conta"), usando a claim `contas`.
    """
    if id_conta not in payload.get("contas", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "erro": f"Usuario '{payload.get('sub')}' nao e dono da conta {id_conta}."
            },
        )


def estado(request: Request):
    """Atalho para o estado do processo da agencia (equivalente ao app.locals)."""
    return request.app.state
