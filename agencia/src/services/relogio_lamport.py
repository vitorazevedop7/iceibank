"""Parte B - relogio logico de Lamport.

As tres regras do algoritmo (Lamport, 1978):

1. Antes de qualquer evento local, o processo incrementa seu contador.
2. Ao enviar uma mensagem, o processo incrementa o contador e anexa o valor a mensagem.
3. Ao receber uma mensagem com timestamp t, o processo ajusta seu contador para
   max(contador_local, t) + 1.

Isso garante que, se A aconteceu-antes de B causalmente, entao ts(A) < ts(B).
A volta nao vale: timestamps ordenados nao provam relacao causal.
"""

import asyncio


class RelogioLamport:
    """Contador logico da agencia, protegido contra acesso concorrente.

    O lock existe porque o contador e estado compartilhado entre requisicoes. Mesmo
    com o uvicorn em um unico worker, um handler assincrono pode ceder o controle em
    um `await` (por exemplo, na chamada HTTP para outra agencia no meio de uma
    transferencia) e permitir que outra requisicao intercale sua leitura e escrita do
    contador - a mesma condicao de corrida vista no laboratorio de Threads e Semaforos.
    """

    def __init__(self) -> None:
        self.contador = 0
        self._lock = asyncio.Lock()

    async def evento_local(self) -> int:
        """Regra 1: incrementa antes de registrar um evento interno da agencia."""
        async with self._lock:
            self.contador += 1
            return self.contador

    async def ao_enviar(self) -> int:
        """Regra 2: incrementa e devolve o valor que sera anexado a mensagem."""
        async with self._lock:
            self.contador += 1
            return self.contador

    async def ao_receber(self, timestamp_recebido: int) -> int:
        """Regra 3: sincroniza com o remetente sem nunca retroceder o relogio."""
        async with self._lock:
            self.contador = max(self.contador, timestamp_recebido) + 1
            return self.contador

    async def valor_atual(self) -> int:
        """Leitura do contador sem gerar evento (usada pela rota de status)."""
        async with self._lock:
            return self.contador
