/**
 * Casca da aplicação.
 *
 * Três zonas na barra: marca à esquerda, **busca e local no centro**, ações à
 * direita. A busca no centro porque é a ação principal de quem chega — e o
 * centro é o lugar que o olho encontra primeiro numa barra larga.
 *
 * A busca e o local vivem aqui, e não na vitrine, porque são ações globais:
 * funcionam de qualquer tela e levam de volta à vitrine com o filtro aplicado.
 */

import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate, useSearchParams } from 'react-router-dom'

import { useSessao } from '../auth/Sessao'
import { SeletorLocal } from './SeletorLocal'

/** "Ana Ribeiro" → "AR". */
function iniciais(nome: string): string {
  const p = nome.trim().split(/\s+/)
  return ((p[0]?.[0] ?? '') + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase()
}

export function Layout() {
  const { usuario, sair } = useSessao()
  const navegar = useNavigate()
  const [params] = useSearchParams()

  const [termo, setTermo] = useState(params.get('q') ?? '')

  // Ao navegar, o campo acompanha a URL: senão mostraria uma busca que não
  // está mais aplicada.
  useEffect(() => {
    setTermo(params.get('q') ?? '')
  }, [params])

  const cidade = params.get('cidade')
  const uf = params.get('uf')

  /** Monta a URL da vitrine preservando os filtros que continuam valendo. */
  function urlVitrine(over: { q?: string | null; cidade?: string | null; uf?: string | null }) {
    const qs = new URLSearchParams()
    const q = over.q !== undefined ? over.q : termo.trim()
    const c = over.cidade !== undefined ? over.cidade : cidade
    const u = over.uf !== undefined ? over.uf : uf

    if (q) qs.set('q', q)
    if (c) qs.set('cidade', c)
    if (u) qs.set('uf', u)
    // Gênero e página não são preservados: mudar de cidade ou de termo torna a
    // página 4 e o gênero anterior irrelevantes, e insistir neles mostraria
    // vazio com resultado disponível.

    // Buscar de qualquer tela leva de volta à vitrine com o filtro aplicado.
    return qs.size > 0 ? `/?${qs}` : '/'
  }

  async function encerrar() {
    await sair()
    navegar('/')
  }

  return (
    <>
      <header className="cabecalho">
        <div className="barra">
          <Link to="/" className="logo" aria-label="Palco — início">
            <span className="logo-marca" aria-hidden="true" />
            Palco
          </Link>

          <div className="barra-centro">
            <form
              className="campo-busca"
              role="search"
              onSubmit={(e) => {
                e.preventDefault()
                navegar(urlVitrine({}))
              }}
            >
              <span className="campo-busca-icone" aria-hidden="true">
                ⌕
              </span>
              <input
                type="search"
                placeholder="Buscar filme ou cinema…"
                value={termo}
                onChange={(e) => setTermo(e.target.value)}
                aria-label="Buscar eventos"
              />
            </form>

            <SeletorLocal
              cidade={cidade}
              uf={uf}
              onEscolher={(c, u) => navegar(urlVitrine({ cidade: c, uf: u }))}
            />
          </div>

          <nav className="nav">
            {usuario?.role === 'CUSTOMER' && (
              <NavLink
                to="/meus-ingressos"
                className={({ isActive }) => (isActive ? 'nav-item ativo' : 'nav-item')}
              >
                Meus ingressos
              </NavLink>
            )}
            {usuario?.role === 'ORGANIZER' && (
              <NavLink
                to="/organizador"
                className={({ isActive }) => (isActive ? 'nav-item ativo' : 'nav-item')}
              >
                Meus eventos
              </NavLink>
            )}
            {usuario?.role === 'GATE' && (
              <NavLink
                to="/portaria"
                className={({ isActive }) => (isActive ? 'nav-item ativo' : 'nav-item')}
              >
                Portaria
              </NavLink>
            )}

            {usuario ? (
              <div className="usuario-chip">
                {/* Nome à vista: em demonstração com três papéis, saber quem
                    está logado evita confusão ao trocar de perfil. */}
                <span className="texto-pp forte">{usuario.name.split(' ')[0]}</span>
                <button
                  type="button"
                  className="avatar"
                  onClick={encerrar}
                  title={`Sair (${usuario.name})`}
                  aria-label="Sair"
                >
                  {iniciais(usuario.name)}
                </button>
              </div>
            ) : (
              <>
                <Link to="/entrar" className="btn btn-fantasma btn-p">
                  Entrar
                </Link>
                <Link to="/criar-conta" className="btn btn-principal btn-p">
                  Criar conta
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="container conteudo">
        <Outlet />
      </main>
    </>
  )
}
