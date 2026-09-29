"""Parte B (Sprint 2) - relogio vetorial.

Substitui o relogio de Lamport do Sprint 1. Em vez de um unico contador, cada
agencia mantem um VETOR com um contador por agencia; a posicao `id_agencia` e a
unica que ela incrementa por conta propria.

As tres regras (Fidge, 1988; Mattern, 1989):

1. Antes de um evento local, a agencia incrementa a propria posicao.
2. Ao enviar uma mensagem, incrementa a propria posicao e anexa o vetor inteiro.
3. Ao receber um vetor V, faz vetor[i] = max(vetor[i], V[i]) para todo i e, em
   seguida, incrementa a propria posicao.

Diferente de Lamport, a comparacao de dois vetores diz com certeza se um evento
aconteceu-antes do outro ou se os dois sao concorrentes (ver `comparar_vetores`).
"""

import asyncio

ANTES = "ANTES"
DEPOIS = "DEPOIS"
IGUAIS = "IGUAIS"
CONCORRENTES = "CONCORRENTES"


class RelogioVetorial:
    """Vetor de contadores da agencia, protegido contra acesso concorrente.

    O lock tem o mesmo motivo do Sprint 1: o vetor e estado compartilhado entre
    requisicoes (e, a partir da mensageria, entre requisicoes e o consumidor de
    mensagens), e um handler assincrono pode ceder o controle num `await`.

    Todos os metodos devolvem uma COPIA do vetor. Quem registra o evento ou anexa o
    vetor a uma mensagem precisa de uma foto daquele instante; devolver a lista
    interna faria o valor registrado mudar sozinho nos eventos seguintes.
    """

    def __init__(self, id_agencia: int, numero_agencias: int) -> None:
        if not 0 <= id_agencia < numero_agencias:
            raise ValueError(
                f"id_agencia {id_agencia} fora do intervalo 0..{numero_agencias - 1}"
            )
        self.id_agencia = id_agencia
        self.vetor = [0] * numero_agencias
        self._lock = asyncio.Lock()

    async def evento_local(self) -> list[int]:
        """Regra 1: incrementa a propria posicao antes de um evento interno."""
        async with self._lock:
            self.vetor[self.id_agencia] += 1
            return list(self.vetor)

    async def ao_enviar(self) -> list[int]:
        """Regra 2: incrementa a propria posicao e devolve o vetor a anexar."""
        async with self._lock:
            self.vetor[self.id_agencia] += 1
            return list(self.vetor)

    async def ao_receber(self, vetor_recebido: list[int]) -> list[int]:
        """Regra 3: maximo posicao a posicao, depois incrementa a propria posicao."""
        if len(vetor_recebido) != len(self.vetor):
            raise ValueError(
                f"Vetor recebido tem {len(vetor_recebido)} posicoes; "
                f"esperado {len(self.vetor)}."
            )
        async with self._lock:
            for i, valor in enumerate(vetor_recebido):
                self.vetor[i] = max(self.vetor[i], valor)
            self.vetor[self.id_agencia] += 1
            return list(self.vetor)

    async def valor_atual(self) -> list[int]:
        """Leitura do vetor sem gerar evento (usada pela rota de status)."""
        async with self._lock:
            return list(self.vetor)


def comparar_vetores(v1: list[int], v2: list[int]) -> str:
    """Relacao causal entre os eventos carimbados com v1 e v2.

    - ANTES:        v1 <= v2 em todas as posicoes (e diferentes): v1 aconteceu-antes de v2
    - DEPOIS:       v2 <= v1 em todas as posicoes (e diferentes): v2 aconteceu-antes de v1
    - IGUAIS:       mesmo vetor (o mesmo evento)
    - CONCORRENTES: nenhum dos dois domina o outro; nenhum influenciou o outro
    """
    if len(v1) != len(v2):
        raise ValueError("Vetores de tamanhos diferentes nao sao comparaveis.")
    v1_menor_ou_igual = all(a <= b for a, b in zip(v1, v2))
    v2_menor_ou_igual = all(b <= a for a, b in zip(v1, v2))
    if v1_menor_ou_igual and v2_menor_ou_igual:
        return IGUAIS
    if v1_menor_ou_igual:
        return ANTES
    if v2_menor_ou_igual:
        return DEPOIS
    return CONCORRENTES
