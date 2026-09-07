// Camada VIEW - painel de operacoes (saldo, deposito, saque, transferencia).

import { useState } from 'react'
import { AGENCIAS, agenciaResponsavel } from '../model/api'
import type { Feedback } from '../controller/useBanco'
import type { Conta } from '../model/tipos'

interface Props {
  usuario: string
  agencia: number
  aoTrocarAgencia: (id: number) => void
  aoSair: () => void
  conta: Conta | null
  feedback: Feedback
  carregando: boolean
  consultar: (id: number) => void
  criarConta: (id: number, nome: string, saldo: number) => void
  depositar: (id: number, valor: number) => void
  sacar: (id: number, valor: number) => void
  transferir: (origem: number, destino: number, valor: number, chave?: string) => void
}

export function PainelView(p: Props) {
  const [idConta, setIdConta] = useState('0')
  const [nomeNovaConta, setNomeNovaConta] = useState('')
  const [saldoInicial, setSaldoInicial] = useState('100')
  const [valor, setValor] = useState('50')
  const [idDestino, setIdDestino] = useState('1')
  const [valorTransf, setValorTransf] = useState('30')
  const [chave, setChave] = useState('')

  const num = (s: string) => Number(s)
  const donaDaConta = idConta === '' ? null : agenciaResponsavel(num(idConta))
  const donaDoDestino = idDestino === '' ? null : agenciaResponsavel(num(idDestino))

  return (
    <div className="painel">
      <header className="barra">
        <div>
          <strong>ICEIBank</strong>
          <span className="chip">Agencia {p.agencia}</span>
        </div>
        <div>
          <label className="inline">
            Porta de entrada:
            <select value={p.agencia} onChange={(e) => p.aoTrocarAgencia(Number(e.target.value))}>
              {AGENCIAS.map((a) => (
                <option key={a.id} value={a.id}>
                  Agencia {a.id}
                </option>
              ))}
            </select>
          </label>
          <span className="usuario">{p.usuario}</span>
          <button className="secundario" onClick={p.aoSair}>
            Sair
          </button>
        </div>
      </header>

      {p.feedback && (
        <div className={`alerta alerta-${p.feedback.tipo}`}>{p.feedback.texto}</div>
      )}

      {p.conta && (
        <div className="cartao destaque">
          <span className="rotulo">Conta {p.conta.id} &middot; {p.conta.nomeAluno}</span>
          <span className="saldo">R$ {p.conta.saldo.toFixed(2)}</span>
        </div>
      )}

      <div className="grade">
        <section className="cartao">
          <h2>Conta</h2>
          <label>
            Numero da conta
            <input value={idConta} onChange={(e) => setIdConta(e.target.value)} inputMode="numeric" />
          </label>
          {donaDaConta !== null && !Number.isNaN(donaDaConta) && (
            <p className={`nota ${donaDaConta !== p.agencia ? 'nota-alerta' : ''}`}>
              Pela particao (id % 3), a conta {idConta} pertence a <b>Agencia {donaDaConta}</b>
              {donaDaConta !== p.agencia && ' - troque a porta de entrada para opera-la.'}
            </p>
          )}
          <button disabled={p.carregando} onClick={() => p.consultar(num(idConta))}>
            Consultar saldo
          </button>

          <hr />
          <h3>Criar conta</h3>
          <label>
            Nome do titular
            <input value={nomeNovaConta} onChange={(e) => setNomeNovaConta(e.target.value)} />
          </label>
          <label>
            Saldo inicial
            <input value={saldoInicial} onChange={(e) => setSaldoInicial(e.target.value)} inputMode="decimal" />
          </label>
          <button
            className="secundario"
            disabled={p.carregando}
            onClick={() => p.criarConta(num(idConta), nomeNovaConta, num(saldoInicial))}
          >
            Criar conta {idConta}
          </button>
        </section>

        <section className="cartao">
          <h2>Deposito e saque</h2>
          <label>
            Valor
            <input value={valor} onChange={(e) => setValor(e.target.value)} inputMode="decimal" />
          </label>
          <div className="linha">
            <button disabled={p.carregando} onClick={() => p.depositar(num(idConta), num(valor))}>
              Depositar
            </button>
            <button
              className="secundario"
              disabled={p.carregando}
              onClick={() => p.sacar(num(idConta), num(valor))}
            >
              Sacar
            </button>
          </div>
          <p className="nota">Opera sobre a conta informada no cartao ao lado.</p>
        </section>

        <section className="cartao">
          <h2>Transferencia</h2>
          <p className="nota">
            A tela nao decide se e local ou entre agencias: ela envia o pedido para a agencia de
            origem e o backend resolve. O resultado abaixo diz o que aconteceu.
          </p>
          <label>
            Conta de destino
            <input value={idDestino} onChange={(e) => setIdDestino(e.target.value)} inputMode="numeric" />
          </label>
          {donaDoDestino !== null && !Number.isNaN(donaDoDestino) && (
            <p className="nota">
              Destino pertence a <b>Agencia {donaDoDestino}</b> &rarr;{' '}
              {donaDoDestino === p.agencia ? 'transferencia local' : 'transferencia entre agencias'}
            </p>
          )}
          <label>
            Valor
            <input value={valorTransf} onChange={(e) => setValorTransf(e.target.value)} inputMode="decimal" />
          </label>
          <label>
            Idempotency-Key (opcional)
            <input
              value={chave}
              onChange={(e) => setChave(e.target.value)}
              placeholder="ex.: transf-001"
            />
          </label>
          <p className="nota">
            Com uma chave preenchida, reenviar a mesma transferencia nao debita de novo.
          </p>
          <button
            disabled={p.carregando}
            onClick={() => p.transferir(num(idConta), num(idDestino), num(valorTransf), chave)}
          >
            Transferir
          </button>
        </section>
      </div>
    </div>
  )
}
