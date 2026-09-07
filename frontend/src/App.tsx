// Amarracao das tres camadas: escolhe a VIEW conforme o estado da sessao e
// injeta nela as acoes vindas dos CONTROLLERS.

import { useState } from 'react'
import { useBanco } from './controller/useBanco'
import { useSessao } from './controller/useSessao'
import { LoginView } from './view/LoginView'
import { PainelView } from './view/PainelView'

export default function App() {
  const [agencia, setAgencia] = useState(0)
  const { usuario, autenticado, avisoExpiracao, entrar, sair, tratarFalha } = useSessao()
  const banco = useBanco(agencia, tratarFalha)

  if (!autenticado || usuario === null) {
    return (
      <LoginView
        agencia={agencia}
        aoTrocarAgencia={setAgencia}
        aoEntrar={entrar}
        aviso={avisoExpiracao}
      />
    )
  }

  return (
    <PainelView
      usuario={usuario}
      agencia={agencia}
      aoTrocarAgencia={setAgencia}
      aoSair={sair}
      conta={banco.conta}
      feedback={banco.feedback}
      carregando={banco.carregando}
      consultar={banco.consultar}
      criarConta={banco.criarConta}
      depositar={banco.depositar}
      sacar={banco.sacar}
      transferir={banco.transferir}
    />
  )
}
