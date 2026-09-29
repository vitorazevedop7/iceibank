"""Parte C - controller de contas: criar, consultar, depositar e sacar.

Toda operacao que altera ou cria estado gera um evento local no relogio vetorial
(regra 1) e e registrada no log da agencia.
"""

from fastapi import HTTPException, status

from src import config
from src.auth import exigir_dono_da_conta
from src.models import Conta, CriarContaRequest, ValorRequest


def _conta_ou_404(estado, id_conta: int) -> Conta:
    conta = estado.contas.get(id_conta)
    if conta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"erro": f"Conta {id_conta} nao encontrada nesta agencia."},
        )
    return conta


async def criar_conta(dados: CriarContaRequest, estado, usuario: dict) -> dict:
    exigir_dono_da_conta(usuario, dados.id)

    # Particionamento: a agencia recusa operar contas que nao sao suas.
    if config.agencia_responsavel(dados.id) != estado.id_agencia:
        dona = config.agencia_responsavel(dados.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "erro": f"Conta {dados.id} nao pertence a esta agencia. "
                f"Responsavel: Agencia {dona} ({config.url_da_agencia(dona)})."
            },
        )

    if dados.id in estado.contas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"erro": f"Conta {dados.id} ja existe."},
        )

    ts = await estado.relogio.evento_local()
    estado.contas[dados.id] = Conta(
        id=dados.id, nome_aluno=dados.nomeAluno, saldo=dados.saldoInicial
    )
    estado.registro.registrar(
        "CRIAR_CONTA",
        ts,
        {"id": dados.id, "nomeAluno": dados.nomeAluno, "saldoInicial": dados.saldoInicial},
    )
    return estado.contas[dados.id].para_dict()


async def consultar_saldo(id_conta: int, estado, usuario: dict) -> dict:
    exigir_dono_da_conta(usuario, id_conta)
    return _conta_ou_404(estado, id_conta).para_dict()


async def depositar(id_conta: int, dados: ValorRequest, estado, usuario: dict) -> dict:
    exigir_dono_da_conta(usuario, id_conta)
    conta = _conta_ou_404(estado, id_conta)

    ts = await estado.relogio.evento_local()
    conta.saldo += dados.valor
    estado.registro.registrar(
        "DEPOSITO", ts, {"id": id_conta, "valor": dados.valor, "novoSaldo": conta.saldo}
    )
    return conta.para_dict()


async def sacar(id_conta: int, dados: ValorRequest, estado, usuario: dict) -> dict:
    exigir_dono_da_conta(usuario, id_conta)
    conta = _conta_ou_404(estado, id_conta)

    if conta.saldo < dados.valor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "erro": f"Saldo insuficiente. Saldo atual: {conta.saldo}, "
                f"valor solicitado: {dados.valor}."
            },
        )

    ts = await estado.relogio.evento_local()
    conta.saldo -= dados.valor
    estado.registro.registrar(
        "SAQUE", ts, {"id": id_conta, "valor": dados.valor, "novoSaldo": conta.saldo}
    )
    return conta.para_dict()


async def status_agencia(estado) -> dict:
    """Rota utilitaria: identidade da agencia, relogio atual e contas sob sua guarda."""
    return {
        "agencia": estado.id_agencia,
        "relogioVetorial": await estado.relogio.valor_atual(),
        "quantidadeContas": len(estado.contas),
        "contas": sorted(estado.contas.keys()),
    }
