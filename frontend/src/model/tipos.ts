// Camada MODEL - formatos de dados trocados com a API das agencias.

export interface Conta {
  id: number
  nomeAluno: string
  saldo: number
}

export interface RespostaLogin {
  access_token: string
  token_type: string
  expira_em_segundos: number
}

export interface ResultadoTransferencia {
  mensagem: string
  escopo: 'local' | 'entre-agencias'
  agenciaDestino?: number
  saldoOrigem: number
  timestampLamport: number
  repetida?: boolean
}

export interface StatusAgencia {
  agencia: number
  relogioLamport: number
  quantidadeContas: number
  contas: number[]
}

/** Erro de API ja traduzido para uma mensagem exibivel na tela. */
export class ErroApi extends Error {
  constructor(
    public readonly status: number,
    mensagem: string,
    public readonly expirado = false,
  ) {
    super(mensagem)
  }
}
