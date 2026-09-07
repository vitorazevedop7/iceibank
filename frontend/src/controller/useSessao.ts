// Camada CONTROLLER - orquestra login/logout e reage a expiracao do token.

import { useCallback, useState } from 'react'
import { api } from '../model/api'
import { sessao } from '../model/sessao'
import { ErroApi } from '../model/tipos'

export function useSessao() {
  const [usuario, setUsuario] = useState<string | null>(() => sessao.usuario())
  const [avisoExpiracao, setAvisoExpiracao] = useState<string | null>(null)

  const autenticado = usuario !== null && sessao.token() !== null

  const entrar = useCallback(
    async (agencia: number, nome: string, senha: string) => {
      const resposta = await api.login(agencia, nome, senha)
      sessao.salvar(resposta.access_token, nome)
      setUsuario(nome)
      setAvisoExpiracao(null)
      return resposta.expira_em_segundos
    },
    [],
  )

  const sair = useCallback(() => {
    sessao.limpar()
    setUsuario(null)
  }, [])

  /**
   * Chamado sempre que uma operacao falha. Se a falha foi token expirado ou
   * ausente, a sessao e encerrada e a pessoa volta para a tela de login com um
   * aviso explicito - em vez de ficar vendo um erro generico repetido.
   */
  const tratarFalha = useCallback(
    (erro: unknown) => {
      if (erro instanceof ErroApi && erro.status === 401) {
        sessao.limpar()
        setUsuario(null)
        setAvisoExpiracao(
          erro.expirado
            ? 'Sua sessao expirou durante a operacao. Faca login novamente - a operacao NAO foi concluida.'
            : 'Sua sessao nao e mais valida. Faca login novamente.',
        )
      }
    },
    [],
  )

  return { usuario, autenticado, avisoExpiracao, entrar, sair, tratarFalha }
}
