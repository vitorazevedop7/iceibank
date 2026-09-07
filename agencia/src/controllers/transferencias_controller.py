"""Parte D - controller de transferencias (local e entre agencias)."""

import httpx
from fastapi import HTTPException, status

from src import config
from src.auth import criar_token_servico, exigir_dono_da_conta
from src.models import CreditoRemotoRequest, TransferenciaRequest

_TEMPO_LIMITE = httpx.Timeout(5.0)


async def transferir(dados: TransferenciaRequest, estado, usuario: dict) -> dict:
    exigir_dono_da_conta(usuario, dados.idOrigem)
    return await _executar_transferencia(dados, estado)


async def _executar_transferencia(dados: TransferenciaRequest, estado) -> dict:
    conta_origem = estado.contas.get(dados.idOrigem)
    if conta_origem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "erro": f"Conta de origem {dados.idOrigem} nao encontrada nesta agencia."
            },
        )
    if conta_origem.saldo < dados.valor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "erro": f"Saldo insuficiente. Saldo atual: {conta_origem.saldo}, "
                f"valor solicitado: {dados.valor}."
            },
        )

    agencia_destino = config.agencia_responsavel(dados.idDestino)

    # --- Caso 1: mesma agencia --------------------------------------------
    # Debito e credito acontecem no mesmo processo. Nao ha mensagem trocada entre
    # processos, entao nao ha nada para sincronizar: bastam dois eventos locais.
    if agencia_destino == estado.id_agencia:
        conta_destino = estado.contas.get(dados.idDestino)
        if conta_destino is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "erro": f"Conta de destino {dados.idDestino} nao encontrada nesta agencia."
                },
            )

        ts_debito = await estado.relogio.evento_local()
        conta_origem.saldo -= dados.valor
        estado.registro.registrar(
            "TRANSFERENCIA_DEBITO",
            ts_debito,
            {"idOrigem": dados.idOrigem, "idDestino": dados.idDestino, "valor": dados.valor},
        )

        ts_credito = await estado.relogio.evento_local()
        conta_destino.saldo += dados.valor
        estado.registro.registrar(
            "TRANSFERENCIA_CREDITO",
            ts_credito,
            {"idOrigem": dados.idOrigem, "idDestino": dados.idDestino, "valor": dados.valor},
        )
        return {
            "mensagem": "Transferencia concluida (mesma agencia).",
            "escopo": "local",
            "saldoOrigem": conta_origem.saldo,
            "timestampLamport": ts_credito,
        }

    # --- Caso 2: entre agencias -------------------------------------------
    # O debito e sempre local, pois esta agencia e a dona da conta de origem.
    ts_debito = await estado.relogio.evento_local()
    conta_origem.saldo -= dados.valor
    estado.registro.registrar(
        "TRANSFERENCIA_DEBITO",
        ts_debito,
        {
            "idOrigem": dados.idOrigem,
            "idDestino": dados.idDestino,
            "valor": dados.valor,
            "agenciaDestino": agencia_destino,
        },
    )

    # Regra 2 de Lamport: incrementa e anexa o timestamp a mensagem enviada.
    ts_envio = await estado.relogio.ao_enviar()
    url_destino = config.url_da_agencia(agencia_destino)

    try:
        async with httpx.AsyncClient(timeout=_TEMPO_LIMITE) as cliente:
            resposta = await cliente.post(
                f"{url_destino}/contas/{dados.idDestino}/creditar-remoto",
                json={
                    "valor": dados.valor,
                    "timestampLamport": ts_envio,
                    "origemAgencia": estado.id_agencia,
                },
                headers={
                    # Token de servico: quem chama e outra agencia, nao uma pessoa.
                    "Authorization": f"Bearer {criar_token_servico(estado.id_agencia)}"
                },
            )
            resposta.raise_for_status()
    except Exception as erro:
        # LIMITACAO CONHECIDA DESTE SPRINT: o debito aplicado acima NAO e revertido.
        # O dinheiro "desaparece" temporariamente. Garantir atomicidade sob falha e
        # o assunto do Sprint 4 (2PC ou Saga). Por enquanto apenas registramos a
        # inconsistencia no log, em vez de esconde-la.
        ts_falha = await estado.relogio.evento_local()
        estado.registro.registrar(
            "TRANSFERENCIA_FALHOU",
            ts_falha,
            {
                "idOrigem": dados.idOrigem,
                "idDestino": dados.idDestino,
                "valor": dados.valor,
                "agenciaDestino": agencia_destino,
                "erro": f"{type(erro).__name__}: {erro}",
                "inconsistencia": "debito aplicado sem credito correspondente",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "erro": "Falha ao contatar a agencia de destino. Debito ja aplicado - "
                "inconsistencia conhecida deste sprint (ver Sprint 4).",
                "saldoOrigem": conta_origem.saldo,
                "valorEmTransito": dados.valor,
            },
        )

    return {
        "mensagem": "Transferencia concluida (entre agencias).",
        "escopo": "entre-agencias",
        "agenciaDestino": agencia_destino,
        "saldoOrigem": conta_origem.saldo,
        "timestampLamport": ts_envio,
    }


async def creditar_remoto(
    id_conta: int, dados: CreditoRemotoRequest, estado, servico: dict
) -> dict:
    """Recebe o credito enviado por outra agencia.

    Regra 3 de Lamport: o relogio local e ajustado com base no timestamp recebido,
    para max(local, recebido) + 1.
    """
    ts = await estado.relogio.ao_receber(dados.timestampLamport)

    conta = estado.contas.get(id_conta)
    if conta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"erro": f"Conta {id_conta} nao encontrada nesta agencia."},
        )

    conta.saldo += dados.valor
    estado.registro.registrar(
        "TRANSFERENCIA_CREDITO_REMOTO",
        ts,
        {
            "idConta": id_conta,
            "valor": dados.valor,
            "origemAgencia": dados.origemAgencia,
            "timestampRecebido": dados.timestampLamport,
            "chamadaPor": servico.get("sub"),
        },
    )
    return {
        "mensagem": "Credito remoto aplicado.",
        "saldoAtual": conta.saldo,
        "timestampLamport": ts,
    }
