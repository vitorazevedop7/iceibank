"""Camada de rotas (APIRouter): declara os endpoints e delega para os controllers.

Nenhuma regra de negocio mora aqui - esta camada so amarra caminho HTTP,
validacao de schema e dependencia de autenticacao ao controller correspondente.
"""

from fastapi import APIRouter, Depends, Header, Request

from src.auth import usuario_autenticado
from src.controllers import auth_controller, contas_controller
from src.controllers import transferencias_controller as transferencias
from src.models import (
    CriarContaRequest,
    LoginRequest,
    TokenResponse,
    TransferenciaRequest,
    ValorRequest,
)

router = APIRouter()


def _estado(request: Request):
    return request.app.state


# --- Parte F: autenticacao (rota publica) ----------------------------------


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def rota_login(dados: LoginRequest):
    return await auth_controller.login(dados)


# --- Parte C: contas (rotas protegidas) ------------------------------------


@router.post("/contas", status_code=201, tags=["contas"])
async def rota_criar_conta(
    dados: CriarContaRequest,
    request: Request,
    usuario: dict = Depends(usuario_autenticado),
):
    return await contas_controller.criar_conta(dados, _estado(request), usuario)


@router.get("/contas/{id_conta}", tags=["contas"])
async def rota_consultar_saldo(
    id_conta: int, request: Request, usuario: dict = Depends(usuario_autenticado)
):
    return await contas_controller.consultar_saldo(id_conta, _estado(request), usuario)


@router.post("/contas/{id_conta}/depositar", tags=["contas"])
async def rota_depositar(
    id_conta: int,
    dados: ValorRequest,
    request: Request,
    usuario: dict = Depends(usuario_autenticado),
):
    return await contas_controller.depositar(id_conta, dados, _estado(request), usuario)


@router.post("/contas/{id_conta}/sacar", tags=["contas"])
async def rota_sacar(
    id_conta: int,
    dados: ValorRequest,
    request: Request,
    usuario: dict = Depends(usuario_autenticado),
):
    return await contas_controller.sacar(id_conta, dados, _estado(request), usuario)


# --- Parte D: transferencias -----------------------------------------------
#
# Sprint 2: a rota interna /contas/{id}/creditar-remoto deixou de existir. O
# credito vindo de outra agencia chega pelo RabbitMQ (ver services/mensageria.py).


@router.post("/transferencias", tags=["transferencias"])
async def rota_transferir(
    dados: TransferenciaRequest,
    request: Request,
    usuario: dict = Depends(usuario_autenticado),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    return await transferencias.transferir(
        dados, _estado(request), usuario, idempotency_key
    )


# --- Rota utilitaria (publica) ---------------------------------------------


@router.get("/status", tags=["status"])
async def rota_status(request: Request):
    return await contas_controller.status_agencia(_estado(request))
