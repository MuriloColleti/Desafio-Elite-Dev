/** Casca da aplicação: cabeçalho com navegação por papel. */

import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useSessao } from '../auth/Sessao'

export function Layout() {
  const { usuario, sair } = useSessao()
  const navegar = useNavigate()

  async function encerrar() {
    await sair()
    navegar('/')
  }

  return (
    <>
      <header className="cabecalho">
        <div className="container cabecalho-interno">
          <Link to="/" className="marca-logo">
            Palco
          </Link>

          <nav className="nav">
            <NavLink to="/" end>
              Eventos
            </NavLink>

            {usuario?.role === 'CUSTOMER' && <NavLink to="/meus-ingressos">Meus ingressos</NavLink>}
            {usuario?.role === 'ORGANIZER' && <NavLink to="/organizador">Meus eventos</NavLink>}
            {usuario?.role === 'GATE' && <NavLink to="/portaria">Portaria</NavLink>}

            {usuario ? (
              <div className="linha-flex" style={{ gap: 14 }}>
                {/* Nome visível: em demonstração com três papéis, saber quem
                    está logado evita confusão ao trocar de perfil. */}
                <span className="texto-pp texto-fraco">{usuario.name}</span>
                <button type="button" className="btn-texto texto-pp" onClick={encerrar}>
                  Sair
                </button>
              </div>
            ) : (
              <NavLink to="/entrar" className="btn btn-secundario texto-p">
                Entrar
              </NavLink>
            )}
          </nav>
        </div>
      </header>

      <main className="container" style={{ padding: '32px 24px 72px' }}>
        <Outlet />
      </main>
    </>
  )
}
