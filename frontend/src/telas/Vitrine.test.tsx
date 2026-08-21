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
    genre: 'DRAMA',
    price_cents: 3200,
    capacity: 96,
    status: 'PUBLISHED',
    available: 50,
    ...over,
  }
}

const FILMES = [
  evento({ title: 'Parasita', layout: 'SEATED', genre: 'SUSPENSE' }),
  evento({ title: 'O Grande Truque', layout: 'SEATED', genre: 'SUSPENSE' }),
  evento({ title: 'Corra!', layout: 'SEATED', genre: 'TERROR' }),
]
const SHOWS = [
  evento({ title: 'Baile do Terreiro', layout: 'GENERAL', venue: 'Circo Voador', genre: 'SAMBA' }),
]

/** Busca o título na **grade**, não no carrossel: o mesmo evento aparece nos
 *  dois, e a grade é o que a aba filtra. */
function naGrade(titulo: string): HTMLElement | null {
  const grade = document.querySelector('.grade-eventos')
  if (!grade) return null
  return (
    Array.from(grade.querySelectorAll('h3')).find((h) => h.textContent === titulo) ?? null
  )
}

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

    await waitFor(() => expect(naGrade('Parasita')).not.toBeNull())
    expect(screen.getByRole('tab', { name: /Cinema/ })).toHaveAttribute('aria-selected', 'true')
  })

  it('mostra apenas filmes na aba de cinema', async () => {
    montar('/')

    await waitFor(() => expect(naGrade('Parasita')).not.toBeNull())
    expect(naGrade('O Grande Truque')).not.toBeNull()
    expect(naGrade('Baile do Terreiro')).toBeNull()
  })

  it('mostra apenas shows na aba de shows', async () => {
    montar('/shows')

    await waitFor(() => expect(naGrade('Baile do Terreiro')).not.toBeNull())
    expect(naGrade('Parasita')).toBeNull()
  })

  it('conta os eventos de cada aba', async () => {
    montar('/')

    // 3 filmes e 1 show: o contador evita clicar às cegas numa aba vazia.
    await waitFor(() =>
      expect(screen.getByRole('tab', { name: /Cinema/ })).toHaveTextContent(String(FILMES.length)),
    )
    expect(screen.getByRole('tab', { name: /Shows/ })).toHaveTextContent(String(SHOWS.length))
  })

  it('troca de aba ao clicar', async () => {
    montar('/')
    await waitFor(() => expect(naGrade('Parasita')).not.toBeNull())

    await userEvent.click(screen.getByRole('tab', { name: /Shows/ }))

    await waitFor(() => expect(naGrade('Baile do Terreiro')).not.toBeNull())
    expect(naGrade('Parasita')).toBeNull()
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

  it('oferece apenas os gêneros da aba aberta', async () => {
    montar('/')

    // Gêneros de filme aparecem; de show, não — oferecer "Samba" em Cinema
    // seria ruído.
    await waitFor(() => expect(screen.getByRole('button', { name: 'Terror' })).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Samba' })).not.toBeInTheDocument()
  })

  it('omite gênero que não tem nenhum evento', async () => {
    montar('/')

    // Um filtro que devolve lista vazia é armadilha, não escolha.
    await waitFor(() => expect(screen.getByRole('button', { name: 'Terror' })).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Romance' })).not.toBeInTheDocument()
  })

  it('repassa o gênero da URL ao servidor', async () => {
    const buscar = vi.spyOn(api, 'get').mockResolvedValue(FILMES)
    montar('/?g=TERROR')

    await waitFor(() =>
      expect(buscar).toHaveBeenCalledWith(expect.stringContaining('genre=TERROR')),
    )
  })

  it('marca o gênero ativo', async () => {
    montar('/?g=TERROR')

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Terror' })).toHaveClass('ativo'),
    )
  })

  it('contador da aba ignora o filtro de gênero', async () => {
    // Senão "Shows (0)" apareceria só porque o gênero escolhido é de filme.
    montar('/?g=TERROR')

    await waitFor(() => expect(screen.getByRole('tab', { name: /Shows/ })).toHaveTextContent('1'))
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
