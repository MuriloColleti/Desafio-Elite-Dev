/**
 * Vitrine com abas.
 *
 * O que importa: cada aba mostra só o seu tipo, o contador reflete o conteúdo
 * real, e a aba escolhida está na URL — senão o link não é compartilhável e o
 * botão "voltar" do navegador não funciona.
 *
 * Busca por `heading` e não por texto: quando o evento não tem pôster, o
 * título aparece também na arte de fallback (decorativa, `aria-hidden`), e
 * `getByText` acharia os dois.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../lib/api'
import type { Evento } from '../lib/tipos'
import { Vitrine } from './Vitrine'

function evento(over: Partial<Evento> = {}): Evento {
  return {
    id: crypto.randomUUID(),
    title: 'Evento',
    synopsis: null,
    poster_url: null,
    venue: 'Local',
    starts_at: new Date(Date.now() + 86_400_000).toISOString(),
    layout: 'SEATED',
    price_cents: 3200,
    capacity: 96,
    status: 'PUBLISHED',
    available: 50,
    ...over,
  }
}

const FILMES = [
  evento({ title: 'Parasita', layout: 'SEATED' }),
  evento({ title: 'O Grande Truque', layout: 'SEATED' }),
]
const SHOWS = [evento({ title: 'Baile do Terreiro', layout: 'GENERAL', venue: 'Circo Voador' })]

function montar(rota = '/') {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <Routes>
        <Route path="/" element={<Vitrine />} />
        <Route path="/shows" element={<Vitrine />} />
        <Route path="/cinema" element={<Vitrine />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Vitrine', () => {
  beforeEach(() => {
    vi.spyOn(api, 'get').mockResolvedValue([...FILMES, ...SHOWS])
  })

  it('abre na aba de cinema', async () => {
    montar('/')

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Parasita' })).toBeInTheDocument())
    expect(screen.getByRole('tab', { name: /Cinema/ })).toHaveAttribute('aria-selected', 'true')
  })

  it('mostra apenas filmes na aba de cinema', async () => {
    montar('/')

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Parasita' })).toBeInTheDocument())
    expect(screen.getByRole('heading', { name: 'O Grande Truque' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Baile do Terreiro' })).not.toBeInTheDocument()
  })

  it('mostra apenas shows na aba de shows', async () => {
    montar('/shows')

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Baile do Terreiro' })).toBeInTheDocument())
    expect(screen.queryByRole('heading', { name: 'Parasita' })).not.toBeInTheDocument()
  })

  it('conta os eventos de cada aba', async () => {
    montar('/')

    // 2 filmes e 1 show: o contador evita clicar às cegas numa aba vazia.
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /Cinema/ })).toHaveTextContent('2'),
    )
    expect(screen.getByRole('tab', { name: /Shows/ })).toHaveTextContent('1')
  })

  it('troca de aba ao clicar', async () => {
    montar('/')
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Parasita' })).toBeInTheDocument())

    await userEvent.click(screen.getByRole('tab', { name: /Shows/ }))

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Baile do Terreiro' })).toBeInTheDocument())
    expect(screen.queryByRole('heading', { name: 'Parasita' })).not.toBeInTheDocument()
  })

  it('oferece a outra aba quando a atual está vazia', async () => {
    // Só shows cadastrados: quem cai em cinema precisa de uma saída, não de um
    // vazio sem ação.
    vi.spyOn(api, 'get').mockResolvedValue(SHOWS)
    montar('/')

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Ver shows e festas/ })).toBeInTheDocument(),
    )
  })

  it('repassa ao servidor o termo que vem da URL', async () => {
    // A busca mora no cabeçalho e chega por `?q=`. É o back-end que sabe filtrar
    // por título E local; refazer isso no cliente divergiria da vitrine.
    const buscar = vi.spyOn(api, 'get').mockResolvedValue(FILMES)
    montar('/?q=parasita')

    await waitFor(() => expect(buscar).toHaveBeenCalledWith(expect.stringContaining('q=parasita')))
  })

  it('avisa quando a busca não acha nada', async () => {
    vi.spyOn(api, 'get').mockResolvedValue([])
    montar('/?q=xyz')

    await waitFor(() => expect(screen.getByText(/Nada encontrado/)).toBeInTheDocument())
  })

  it('mostra o termo ativo como pílula removível', async () => {
    vi.spyOn(api, 'get').mockResolvedValue(FILMES)
    montar('/?q=parasita')

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /parasita/ })).toBeInTheDocument(),
    )
  })

  it('preserva o termo ao trocar de aba', async () => {
    // Quem buscou "rock" em cinema quer ver "rock" em shows, não a lista toda.
    vi.spyOn(api, 'get').mockResolvedValue([...FILMES, ...SHOWS])
    montar('/?q=rock')

    await waitFor(() => expect(screen.getByRole('tab', { name: /Shows/ })).toBeInTheDocument())
    await userEvent.click(screen.getByRole('tab', { name: /Shows/ }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /rock/ })).toBeInTheDocument(),
    )
  })
})
