/**
 * Criar conta.
 *
 * O papel é escolhido aqui, entre cliente e organizador. Portaria não aparece
 * de propósito: é conta operacional da casa de espetáculo, e quem pudesse
 * criá-la validaria ingressos de eventos alheios.
 *
 * Cadastrar já abre a sessão — pedir para entrar depois de definir a senha é um
 * passo sem propósito.
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { inicioDoPapel, useSessao } from '../auth/Sessao'
import { ApiError } from '../lib/api'
import { mensagemDeErro } from '../lib/formato'
import type { Papel } from '../lib/tipos'

const PAPEIS: { valor: Extract<Papel, 'CUSTOMER' | 'ORGANIZER'>; icone: string; titulo: string; descricao: string }[] = [
  {
    valor: 'CUSTOMER',
    icone: '🎟',
    titulo: 'Quero comprar',
    descricao: 'Reserve lugar e receba seu ingresso',
  },
  {
    valor: 'ORGANIZER',
    icone: '🎬',
    titulo: 'Quero publicar',
    descricao: 'Crie e gerencie seus eventos',
  },
]

const SENHA_MINIMA = 8

export function CriarConta() {
  const { registrar } = useSessao()
  const navegar = useNavigate()

  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [papel, setPapel] = useState<'CUSTOMER' | 'ORGANIZER'>('CUSTOMER')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const senhaCurta = senha.length > 0 && senha.length < SENHA_MINIMA

  async function submeter(e: React.FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)

    try {
      const usuario = await registrar({ nome, email, senha, papel })
      navegar(inicioDoPapel(usuario.role), { replace: true })
    } catch (err) {
      setErro(
        err instanceof ApiError
          ? mensagemDeErro(err.code, err.message)
          : 'Não foi possível criar a conta.',
      )
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="auth-caixa">
      <form className="pilha pilha-24 entrar-form" onSubmit={submeter}>
        <div className="pilha pilha-8">
          <h1>Criar conta</h1>
          <p className="texto-2 texto-p">Leva menos de um minuto.</p>
        </div>

        {erro && <div className="aviso aviso-erro">{erro}</div>}

        <fieldset className="escolha-papel">
          <legend className="texto-p forte">O que você quer fazer?</legend>
          <div className="escolha-opcoes">
            {PAPEIS.map((p) => (
              <label key={p.valor} className={papel === p.valor ? 'opcao ativa' : 'opcao'}>
                <input
                  type="radio"
                  name="papel"
                  value={p.valor}
                  checked={papel === p.valor}
                  onChange={() => setPapel(p.valor)}
                />
                <span className="opcao-icone" aria-hidden="true">
                  {p.icone}
                </span>
                <span className="pilha pilha-4">
                  <span className="forte texto-p">{p.titulo}</span>
                  <span className="texto-pp texto-3">{p.descricao}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="campo">
          <label htmlFor="nome">Nome</label>
          <input
            id="nome"
            required
            minLength={2}
            autoComplete="name"
            placeholder="Como quer ser chamado"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
          />
        </div>

        <div className="campo">
          <label htmlFor="email">E-mail</label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="campo">
          <label htmlFor="senha">Senha</label>
          <input
            id="senha"
            type="password"
            required
            minLength={SENHA_MINIMA}
            autoComplete="new-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            aria-describedby="dica-senha"
          />
          <span
            id="dica-senha"
            className="campo-dica"
            style={senhaCurta ? { color: 'var(--erro)' } : undefined}
          >
            {/* Só comprimento: regra de composição empurra para senha
                previsível com um "!" no fim. */}
            Ao menos {SENHA_MINIMA} caracteres.
          </span>
        </div>

        <button
          type="submit"
          className="btn btn-principal btn-largo btn-grande"
          disabled={enviando || senhaCurta}
        >
          {enviando ? 'Criando…' : 'Criar conta'}
        </button>

        <p className="centro texto-p texto-2">
          Já tem conta?{' '}
          <Link to="/entrar" className="btn-texto">
            Entrar
          </Link>
        </p>
      </form>
    </div>
  )
}
