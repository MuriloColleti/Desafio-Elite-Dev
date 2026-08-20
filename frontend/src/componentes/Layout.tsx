/**
 * Casca da aplicação.
 *
 * O cabeçalho usa a largura toda da janela — logo encostada na esquerda,
 * ações na direita — em vez de respeitar o container central do conteúdo. É a
 * convenção de barra de aplicação: a marca ancora o canto, não flutua no meio.
 *
 * A busca vive aqui, e não na vitrine, porque buscar evento é ação global:
 * funciona de qualquer tela e leva de volta à vitrine com o termo aplicado.
 */

import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { useSessao } from '../auth/Sessao'

/** "Ana Ribeiro" → "AR". */
function iniciais(nome: string): string {
  const p = nome.trim().split(/\s+/)
  return ((p[0]?.[0] ?? '') + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase()
}

export function Layout() {
  const { usuario, sair } = useSessao()
  const navegar = useNavigate()
  const { pathname } = useLocation()
  const [params] = useSearchParams()

  // O termo mora na URL (`?q=`), então a vitrine o lê e o link é
  // compartilhável. Este estado é só o texto sendo digitado.
  const [termo, setTermo] = useState(params.get('q') ?? '')

  // Ao navegar para fora da vitrine, o campo acompanha a URL: senão ele
  // mostraria uma busca que não está mais aplicada.
  useEffect(() => {
    setTermo(params.get('q') ?? '')
  }, [params])

  function buscar(e: React.FormEvent) {
    e.preventDefault()
    const q = termo.trim()
    const base = pathname === '/shows' ? '/shows' : '/'
    navegar(q ? `${base}?q=${encodeURIComponent(q)}` : base)
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

          <div className="barra-direita">
            <form className="campo-busca" onSubmit={buscar} role="search">
              <span className="campo-busca-icone" aria-hidden="true">
                ⌕
              </span>
              <input
                type="search"
                placeholder="Buscar evento, filme ou local…"
                value={termo}
                onChange={(e) => setTermo(e.target.value)}
                aria-label="Buscar eventos"
              />
            </form>

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
        </div>
      </header>

      <main className="container conteudo">
        <Outlet />
      </main>
    </>
  )
}
