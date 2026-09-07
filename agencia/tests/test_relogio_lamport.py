"""Parte B - teste isolado do relogio de Lamport, antes de plugar na API.

Executar com:  python -m pytest tests/ -v
"""

import asyncio

from src.services import RelogioLamport


def test_evento_local_incrementa_de_um_em_um():
    relogio = RelogioLamport()
    assert asyncio.run(relogio.evento_local()) == 1
    assert asyncio.run(relogio.evento_local()) == 2
    assert asyncio.run(relogio.evento_local()) == 3


def test_ao_enviar_tambem_incrementa():
    relogio = RelogioLamport()
    asyncio.run(relogio.evento_local())
    assert asyncio.run(relogio.ao_enviar()) == 2


def test_ao_receber_timestamp_maior_salta_para_o_recebido():
    relogio = RelogioLamport()
    asyncio.run(relogio.evento_local())          # contador = 1
    assert asyncio.run(relogio.ao_receber(8)) == 9   # max(1, 8) + 1


def test_ao_receber_timestamp_menor_nao_retrocede():
    """Pergunta 2 da secao 6.4: contador 10 recebendo timestamp 3 vira 11."""
    relogio = RelogioLamport()
    for _ in range(10):
        asyncio.run(relogio.evento_local())
    assert relogio.contador == 10
    assert asyncio.run(relogio.ao_receber(3)) == 11


def test_ao_receber_timestamp_igual_ainda_incrementa():
    """A desigualdade precisa ser estrita: envio e recebimento nunca empatam."""
    relogio = RelogioLamport()
    for _ in range(5):
        asyncio.run(relogio.evento_local())
    assert asyncio.run(relogio.ao_receber(5)) == 6


def test_causalidade_entre_duas_agencias():
    """Se A aconteceu-antes de B, entao ts(A) < ts(B)."""
    agencia_a = RelogioLamport()
    agencia_b = RelogioLamport()

    async def cenario():
        for _ in range(3):
            await agencia_b.evento_local()          # B trabalha sozinha ate 3
        ts_envio = await agencia_a.ao_enviar()       # A envia com ts 1
        ts_recebimento = await agencia_b.ao_receber(ts_envio)
        return ts_envio, ts_recebimento

    ts_envio, ts_recebimento = asyncio.run(cenario())
    assert ts_envio == 1
    assert ts_recebimento == 4          # max(3, 1) + 1
    assert ts_envio < ts_recebimento    # a garantia do algoritmo


def test_incrementos_concorrentes_nao_se_perdem():
    """O lock protege o contador contra intercalacao entre requisicoes."""
    relogio = RelogioLamport()

    async def cenario():
        await asyncio.gather(*(relogio.evento_local() for _ in range(200)))

    asyncio.run(cenario())
    assert relogio.contador == 200
