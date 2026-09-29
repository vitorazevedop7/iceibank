"""Parte C (Sprint 2) - comunicacao indireta entre agencias via RabbitMQ.

Substitui a chamada REST direta do Sprint 1. Uma agencia nao chama mais a outra:
ela publica um evento numa exchange, e a agencia de destino o consome quando
puder - inclusive depois de voltar de uma queda, porque fila e mensagem sao
duraveis.

Topologia (Publish/Subscribe com exchange do tipo topic):

    exchange  iceibank.eventos (topic, duravel)
      ├── agencia.0.creditar ──> fila-agencia-0 (duravel)
      ├── agencia.1.creditar ──> fila-agencia-1 (duravel)
      └── agencia.2.creditar ──> fila-agencia-2 (duravel)

Este modulo e so infraestrutura (conectar, declarar, publicar, consumir). A regra
de negocio do credito remoto fica no controller de transferencias.

Por que aio-pika e nao pika: o pika e bloqueante e obrigaria a rodar o consumidor
numa thread separada, com `contas` e o relogio acessados por duas threads ao mesmo
tempo. Com o aio-pika o consumidor roda no MESMO event loop do uvicorn, entao o
modelo de concorrencia do Sprint 1 (um unico loop, lock assincrono no relogio)
continua valendo sem mudancas.
"""

import json
import logging
from collections.abc import Awaitable, Callable

import aio_pika
from aio_pika.abc import (
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractRobustChannel,
    AbstractRobustConnection,
)

EXCHANGE = "iceibank.eventos"

# Tempo maximo esperando o broker confirmar (publisher confirm) uma publicacao.
TEMPO_LIMITE_PUBLICACAO_SEGUNDOS = 5

log = logging.getLogger("iceibank.mensageria")

TratadorMensagem = Callable[[dict], Awaitable[None]]


def routing_key_credito(id_agencia: int) -> str:
    return f"agencia.{id_agencia}.creditar"


def nome_fila(id_agencia: int) -> str:
    return f"fila-agencia-{id_agencia}"


class Mensageria:
    def __init__(self, url: str, numero_agencias: int) -> None:
        self._url = url
        self._numero_agencias = numero_agencias
        self._conexao: AbstractRobustConnection | None = None
        self._canal: AbstractRobustChannel | None = None
        self._exchange: AbstractExchange | None = None

    async def conectar(self) -> None:
        # connect_robust reconecta sozinho se a conexao com o broker cair, e
        # restaura canal, filas e consumidores ao voltar.
        self._conexao = await aio_pika.connect_robust(self._url)
        # publisher_confirms: o publish so retorna depois que o broker confirma que
        # recebeu (e, com mensagem persistente e fila duravel, gravou) a mensagem.
        # on_return_raises: mensagem sem fila vinculada vira excecao, nao silencio.
        self._canal = await self._conexao.channel(
            publisher_confirms=True, on_return_raises=True
        )
        # Uma mensagem por vez: o proximo credito so e entregue depois do ack do anterior.
        await self._canal.set_qos(prefetch_count=1)
        await self._declarar_topologia()

    async def _declarar_topologia(self) -> None:
        """Declara exchange, as filas de TODAS as agencias e os bindings.

        Cada agencia declara a topologia inteira, nao so a propria fila. Se so a
        dona declarasse a fila, uma agencia que nunca subiu naquele broker nao
        teria fila, e uma mensagem com a routing key dela seria descartada pelo
        RabbitMQ. As declaracoes sao idempotentes: repetir nao muda nada.
        """
        assert self._canal is not None
        self._exchange = await self._canal.declare_exchange(
            EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )
        for id_agencia in range(self._numero_agencias):
            fila = await self._canal.declare_queue(nome_fila(id_agencia), durable=True)
            await fila.bind(self._exchange, routing_key=routing_key_credito(id_agencia))

    async def publicar(self, routing_key: str, corpo: dict, id_mensagem: str) -> None:
        """Publica uma mensagem persistente e espera a confirmacao do broker.

        Levanta excecao se o broker recusar, se nao houver fila para a routing key
        ou se a confirmacao nao chegar a tempo.
        """
        if self._exchange is None:
            raise RuntimeError("Mensageria nao conectada.")
        mensagem = aio_pika.Message(
            body=json.dumps(corpo).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=id_mensagem,
        )
        await self._exchange.publish(
            mensagem,
            routing_key=routing_key,
            mandatory=True,
            timeout=TEMPO_LIMITE_PUBLICACAO_SEGUNDOS,
        )

    async def consumir(self, id_agencia: int, tratador: TratadorMensagem) -> None:
        """Assina a fila desta agencia e entrega cada mensagem ao tratador.

        O ack so e enviado depois que o tratador termina sem erro. Se ele levantar
        excecao (ou o corpo nao for JSON), a mensagem e rejeitada sem reenfileirar.
        """
        assert self._canal is not None
        fila = await self._canal.get_queue(nome_fila(id_agencia))

        async def ao_chegar(mensagem: AbstractIncomingMessage) -> None:
            async with mensagem.process(requeue=False):
                try:
                    corpo = json.loads(mensagem.body)
                except json.JSONDecodeError:
                    log.error("Mensagem %s descartada: corpo nao e JSON.", mensagem.message_id)
                    raise
                await tratador(corpo)

        await fila.consume(ao_chegar)

    async def fechar(self) -> None:
        if self._conexao is not None:
            await self._conexao.close()
