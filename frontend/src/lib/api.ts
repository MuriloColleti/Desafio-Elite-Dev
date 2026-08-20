/**
 * Cliente HTTP da API.
 *
 * O back-end responde erro sempre no mesmo formato:
 *   { "error": { "code": "SEAT_TAKEN", "message": "..." } }
 *
 * O `code` é o que a interface usa para decidir o que fazer — nunca o texto.
 * Comparar mensagem quebraria na primeira vez que alguém reescrevesse uma frase.
 */

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

type Opcoes = {
  method?: string
  body?: unknown
}

async function request<T>(caminho: string, { method = 'GET', body }: Opcoes = {}): Promise<T> {
  let resposta: Response

  try {
    resposta = await fetch(`${BASE}${caminho}`, {
      method,
      // A sessão é um cookie httponly: sem isto o navegador não o envia, e
      // toda rota autenticada responderia 401.
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    // Falha de rede não tem `code` do servidor; damos um para a interface
    // poder tratar "API fora do ar" como um caso próprio.
    throw new ApiError('NETWORK_ERROR', 'Não foi possível falar com o servidor.', 0)
  }

  if (resposta.status === 204) return undefined as T

  const texto = await resposta.text()
  const dados = texto ? JSON.parse(texto) : null

  if (!resposta.ok) {
    const erro = dados?.error
    if (erro?.code) throw new ApiError(erro.code, erro.message, resposta.status)

    // 422 do Pydantic não segue o nosso formato: vem como `detail`.
    if (resposta.status === 422 && dados?.detail) {
      const primeiro = Array.isArray(dados.detail) ? dados.detail[0] : dados.detail
      throw new ApiError('VALIDATION_FAILED', primeiro?.msg ?? 'Dados inválidos.', 422)
    }

    throw new ApiError('UNKNOWN', `Erro ${resposta.status}.`, resposta.status)
  }

  return dados as T
}

export const api = {
  get: <T>(caminho: string) => request<T>(caminho),
  post: <T>(caminho: string, body?: unknown) => request<T>(caminho, { method: 'POST', body }),
  patch: <T>(caminho: string, body?: unknown) => request<T>(caminho, { method: 'PATCH', body }),
  delete: <T>(caminho: string) => request<T>(caminho, { method: 'DELETE' }),
}

/** URL absoluta de um recurso da API — para `<img src>` do QR, que não passa pelo fetch. */
export function urlApi(caminho: string): string {
  return `${BASE}${caminho}`
}
