// Camada MODEL - cliente HTTP das agencias.
//
// Todo acesso a rede passa por `requisicao()`, que faz tres coisas em um lugar so:
//   1. anexa o cabecalho Authorization com o token guardado na sessao;
//   2. traduz o corpo de erro da API em uma mensagem exibivel (ErroApi);
//   3. marca especificamente o caso 401 por token expirado, para a interface
//      poder avisar a pessoa em vez de mostrar um erro generico.

import { sessao } from './sessao'
import {
  ErroApi,
  type Conta,
  type RespostaLogin,
  type ResultadoTransferencia,
  type StatusAgencia,
} from './tipos'

/** As 3 agencias. A porta base acompanha o OFFSET definido no backend. */
export const AGENCIAS = [
  { id: 0, url: 'http://localhost:4000' },
  { id: 1, url: 'http://localhost:4001' },
  { id: 2, url: 'http://localhost:4002' },
]

export function urlDaAgencia(id: number): string {
  return AGENCIAS.find((a) => a.id === id)?.url ?? AGENCIAS[0].url
}

/** Mesma regra de particao do backend, usada apenas para orientar quem usa a tela. */
export function agenciaResponsavel(idConta: number): number {
  return idConta % AGENCIAS.length
}

async function requisicao<T>(
  agencia: number,
  caminho: string,
  opcoes: { metodo?: string; corpo?: unknown; cabecalhos?: Record<string, string> } = {},
): Promise<T> {
  const { metodo = 'GET', corpo, cabecalhos = {} } = opcoes
  const token = sessao.token()

  let resposta: Response
  try {
    resposta = await fetch(`${urlDaAgencia(agencia)}${caminho}`, {
      method: metodo,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...cabecalhos,
      },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    })
  } catch {
    throw new ErroApi(
      0,
      `Nao foi possivel falar com a Agencia ${agencia} (${urlDaAgencia(agencia)}). ` +
        'Ela esta no ar?',
    )
  }

  const texto = await resposta.text()
  const dados = texto ? JSON.parse(texto) : {}

  if (!resposta.ok) {
    const mensagem: string =
      dados?.detail?.erro ??
      dados?.erro ??
      (typeof dados?.detail === 'string' ? dados.detail : null) ??
      `Erro ${resposta.status} na Agencia ${agencia}.`
    const expirado = resposta.status === 401 && /expirado/i.test(mensagem)
    throw new ErroApi(resposta.status, mensagem, expirado)
  }

  return dados as T
}

export const api = {
  login: (agencia: number, usuario: string, senha: string) =>
    requisicao<RespostaLogin>(agencia, '/auth/login', {
      metodo: 'POST',
      corpo: { usuario, senha },
    }),

  status: (agencia: number) => requisicao<StatusAgencia>(agencia, '/status'),

  criarConta: (agencia: number, id: number, nomeAluno: string, saldoInicial: number) =>
    requisicao<Conta>(agencia, '/contas', {
      metodo: 'POST',
      corpo: { id, nomeAluno, saldoInicial },
    }),

  consultarSaldo: (agencia: number, id: number) =>
    requisicao<Conta>(agencia, `/contas/${id}`),

  depositar: (agencia: number, id: number, valor: number) =>
    requisicao<Conta>(agencia, `/contas/${id}/depositar`, {
      metodo: 'POST',
      corpo: { valor },
    }),

  sacar: (agencia: number, id: number, valor: number) =>
    requisicao<Conta>(agencia, `/contas/${id}/sacar`, { metodo: 'POST', corpo: { valor } }),

  transferir: (
    agencia: number,
    idOrigem: number,
    idDestino: number,
    valor: number,
    chaveIdempotencia?: string,
  ) =>
    requisicao<ResultadoTransferencia>(agencia, '/transferencias', {
      metodo: 'POST',
      corpo: { idOrigem, idDestino, valor },
      cabecalhos: chaveIdempotencia ? { 'Idempotency-Key': chaveIdempotencia } : {},
    }),
}
