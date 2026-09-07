// Camada CONTROLLER - traduz acoes da interface em chamadas do Model e
// concentra o estado de carregamento, mensagem de sucesso e mensagem de erro.

import { useCallback, useState } from 'react'
import { agenciaResponsavel, api } from '../model/api'
import type { Conta } from '../model/tipos'

export type Feedback = { tipo: 'sucesso' | 'erro' | 'aviso'; texto: string } | null

export function useBanco(agencia: number, aoFalhar: (erro: unknown) => void) {
  const [conta, setConta] = useState<Conta | null>(null)
  const [feedback, setFeedback] = useState<Feedback>(null)
  const [carregando, setCarregando] = useState(false)

  const executar = useCallback(
    async <T,>(acao: () => Promise<T>, aoConcluir: (r: T) => Feedback) => {
      setCarregando(true)
      setFeedback(null)
      try {
        const resultado = await acao()
        setFeedback(aoConcluir(resultado))
        return resultado
      } catch (erro) {
        aoFalhar(erro)
        setFeedback({
          tipo: 'erro',
          texto: erro instanceof Error ? erro.message : 'Erro inesperado.',
        })
        return null
      } finally {
        setCarregando(false)
      }
    },
    [aoFalhar],
  )

  const consultar = useCallback(
    (id: number) =>
      executar(
        () => api.consultarSaldo(agencia, id),
        (c) => {
          setConta(c)
          return { tipo: 'sucesso', texto: `Conta ${c.id} - saldo atual: R$ ${c.saldo.toFixed(2)}` }
        },
      ),
    [agencia, executar],
  )

  const criarConta = useCallback(
    (id: number, nome: string, saldoInicial: number) =>
      executar(
        () => api.criarConta(agencia, id, nome, saldoInicial),
        (c) => {
          setConta(c)
          return { tipo: 'sucesso', texto: `Conta ${c.id} criada na Agencia ${agencia}.` }
        },
      ),
    [agencia, executar],
  )

  const depositar = useCallback(
    (id: number, valor: number) =>
      executar(
        () => api.depositar(agencia, id, valor),
        (c) => {
          setConta(c)
          return { tipo: 'sucesso', texto: `Deposito de R$ ${valor.toFixed(2)}. Novo saldo: R$ ${c.saldo.toFixed(2)}` }
        },
      ),
    [agencia, executar],
  )

  const sacar = useCallback(
    (id: number, valor: number) =>
      executar(
        () => api.sacar(agencia, id, valor),
        (c) => {
          setConta(c)
          return { tipo: 'sucesso', texto: `Saque de R$ ${valor.toFixed(2)}. Novo saldo: R$ ${c.saldo.toFixed(2)}` }
        },
      ),
    [agencia, executar],
  )

  const transferir = useCallback(
    (idOrigem: number, idDestino: number, valor: number, chave?: string) =>
      executar(
        () => api.transferir(agencia, idOrigem, idDestino, valor, chave || undefined),
        (r) => {
          // Mantem o cartao de saldo coerente com o que o backend acabou de aplicar.
          setConta((atual) =>
            atual && atual.id === idOrigem ? { ...atual, saldo: r.saldoOrigem } : atual,
          )
          if (r.repetida) {
            return {
              tipo: 'aviso',
              texto:
                `Transferencia ja aplicada anteriormente com esta Idempotency-Key. ` +
                `Nada foi debitado de novo. Saldo da origem: R$ ${r.saldoOrigem.toFixed(2)}`,
            }
          }
          const onde =
            r.escopo === 'local'
              ? 'dentro da mesma agencia'
              : `entre agencias (destino: Agencia ${r.agenciaDestino})`
          return {
            tipo: 'sucesso',
            texto:
              `Transferencia de R$ ${valor.toFixed(2)} concluida ${onde}. ` +
              `Saldo da origem: R$ ${r.saldoOrigem.toFixed(2)} | Lamport ${r.timestampLamport}`,
          }
        },
      ),
    [agencia, executar],
  )

  return {
    conta,
    feedback,
    carregando,
    setFeedback,
    consultar,
    criarConta,
    depositar,
    sacar,
    transferir,
    agenciaResponsavel,
  }
}
