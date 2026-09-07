// Camada MODEL - guarda o token do login. E o unico ponto do app que toca
// no localStorage, o que mantem a "memoria" da sessao em um lugar so.

const CHAVE_TOKEN = 'iceibank.token'
const CHAVE_USUARIO = 'iceibank.usuario'

export const sessao = {
  salvar(token: string, usuario: string) {
    try {
      localStorage.setItem(CHAVE_TOKEN, token)
      localStorage.setItem(CHAVE_USUARIO, usuario)
    } catch {
      /* modo privado do navegador pode bloquear: a sessao vira apenas de memoria */
    }
  },
  token(): string | null {
    try {
      return localStorage.getItem(CHAVE_TOKEN)
    } catch {
      return null
    }
  },
  usuario(): string | null {
    try {
      return localStorage.getItem(CHAVE_USUARIO)
    } catch {
      return null
    }
  },
  limpar() {
    try {
      localStorage.removeItem(CHAVE_TOKEN)
      localStorage.removeItem(CHAVE_USUARIO)
    } catch {
      /* ignorado */
    }
  },
}
