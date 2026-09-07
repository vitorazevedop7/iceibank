"""Camada de rotas (APIRouter): declara os endpoints e delega para os controllers.

Nenhuma regra de negocio mora aqui - esta camada so amarra caminho HTTP,
validacao de schema e o controller correspondente.
"""

from fastapi import APIRouter, Request

from src.controllers import contas_controller
from src.controllers import transferencias_controller as transferencias
from src.models import (
    CreditoRemotoRequest,
    CriarContaRequest,
    TransferenciaRequest,
    ValorRequest,
)

router = APIRouter()


def _estado(request: Request):
    return request.app.state


# --- Parte C: contas ---------------------------------------------------------


@router.post("/contas", status_code=201, tags=["contas"])
async def rota_criar_conta(dados: CriarContaRequest, request: Request):
    return await contas_controller.criar_conta(dados, _estado(request))


@router.get("/contas/{id_conta}", tags=["contas"])
async def rota_consultar_saldo(id_conta: int, request: Request):
    return await contas_controller.consultar_saldo(id_conta, _estado(request))


@router.post("/contas/{id_conta}/depositar", tags=["contas"])
async def rota_depositar(id_conta: int, dados: ValorRequest, request: Request):
    return await contas_controller.depositar(id_conta, dados, _estado(request))


@router.post("/contas/{id_conta}/sacar", tags=["contas"])
async def rota_sacar(id_conta: int, dados: ValorRequest, request: Request):
    return await contas_controller.sacar(id_conta, dados, _estado(request))


# --- Parte D: transferencias -------------------------------------------------


@router.post("/transferencias", tags=["transferencias"])
async def rota_transferir(dados: TransferenciaRequest, request: Request):
    return await transferencias.transferir(dados, _estado(request))


@router.post("/contas/{id_conta}/creditar-remoto", tags=["transferencias"])
async def rota_creditar_remoto(
    id_conta: int, dados: CreditoRemotoRequest, request: Request
):
    """Rota interna, chamada por outra agencia."""
    return await transferencias.creditar_remoto(id_conta, dados, _estado(request))


# --- Rota utilitaria ---------------------------------------------------------


@router.get("/status", tags=["status"])
async def rota_status(request: Request):
    return await contas_controller.status_agencia(_estado(request))
