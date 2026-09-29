"""Parte B (Sprint 2) - teste isolado do relogio vetorial, antes de plugar na API.

Executar com:  python -m pytest tests/ -v
"""

import asyncio

import pytest

from src.services import RelogioVetorial, comparar_vetores
from src.services.relogio_vetorial import ANTES, CONCORRENTES, DEPOIS, IGUAIS


def rodar(coro):
    return asyncio.run(coro)


# --- As tres regras ---------------------------------------------------------


def test_evento_local_incrementa_so_a_propria_posicao():
    relogio = RelogioVetorial(id_agencia=1, numero_agencias=3)
    assert rodar(relogio.evento_local()) == [0, 1, 0]
    assert rodar(relogio.evento_local()) == [0, 2, 0]


def test_ao_enviar_incrementa_e_devolve_o_vetor_inteiro():
    relogio = RelogioVetorial(id_agencia=0, numero_agencias=3)
    rodar(relogio.evento_local())
    assert rodar(relogio.ao_enviar()) == [2, 0, 0]


def test_ao_receber_faz_maximo_posicao_a_posicao_e_incrementa():
    relogio = RelogioVetorial(id_agencia=2, numero_agencias=3)
    rodar(relogio.evento_local())                      # [0, 0, 1]
    assert rodar(relogio.ao_receber([3, 1, 0])) == [3, 1, 2]


def test_ao_receber_nunca_retrocede_nenhuma_posicao():
    relogio = RelogioVetorial(id_agencia=0, numero_agencias=3)
    for _ in range(5):
        rodar(relogio.evento_local())                  # [5, 0, 0]
    assert rodar(relogio.ao_receber([1, 4, 0])) == [6, 4, 0]


def test_vetor_devolvido_e_uma_copia():
    """O vetor registrado num evento nao pode mudar quando o relogio avanca."""
    relogio = RelogioVetorial(id_agencia=0, numero_agencias=3)
    foto = rodar(relogio.evento_local())
    rodar(relogio.evento_local())
    assert foto == [1, 0, 0]


def test_vetor_recebido_de_tamanho_errado_e_rejeitado():
    relogio = RelogioVetorial(id_agencia=0, numero_agencias=3)
    with pytest.raises(ValueError):
        rodar(relogio.ao_receber([1, 2]))


def test_id_de_agencia_fora_do_vetor_e_rejeitado():
    with pytest.raises(ValueError):
        RelogioVetorial(id_agencia=3, numero_agencias=3)


def test_mesma_sequencia_do_roteiro_secao_9_1():
    """Mesma sequencia usada no roteiro para validar Node, Java e Python."""
    a0 = RelogioVetorial(0, 3)
    a1 = RelogioVetorial(1, 3)
    assert rodar(a0.evento_local()) == [1, 0, 0]
    envio = rodar(a0.ao_enviar())
    assert envio == [2, 0, 0]
    assert rodar(a1.evento_local()) == [0, 1, 0]
    assert rodar(a1.ao_receber(envio)) == [2, 2, 0]


def test_incrementos_concorrentes_nao_se_perdem():
    relogio = RelogioVetorial(id_agencia=1, numero_agencias=3)

    async def cenario():
        await asyncio.gather(*(relogio.evento_local() for _ in range(200)))
        return await relogio.valor_atual()

    assert rodar(cenario()) == [0, 200, 0]


# --- Comparacao de vetores ----------------------------------------------------


def test_pergunta_2_da_secao_6_4_v1_aconteceu_antes():
    """V1 = [3,1,0], V2 = [3,2,0]: V1 <= V2 em todas as posicoes e sao diferentes."""
    assert comparar_vetores([3, 1, 0], [3, 2, 0]) == ANTES
    assert comparar_vetores([3, 2, 0], [3, 1, 0]) == DEPOIS


def test_pergunta_3_da_secao_6_4_concorrentes():
    """V1 = [3,1,0], V2 = [1,3,0]: V1 e maior na posicao 0, V2 na posicao 1."""
    assert comparar_vetores([3, 1, 0], [1, 3, 0]) == CONCORRENTES
    assert comparar_vetores([1, 3, 0], [3, 1, 0]) == CONCORRENTES


def test_vetores_iguais():
    assert comparar_vetores([2, 2, 0], [2, 2, 0]) == IGUAIS


def test_envio_aconteceu_antes_do_recebimento():
    """A garantia que Lamport nao tinha na volta: ANTES <=> relacao causal."""
    a0 = RelogioVetorial(0, 3)
    a1 = RelogioVetorial(1, 3)
    envio = rodar(a0.ao_enviar())
    recebimento = rodar(a1.ao_receber(envio))
    assert comparar_vetores(envio, recebimento) == ANTES


def test_eventos_independentes_em_agencias_diferentes_sao_concorrentes():
    """Criar contas em duas agencias sem troca de mensagem: nenhum influencia o outro."""
    a0 = RelogioVetorial(0, 3)
    a2 = RelogioVetorial(2, 3)
    e0 = rodar(a0.evento_local())    # [1, 0, 0]
    e2 = rodar(a2.evento_local())    # [0, 0, 1]
    assert comparar_vetores(e0, e2) == CONCORRENTES
