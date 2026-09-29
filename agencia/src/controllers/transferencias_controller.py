"""Parte D - controller de transferencias (local e entre agencias).

Sprint 2: a transferencia entre agencias deixou de ser uma chamada REST direta.
A agencia de origem publica uma mensagem no RabbitMQ e a agencia de destino a
consome de forma assincrona (`processar_credito_remoto`).

Mantem a funcionalidade adicional do Sprint 1: idempotencia via cabecalho
`Idempotency-Key`, para que o reenvio de uma mesma transferencia nao aplique o
debito duas vezes.
"""

import uuid

from fastapi import HTTPException, status
from pydantic import ValidationError

from src import config
from src.auth import exigir_dono_da_conta
from src.models import MensagemCredito, TransferenciaRequest
from src.services.mensageria import routing_key_credito

# Marcador de operacao ainda em andamento no cache de idempotencia.
_EM_ANDAMENTO = object()


async def transferir(
    dados: TransferenciaRequest, estado, usuario: dict, chave_idempotencia: str | None
) -> dict:
    exigir_dono_da_conta(usuario, dados.idOrigem)

    # --- Funcionalidade adicional: idempotencia -----------------------------
    if chave_idempotencia:
        registrado = estado.idempotencia.get(chave_idempotencia)
        if registrado is _EM_ANDAMENTO:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "erro": "Uma transferencia com esta Idempotency-Key ainda esta em andamento."
                },
            )
        if registrado is not None:
            ts = await estado.relogio.evento_local()
            estado.registro.registrar(
                "TRANSFERENCIA_REPETIDA_IGNORADA",
                ts,
                {
                    "chaveIdempotencia": chave_idempotencia,
                    "idOrigem": dados.idOrigem,
                    "idDestino": dados.idDestino,
                    "valor": dados.valor,
                },
            )
            return {**registrado, "repetida": True}
        estado.idempotencia[chave_idempotencia] = _EM_ANDAMENTO

    try:
        resultado = await _executar_transferencia(dados, estado)
    except Exception:
        # Falhou: libera a chave para que o cliente possa tentar de novo.
        if chave_idempotencia:
            estado.idempotencia.pop(chave_idempotencia, None)
        raise

    if chave_idempotencia:
        estado.idempotencia[chave_idempotencia] = resultado
    return resultado


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

        # O debito vem ANTES de qualquer await: entre a checagem de saldo e o
        # debito nao pode haver ponto de suspensao, senao outra requisicao (ou o
        # consumidor de mensagens) poderia intercalar e gastar o mesmo saldo.
        conta_origem.saldo -= dados.valor
        ts_debito = await estado.relogio.evento_local()
        estado.registro.registrar(
            "TRANSFERENCIA_DEBITO",
            ts_debito,
            {"idOrigem": dados.idOrigem, "idDestino": dados.idDestino, "valor": dados.valor},
        )

        conta_destino.saldo += dados.valor
        ts_credito = await estado.relogio.evento_local()
        estado.registro.registrar(
            "TRANSFERENCIA_CREDITO",
            ts_credito,
            {"idOrigem": dados.idOrigem, "idDestino": dados.idDestino, "valor": dados.valor},
        )
        return {
            "mensagem": "Transferencia concluida (mesma agencia).",
            "escopo": "local",
            "saldoOrigem": conta_origem.saldo,
            "timestampVetorial": ts_credito,
        }

    # --- Caso 2: entre agencias -------------------------------------------
    # O debito e sempre local, pois esta agencia e a dona da conta de origem.
    conta_origem.saldo -= dados.valor
    ts_debito = await estado.relogio.evento_local()
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

    # Em vez de chamar a outra agencia (Sprint 1), publicamos um evento no
    # RabbitMQ. Regra 2 do relogio vetorial: incrementa a propria posicao e anexa
    # o vetor inteiro a mensagem.
    id_mensagem = str(uuid.uuid4())
    ts_envio = await estado.relogio.ao_enviar()
    mensagem = {
        "idMensagem": id_mensagem,
        "idOrigem": dados.idOrigem,
        "idConta": dados.idDestino,
        "valor": dados.valor,
        "vetorEnvio": ts_envio,
        "origemAgencia": estado.id_agencia,
    }

    # O envio e registrado antes da publicacao: o evento de envio (regra 2) ja
    # aconteceu no relogio. Se a publicacao falhar, o estorno vem logo depois.
    estado.registro.registrar(
        "TRANSFERENCIA_ENVIADA",
        ts_envio,
        {
            "idMensagem": id_mensagem,
            "idOrigem": dados.idOrigem,
            "idDestino": dados.idDestino,
            "valor": dados.valor,
            "agenciaDestino": agencia_destino,
        },
    )

    try:
        await estado.mensageria.publicar(
            routing_key_credito(agencia_destino), mensagem, id_mensagem
        )
    except Exception as erro:
        # Diferente do Sprint 1, aqui a falha e local e sincrona: o broker recusou
        # ou nao confirmou a publicacao, entao o credito nao vai acontecer e da
        # para estornar o debito na hora. (Caso ambiguo: se a confirmacao so
        # atrasou, a mensagem pode ter chegado ao broker mesmo assim - garantir
        # atomicidade nesse caso e assunto do Sprint 4.)
        conta_origem.saldo += dados.valor
        ts_estorno = await estado.relogio.evento_local()
        estado.registro.registrar(
            "TRANSFERENCIA_ESTORNADA",
            ts_estorno,
            {
                "idMensagem": id_mensagem,
                "idOrigem": dados.idOrigem,
                "idDestino": dados.idDestino,
                "valor": dados.valor,
                "agenciaDestino": agencia_destino,
                "erro": f"{type(erro).__name__}: {erro}",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "erro": "Nao foi possivel publicar a transferencia no RabbitMQ. "
                "O debito foi estornado; tente novamente.",
                "saldoOrigem": conta_origem.saldo,
            },
        )

    # 200 aqui significa "publicada e confirmada pelo broker", NAO "creditada":
    # o credito acontece depois, quando a agencia de destino consumir a mensagem.
    return {
        "mensagem": f"Transferencia publicada para a Agencia {agencia_destino}; "
        "o credito sera aplicado de forma assincrona.",
        "escopo": "entre-agencias",
        "agenciaDestino": agencia_destino,
        "saldoOrigem": conta_origem.saldo,
        "timestampVetorial": ts_envio,
        "idMensagem": id_mensagem,
    }


async def processar_credito_remoto(corpo: dict, estado) -> None:
    """Consumidor: aplica um credito publicado por outra agencia.

    Faz o papel que no Sprint 1 era da rota creditar-remoto, mas e chamado pelo
    consumidor do RabbitMQ (services/mensageria.py), nao pelo Express/FastAPI -
    por isso nao passa por nenhuma verificacao de JWT.

    Regra 3 do relogio vetorial: o vetor local vira o maximo posicao a posicao
    entre ele e o vetor recebido, e depois a propria posicao e incrementada.
    """
    try:
        mensagem = MensagemCredito.model_validate(corpo)
    except ValidationError as erro:
        # Mensagem malformada: nao ha vetor confiavel para sincronizar o relogio.
        print(f"[Mensageria] mensagem de credito invalida descartada: {erro}", flush=True)
        return

    ts = await estado.relogio.ao_receber(mensagem.vetorEnvio)

    detalhes = {
        "idMensagem": mensagem.idMensagem,
        "idOrigem": mensagem.idOrigem,
        "idConta": mensagem.idConta,
        "valor": mensagem.valor,
        "origemAgencia": mensagem.origemAgencia,
        "vetorRecebido": mensagem.vetorEnvio,
    }

    conta = estado.contas.get(mensagem.idConta)
    if conta is None:
        # A mensagem chegou, mas a conta nao existe (ex.: a agencia reiniciou e
        # perdeu as contas, que vivem so em memoria). A mensageria nao perdeu
        # nada - quem falhou foi o estado da agencia.
        estado.registro.registrar(
            "CREDITO_REMOTO_FALHOU", ts, {**detalhes, "motivo": "conta nao encontrada"}
        )
        return

    conta.saldo += mensagem.valor
    estado.registro.registrar(
        "TRANSFERENCIA_CREDITO_REMOTO", ts, {**detalhes, "novoSaldo": conta.saldo}
    )
