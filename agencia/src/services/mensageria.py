"""Parte C (Sprint 2) - comunicacao indireta entre agencias via RabbitMQ.

Substitui a chamada REST direta do Sprint 1. Uma agencia nao chama mais a outra:
ela publica um evento numa exchange, e a agencia de destino o consome quando
puder - inclusive depois de voltar de uma queda, porque fila e mensagem sao
duraveis.

Topologia (Publish/Subscribe com exchange do tipo topic):

    exchange  iceibank.eventos (topic, duravel)
      ├── agencia.0.creditar ──> fila-agencia-0 (duravel) ─┐
      ├── agencia.1.creditar ──> fila-agencia-1 (duravel) ─┤ rejeitadas
      └── agencia.2.creditar ──> fila-agencia-2 (duravel) ─┘ (dead-letter)
                                                            │
    exchange  iceibank.mortas (fanout, duravel) <───────────┘
      └──> fila-mortas (duravel)

Funcionalidade adicional do sprint (dead-letter queue): uma mensagem que falha ao
ser processada ganha UMA nova tentativa; se falhar de novo, o consumidor a
rejeita sem reenfileirar e o proprio RabbitMQ a move para `fila-mortas` (argumento
x-dead-letter-exchange das filas das agencias), em vez de ela simplesmente
sumir. De la ela pode ser inspecionada e reprocessada (ver mensagens_mortas.py).

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
from aio_pika.exceptions import ChannelPreconditionFailed

EXCHANGE = "iceibank.eventos"
EXCHANGE_MORTAS = "iceibank.mortas"
FILA_MORTAS = "fila-mortas"

# Argumento que liga cada fila de agencia a exchange de mensagens mortas: o que
# for rejeitado sem reenfileirar e desviado pelo broker para la.
ARGUMENTOS_FILA_AGENCIA = {"x-dead-letter-exchange": EXCHANGE_MORTAS}

# Tempo maximo esperando o broker confirmar (publisher confirm) uma publicacao.
TEMPO_LIMITE_PUBLICACAO_SEGUNDOS = 5

log = logging.getLogger("iceibank.mensageria")

# O tratador recebe o corpo da mensagem e se ela e uma reentrega (segunda tentativa).
TratadorMensagem = Callable[[dict, bool], Awaitable[None]]


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
        await self._declarar_topologia()
        # publisher_confirms: o publish so retorna depois que o broker confirma que
        # recebeu (e, com mensagem persistente e fila duravel, gravou) a mensagem.
        # on_return_raises: mensagem sem fila vinculada vira excecao, nao silencio.
        self._canal = await self._conexao.channel(
            publisher_confirms=True, on_return_raises=True
        )
        # Uma mensagem por vez: o proximo credito so e entregue depois do ack do anterior.
        await self._canal.set_qos(prefetch_count=1)
        self._exchange = await self._canal.declare_exchange(
            EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )

    async def _declarar_topologia(self) -> None:
        """Declara as exchanges, as filas de TODAS as agencias, a fila-mortas e os bindings.

        Cada agencia declara a topologia inteira, nao so a propria fila. Se so a
        dona declarasse a fila, uma agencia que nunca subiu naquele broker nao
        teria fila, e uma mensagem com a routing key dela seria descartada pelo
        RabbitMQ. As declaracoes sao idempotentes: repetir nao muda nada.
        """
        assert self._conexao is not None
        canal = await self._conexao.channel()
        mortas = await canal.declare_exchange(
            EXCHANGE_MORTAS, aio_pika.ExchangeType.FANOUT, durable=True
        )
        fila_mortas = await canal.declare_queue(FILA_MORTAS, durable=True)
        await fila_mortas.bind(mortas)
        await canal.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
        await canal.close()

        for id_agencia in range(self._numero_agencias):
            await self._declarar_fila_agencia(id_agencia)

    async def _declarar_fila_agencia(self, id_agencia: int) -> None:
        assert self._conexao is not None
        nome = nome_fila(id_agencia)
        canal = await self._conexao.channel()
        try:
            fila = await canal.declare_queue(
                nome, durable=True, arguments=ARGUMENTOS_FILA_AGENCIA
            )
        except ChannelPreconditionFailed:
            # A fila ja existia sem o argumento de dead-letter (criada antes desta
            # funcionalidade) e o RabbitMQ nao deixa mudar argumentos de uma fila
            # existente. Recria - mas so se estiver vazia, para nao perder credito.
            canal = await self._conexao.channel()
            await canal.queue_delete(nome, if_empty=True)
            fila = await canal.declare_queue(
                nome, durable=True, arguments=ARGUMENTOS_FILA_AGENCIA
            )
            print(f"[Mensageria] {nome} recriada com dead-letter para {FILA_MORTAS}", flush=True)
        exchange = await canal.get_exchange(EXCHANGE)
        await fila.bind(exchange, routing_key=routing_key_credito(id_agencia))
        await canal.close()

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

        - tratador terminou sem erro           -> ack (mensagem removida da fila)
        - falhou na primeira entrega            -> reenfileira para uma nova tentativa
        - falhou de novo (mensagem reentregue)  -> rejeita sem reenfileirar; o broker
                                                   a desvia para a fila-mortas
        """
        assert self._canal is not None
        fila = await self._canal.get_queue(nome_fila(id_agencia))

        async def ao_chegar(mensagem: AbstractIncomingMessage) -> None:
            reentrega = bool(mensagem.redelivered)
            try:
                corpo = json.loads(mensagem.body)
                await tratador(corpo, reentrega)
            except Exception as erro:
                if reentrega:
                    await mensagem.reject(requeue=False)
                    destino = f"enviada para a {FILA_MORTAS}"
                else:
                    await mensagem.reject(requeue=True)
                    destino = "reenfileirada para nova tentativa"
                print(
                    f"[Mensageria] mensagem {mensagem.message_id} falhou "
                    f"({type(erro).__name__}: {erro}); {destino}",
                    flush=True,
                )
                return
            await mensagem.ack()

        await fila.consume(ao_chegar)

    async def fechar(self) -> None:
        if self._conexao is not None:
            await self._conexao.close()
