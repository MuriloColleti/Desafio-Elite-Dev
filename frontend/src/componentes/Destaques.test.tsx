/**
 * Carrossel de destaques.
 *
 * O que importa: mostra 4 de 8, avança sozinho, dá a volta no fim da lista, e
 * **para** quando o mouse está em cima — senão o cartaz escapa debaixo do
 * cursor de quem ia clicar.
 */

import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Evento } from '../lib/tipos'
import { Destaques } from './Destaques'

function evento(titulo: string): Evento {
  return {
    id: `id-${titulo}`,
    title: titulo,
    synopsis: null,
    poster_url: `https://img/${titulo}.jpg`,
    venue: 'Sala 1',
    starts_at: new Date(Date.now() + 86_400_000).toISOString(),
    layout: 'SEATED',
    genre: 'DRAMA',
    price_cents: 3200,
    capacity: 96,
    status: 'PUBLISHED',
    available: 50,
  }
}

const OITO = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'].map(evento)

function montar(eventos = OITO) {
  return render(
    <MemoryRouter>
      <Destaques eventos={eventos} />
    </MemoryRouter>,
  )
}

/** Títulos dos cartazes visíveis, na ordem. */
function visiveis(): string[] {
  return screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent ?? '')
}

describe('Destaques', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('mostra 4 cartazes de uma lista de 8', () => {
    montar()
    expect(visiveis()).toEqual(['A', 'B', 'C', 'D'])
  })

  it('avança um cartaz por vez', () => {
    montar()

    act(() => vi.advanceTimersByTime(4000))

    expect(visiveis()).toEqual(['B', 'C', 'D', 'E'])
  })

  it('dá a volta ao chegar no fim', () => {
    montar()

    // 6 avanços a partir de 0: a janela passa a começar em F e precisa
    // continuar com G, H, A — senão o carrossel "acaba" e fica preso.
    act(() => vi.advanceTimersByTime(4000 * 6))

    expect(visiveis()).toEqual(['G', 'H', 'A', 'B'])
  })

  it('volta ao início depois de uma rodada completa', () => {
    montar()

    act(() => vi.advanceTimersByTime(4000 * 8))

    expect(visiveis()).toEqual(['A', 'B', 'C', 'D'])
  })

  it('pausa quando o mouse está em cima', async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    montar()

    await usuario.hover(screen.getByRole('region', { name: 'Em destaque' }))
    act(() => vi.advanceTimersByTime(4000 * 3))

    // Sem a pausa, o cartaz que a pessoa ia clicar sai debaixo do cursor.
    expect(visiveis()).toEqual(['A', 'B', 'C', 'D'])
  })

  it('retoma quando o mouse sai', async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    montar()
    const area = screen.getByRole('region', { name: 'Em destaque' })

    await usuario.hover(area)
    await usuario.unhover(area)
    act(() => vi.advanceTimersByTime(4000))

    expect(visiveis()).toEqual(['B', 'C', 'D', 'E'])
  })

  it('avança e volta pelas setas', async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    montar()

    await usuario.click(screen.getByRole('button', { name: /Próximos cartazes/ }))
    expect(visiveis()).toEqual(['B', 'C', 'D', 'E'])

    await usuario.click(screen.getByRole('button', { name: /Cartazes anteriores/ }))
    expect(visiveis()).toEqual(['A', 'B', 'C', 'D'])
  })

  it('a seta de voltar dá a volta para o fim da lista', async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    montar()

    await usuario.click(screen.getByRole('button', { name: /Cartazes anteriores/ }))

    expect(visiveis()).toEqual(['H', 'A', 'B', 'C'])
  })

  it('cada cartaz leva ao seu evento', () => {
    montar()
    const links = screen.getAllByRole('link')

    expect(links[0]).toHaveAttribute('href', '/eventos/id-A')
  })

  it('não roda nem mostra controles com 4 ou menos', () => {
    montar(OITO.slice(0, 4))

    expect(visiveis()).toEqual(['A', 'B', 'C', 'D'])
    // Sem cartaz sobrando não há o que rolar; setas seriam decoração inerte.
    expect(screen.queryByRole('button', { name: /Próximos/ })).not.toBeInTheDocument()

    act(() => vi.advanceTimersByTime(4000 * 3))
    expect(visiveis()).toEqual(['A', 'B', 'C', 'D'])
  })

  it('não renderiza nada sem eventos', () => {
    const { container } = montar([])
    expect(container).toBeEmptyDOMElement()
  })

  it('o indicador marca a posição atual', () => {
    montar()

    const pontos = screen.getAllByRole('tab')
    expect(pontos).toHaveLength(8)
    expect(pontos[0]).toHaveAttribute('aria-selected', 'true')

    act(() => vi.advanceTimersByTime(4000))
    expect(screen.getAllByRole('tab')[1]).toHaveAttribute('aria-selected', 'true')
  })

  it('clicar no indicador salta para aquele cartaz', async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    montar()

    await usuario.click(screen.getByRole('tab', { name: /Ir para E/ }))

    expect(visiveis()).toEqual(['E', 'F', 'G', 'H'])
  })
})
