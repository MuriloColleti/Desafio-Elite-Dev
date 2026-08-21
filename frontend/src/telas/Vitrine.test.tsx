/**
 * Vitrine.
 *
 * Sem abas: a plataforma vende só sessões de cinema. O que se testa é o filtro
 * por gênero e por localização vindo da URL, e a paginação.
 *
 * Busca por `heading` dentro da grade, e não por texto: o mesmo evento aparece
 * no carrossel de destaques e na grade, e `getByText` acharia os dois.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../lib/api'
import type { Evento } from '../lib/tipos'
import { Vitrine } from './Vitrine'

function evento(over: Partial<Evento> = {}): Evento {
  return {
    id: crypto.randomUUID(),
    title: 'Filme',
    synopsis: null,
    poster_url: null,
    venue: 'Sala 1',
    city: 'São Paulo',
    state: 'SP',
    country: 'BR',
    starts_at: new Date(Date.now() + 86_400_000).toISOString(),
    layout: 'SEATED',
    genre: 'DRAMA',
    price_cents: 3200,
    capacity: 96,
    status: 'PUBLISHED',
    available: 50,
    ...over,
  }
}

const FILMES = [
  evento({ title: 'Parasita', genre: 'SUSPENSE' }),
  evento({ title: 'Corra!', genre: 'TERROR' }),
  evento({ title: 'Duna', genre: 'FICCAO', city: 'Recife', state: 'PE' }),
]

/** A API devolve um envelope paginado; o mock precisa refletir isso. */
function pagina(itens: Evento[]) {
  return { items: itens, total: itens.length, limit: 12, offset: 0 }
}

/** Mock que filtra como o servidor. Devolver a lista inteira independentemente
 *  dos filtros faria os testes passarem por acidente. */
function mockApi(todos: Evento[]) {
  return vi.spyOn(api, 'get').mockImplementation(async (caminho: string) => {
    const qs = new URLSearchParams(caminho.split('?')[1] ?? '')
    const genero = qs.get('genre')
    const cidade = qs.get('city')

    const itens = todos.filter(
      (e) =>
        (!genero || e.genre === genero) &&
        (!cidade || e.city?.toLowerCase() === cidade.toLowerCase()),
    )
    return pagina(itens) as never
  })
}

function montar(rota = '/') {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <Routes>
        <Route path="/" element={<Vitrine />} />
      </Routes>
    </MemoryRouter>,
  )
}

/** Título na grade, não no carrossel. */
function naGrade(titulo: string): HTMLElement | null {
  const grade = document.querySelector('.grade-eventos')
  if (!grade) return null
  return Array.from(grade.querySelectorAll('h3')).find((h) => h.textContent === titulo) ?? null
}

describe('Vitrine', () => {
  beforeEach(() => {
    // A busca tem debounce de 250ms; `shouldAdvanceTime` deixa o tempo correr
    // sozinho para o `waitFor` não ficar preso no esqueleto de carregamento.
    // Sem declarar aqui, a Vitrine herdaria os fake timers de outro arquivo de
    // teste que roda no mesmo worker — e o debounce nunca dispararia.
    vi.useFakeTimers({ shouldAdvanceTime: true })
    mockApi(FILMES)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('lista as sessões sem exigir login', async () => {
    montar()

    await waitFor(() => expect(naGrade('Parasita')).not.toBeNull())
    expect(naGrade('Duna')).not.toBeNull()
  })

  it('não tem abas de tipo de evento', async () => {
    // As abas existiam quando havia shows; sem a segunda fonte, uma aba
    // solitária seria moldura vazia.
    //
    // Busca pelo grupo `tablist` de abas, e não por `role=tab`: os indicadores
    // do carrossel também usam esse papel.
    montar()

    await waitFor(() => expect(naGrade('Parasita')).not.toBeNull())
    expect(screen.queryByRole('tablist', { name: 'Tipo de evento' })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /Cinema/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /Shows/ })).not.toBeInTheDocument()
  })

  it('oferece apenas gêneros que têm sessão', async () => {
    montar()

    await waitFor(() => expect(screen.getByRole('button', { name: 'Terror' })).toBeInTheDocument())
    // Um filtro que devolve lista vazia é armadilha, não escolha.
    expect(screen.queryByRole('button', { name: 'Romance' })).not.toBeInTheDocument()
  })

  it('não oferece gênero musical', async () => {
    // Herança do enum do back-end, que ainda os carrega.
    montar()

    await waitFor(() => expect(screen.getByRole('button', { name: 'Terror' })).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Pagode' })).not.toBeInTheDocument()
  })

  it('repassa o gênero da URL ao servidor', async () => {
    const buscar = mockApi(FILMES)
    montar('/?g=TERROR')

    await waitFor(() =>
      expect(buscar).toHaveBeenCalledWith(expect.stringContaining('genre=TERROR')),
    )
  })

  it('filtra a grade pelo gênero', async () => {
    montar('/?g=TERROR')

    await waitFor(() => expect(naGrade('Corra!')).not.toBeNull())
    expect(naGrade('Parasita')).toBeNull()
  })

  it('marca o gênero ativo', async () => {
    montar('/?g=TERROR')

    await waitFor(() => expect(screen.getByRole('button', { name: 'Terror' })).toHaveClass('ativo'))
  })

  it('repassa a cidade da URL ao servidor', async () => {
    const buscar = mockApi(FILMES)
    montar('/?cidade=Recife')

    await waitFor(() => expect(buscar).toHaveBeenCalledWith(expect.stringContaining('city=Recife')))
  })

  it('mostra o local como filtro removível', async () => {
    montar('/?cidade=Recife')

    await waitFor(() => expect(screen.getByRole('button', { name: /Recife/ })).toBeInTheDocument())
  })

  it('repassa o termo de busca da URL', async () => {
    const buscar = mockApi(FILMES)
    montar('/?q=duna')

    await waitFor(() => expect(buscar).toHaveBeenCalledWith(expect.stringContaining('q=duna')))
  })

  it('avisa quando nada é encontrado', async () => {
    mockApi([])
    montar('/?q=xyz')

    await waitFor(() => expect(screen.getByText(/Nada encontrado/)).toBeInTheDocument())
  })

  it('combina gênero e cidade', async () => {
    const buscar = mockApi(FILMES)
    montar('/?g=FICCAO&cidade=Recife')

    await waitFor(() => {
      const chamadas = buscar.mock.calls.map((c) => String(c[0]))
      expect(chamadas.some((c) => c.includes('genre=FICCAO') && c.includes('city=Recife'))).toBe(
        true,
      )
    })
  })

  it('trocar de gênero volta para a primeira página', async () => {
    // Continuar na página 4 depois de filtrar mostraria vazio mesmo havendo
    // resultado.
    montar('/?p=3')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Terror' })).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: 'Terror' }))

    await waitFor(() => expect(naGrade('Corra!')).not.toBeNull())
  })
})
