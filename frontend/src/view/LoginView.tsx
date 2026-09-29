// Camada VIEW - tela de login.

import { useState, type FormEvent } from 'react'
import { AGENCIAS } from '../model/api'

interface Props {
  agencia: number
  aoTrocarAgencia: (id: number) => void
  aoEntrar: (agencia: number, usuario: string, senha: string) => Promise<number>
  aviso: string | null
}

export function LoginView({ agencia, aoTrocarAgencia, aoEntrar, aviso }: Props) {
  const [usuario, setUsuario] = useState('ana')
  const [senha, setSenha] = useState('senha123')
  const [erro, setErro] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(false)

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    setErro(null)
    setCarregando(true)
    try {
      await aoEntrar(agencia, usuario, senha)
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Falha no login.')
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div className="cartao cartao-login">
      <h1>ICEIBank</h1>
      <p className="subtitulo">Sprint 2 &middot; API REST/MVC com relogio vetorial</p>

      {aviso && <div className="alerta alerta-aviso">{aviso}</div>}

      <form onSubmit={enviar}>
        <label>
          Agencia de acesso
          <select value={agencia} onChange={(e) => aoTrocarAgencia(Number(e.target.value))}>
            {AGENCIAS.map((a) => (
              <option key={a.id} value={a.id}>
                Agencia {a.id} &mdash; {a.url}
              </option>
            ))}
          </select>
        </label>

        <label>
          Usuario
          <input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="username" />
        </label>

        <label>
          Senha
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            autoComplete="current-password"
          />
        </label>

        {erro && <div className="alerta alerta-erro">{erro}</div>}

        <button type="submit" disabled={carregando}>
          {carregando ? 'Entrando...' : 'Entrar'}
        </button>
      </form>

      <p className="dica">
        Usuarios de teste: <code>ana</code> (contas 0 e 3), <code>bruno</code> (contas 1 e 4),{' '}
        <code>carla</code> (contas 2 e 5). Senha: <code>senha123</code>
      </p>
    </div>
  )
}
