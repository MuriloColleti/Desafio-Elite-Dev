/**
 * Contexto de sessão.
 *
 * O front não guarda token: a sessão é um cookie httponly que o navegador envia
 * sozinho. Aqui só ficam os dados do usuário, buscados em `/auth/me`, e é o
 * servidor que decide se a sessão vale.
 *
 * Consequência prática: nada de decodificar claims nem de confiar em papel
 * guardado em localStorage. Recarregar a página consulta `/auth/me` de novo.
 */

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { ApiError, api } from '../lib/api'
import type { Papel, Usuario } from '../lib/tipos'

type DadosRegistro = {
  nome: string
  email: string
  senha: string
  papel: 'CUSTOMER' | 'ORGANIZER'
}

type Contexto = {
  usuario: Usuario | null
  carregando: boolean
  entrar: (email: string, senha: string) => Promise<Usuario>
  registrar: (dados: DadosRegistro) => Promise<Usuario>
  sair: () => Promise<void>
}

const SessaoContext = createContext<Contexto | null>(null)

export function ProvedorSessao({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    api
      .get<Usuario>('/auth/me')
      .then(setUsuario)
      // 401 aqui é o caso normal de visitante, não erro a reportar.
      .catch(() => setUsuario(null))
      .finally(() => setCarregando(false))
  }, [])

  const entrar = useCallback(async (email: string, senha: string) => {
    await api.post('/auth/login', { email, password: senha })
    // Relê o perfil em vez de usar o corpo do login: /auth/me é a fonte única,
    // e assim há um só formato de usuário no app.
    const eu = await api.get<Usuario>('/auth/me')
    setUsuario(eu)
    return eu
  }, [])

  const registrar = useCallback(async (dados: DadosRegistro) => {
    // O back-end já devolve a sessão pronta no registro; relemos /auth/me por
    // coerência com o login, para haver um só formato de usuário no app.
    await api.post('/auth/register', {
      name: dados.nome,
      email: dados.email,
      password: dados.senha,
      role: dados.papel,
    })
    const eu = await api.get<Usuario>('/auth/me')
    setUsuario(eu)
    return eu
  }, [])

  const sair = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } catch (e) {
      // Sessão já expirada no servidor: o resultado desejado (estar deslogado)
      // já aconteceu, então não é erro para o usuário.
      if (!(e instanceof ApiError)) throw e
    }
    setUsuario(null)
  }, [])

  return (
    <SessaoContext.Provider value={{ usuario, carregando, entrar, registrar, sair }}>
      {children}
    </SessaoContext.Provider>
  )
}

export function useSessao(): Contexto {
  const ctx = useContext(SessaoContext)
  if (!ctx) throw new Error('useSessao precisa estar dentro de ProvedorSessao')
  return ctx
}

/** Rota para onde cada papel vai ao entrar. */
export function inicioDoPapel(papel: Papel): string {
  switch (papel) {
    case 'ORGANIZER':
      return '/organizador'
    case 'GATE':
      return '/portaria'
    case 'CUSTOMER':
      return '/meus-ingressos'
  }
}
