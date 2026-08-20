/**
 * Guarda de rota por papel.
 *
 * É conveniência de navegação, não segurança: a autorização de verdade está no
 * back-end, que rejeita a requisição independentemente do que o front mostre.
 * Aqui só evitamos levar a pessoa a uma tela que ela não pode usar.
 */

import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

import { inicioDoPapel, useSessao } from '../auth/Sessao'
import type { Papel } from '../lib/tipos'

type Props = {
  papel: Papel
  children: ReactNode
}

export function Protegida({ papel, children }: Props) {
  const { usuario, carregando } = useSessao()
  const local = useLocation()

  if (carregando) return <div className="carregando">Carregando…</div>

  if (!usuario) {
    // Guarda de onde veio, para voltar ao lugar certo depois do login.
    return <Navigate to="/entrar" state={{ de: local.pathname }} replace />
  }

  if (usuario.role !== papel) {
    // Papel errado: manda para a tela inicial de quem ele é, em vez de mostrar
    // um "acesso negado" que não oferece saída.
    return <Navigate to={inicioDoPapel(usuario.role)} replace />
  }

  return <>{children}</>
}
