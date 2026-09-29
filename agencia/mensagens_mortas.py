"""Funcionalidade adicional (Sprint 2) - inspeciona e reprocessa a fila-mortas.

Mensagens de credito que falharam duas vezes (ex.: conta nao encontrada porque a
agencia reiniciou e perdeu as contas em memoria) nao somem: o RabbitMQ as desvia
para a fila-mortas. Este script mostra o que esta la e permite devolver as
mensagens para a fila de origem depois que o problema foi resolvido (ex.: a conta
foi recriada).

Uso:
    python mensagens_mortas.py                # lista, sem remover nada
    python mensagens_mortas.py --reprocessar  # republica cada uma na routing key
                                              # original e a remove da fila-mortas
"""

import asyncio
import json
import sys

import aio_pika

from src import config
from src.services.mensageria import EXCHANGE, FILA_MORTAS


def origem_da_morte(mensagem: aio_pika.abc.AbstractIncomingMessage) -> tuple[str, str, str]:
    """(fila de origem, routing key original, motivo) a partir do cabecalho x-death."""
    mortes = (mensagem.headers or {}).get("x-death") or [{}]
    primeira = mortes[0]
    chaves = primeira.get("routing-keys") or [""]
    return (
        str(primeira.get("queue", "?")),
        str(chaves[0]),
        str(primeira.get("reason", "?")),
    )


async def main() -> None:
    reprocessar = "--reprocessar" in sys.argv[1:]
    if not config.RABBITMQ_URL:
        print("Defina RABBITMQ_URL (agencia/.env) antes de rodar.")
        return

    conexao = await aio_pika.connect(config.RABBITMQ_URL)
    async with conexao:
        canal = await conexao.channel(publisher_confirms=True)
        fila = await canal.get_queue(FILA_MORTAS)
        exchange = await canal.get_exchange(EXCHANGE)

        mensagens = []
        while (mensagem := await fila.get(no_ack=False, fail=False)) is not None:
            mensagens.append(mensagem)

        print(f"=== {FILA_MORTAS}: {len(mensagens)} mensagem(ns) ===")
        for mensagem in mensagens:
            corpo = json.loads(mensagem.body)
            fila_origem, routing_key, motivo = origem_da_morte(mensagem)
            print(
                f"  idMensagem={corpo.get('idMensagem')}  conta={corpo.get('idConta')}  "
                f"valor={corpo.get('valor')}  origem=Agencia {corpo.get('origemAgencia')}  "
                f"vetorEnvio={corpo.get('vetorEnvio')}"
            )
            print(f"      veio de {fila_origem} (routing key {routing_key}), motivo: {motivo}")

            if reprocessar:
                await exchange.publish(
                    aio_pika.Message(
                        body=mensagem.body,
                        content_type="application/json",
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        message_id=mensagem.message_id,
                    ),
                    routing_key=routing_key,
                    mandatory=True,
                )
                await mensagem.ack()
                print(f"      -> republicada em {EXCHANGE} com routing key {routing_key}")

        # Sem --reprocessar nada e confirmado: ao fechar o canal, o RabbitMQ devolve
        # todas as mensagens lidas para a fila-mortas.


if __name__ == "__main__":
    asyncio.run(main())
