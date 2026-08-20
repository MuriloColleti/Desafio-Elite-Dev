/**
 * Login.
 *
 * Traz os quatro usuários do seed como atalho. Numa aplicação real isso não
 * existiria, mas aqui o objetivo é o avaliador percorrer três papéis sem
 * decorar e-mail — e o README diz que o seed é a porta de entrada.
 */

import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { inicioDoPapel, useSessao } from '../auth/Sessao'
import { ApiError } from '../lib/api'
import { mensagemDeErro } from '../lib/formato'

const CONTAS_SEED = [
  { email: 'bruno@palco.dev', papel: 'Cliente', icone: '🎟', descricao: 'sem ingresso — compre um' },
  { email: 'ana@palco.dev', papel: 'Cliente', icone: '🎟', descricao: 'já tem 3 ingressos' },
  { email: 'organizador@palco.dev', papel: 'Organizador', icone: '🎬', descricao: 'cria e publica eventos' },
  { email: 'portaria@palco.dev', papel: 'Portaria', icone: '🎫', descricao: 'valida na entrada' },
]

export function Entrar() {
  const { entrar } = useSessao()
  const navegar = useNavigate()
  const local = useLocation()

  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  async function submeter(e: React.FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)

    try {
      const usuario = await entrar(email, senha)
      const de = (local.state as { de?: string } | null)?.de
      navegar(de ?? inicioDoPapel(usuario.role), { replace: true })
    } catch (err) {
      setErro(
        err instanceof ApiError
          ? mensagemDeErro(err.code, err.message)
          : 'Não foi possível entrar.',
      )
    } finally {
      setEnviando(false)
    }
  }

  function preencher(emailSeed: string) {
    setEmail(emailSeed)
    setSenha('senha123')
    setErro(null)
  }

  return (
    <div className="entrar-grade">
      <form className="pilha pilha-16 entrar-form" onSubmit={submeter}>
        <div className="pilha pilha-8">
          <h1>Entrar</h1>
          <p className="texto-2 texto-p" style={{ margin: 0 }}>
            Acesse para reservar ingressos, gerenciar eventos ou validar entradas.
          </p>
        </div>

        {erro && <div className="aviso aviso-erro">{erro}</div>}

        <div className="campo">
          <label htmlFor="email">E-mail</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="campo">
          <label htmlFor="senha">Senha</label>
          <input
            id="senha"
            type="password"
            autoComplete="current-password"
            required
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
        </div>

        <button type="submit" className="btn btn-principal btn-largo" disabled={enviando}>
          {enviando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>

      <aside className="entrar-contas">
        <h3>Contas de demonstração</h3>
        <p className="texto-pp texto-3" style={{ marginTop: 0 }}>
          Senha <code className="mono">senha123</code> para todas. Clique para preencher.
        </p>

        <ul className="pilha pilha-8" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {CONTAS_SEED.map((c) => (
            <li key={c.email}>
              <button type="button" className="conta-seed" onClick={() => preencher(c.email)}>
                <span className="conta-avatar" aria-hidden="true">
                  {c.icone}
                </span>
                <span className="pilha pilha-4" style={{ minWidth: 0 }}>
                  <span className="texto-p forte">{c.papel}</span>
                  <span className="texto-pp texto-3">{c.descricao}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}
