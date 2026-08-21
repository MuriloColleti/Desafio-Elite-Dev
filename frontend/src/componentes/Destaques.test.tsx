/**
 * Carrossel de destaques.
 *
 * O formato é um cartaz central com vizinhos cortados nas laterais, então o que
 * se testa é **qual evento está no centro** — é ele que a legenda descreve e o
 * único clicável. Os vizinhos são cenário: ficam `aria-hidden` justamente para
 * ninguém tabular até um link que não vê por inteiro.
 */

import { act, render, screen } from '@testing-library/react'
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

/** Título do cartaz em destaque, lido da legenda. */
function central(): string {
  return screen.getByRole('heading', { level: 2 }).textContent ?? ''
}

describe('Destaques', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('abre com o primeiro evento no centro', () => {
    montar()
    expect(central()).toBe('A')
  })

  it('mostra local e data do evento central', () => {
    montar()
    expect(screen.getByText(/São Paulo - SP/)).toBeInTheDocument()
  })

  it('avança um cartaz por vez', () => {
    montar()

    act(() => vi.advanceTimersByTime(5000))

    expect(central()).toBe('B')
  })

  it('dá a volta ao chegar no fim', () => {
    montar()

    // Oito avanços numa lista de oito: volta ao início, senão o carrossel
    // "acaba" e fica preso no último.
    act(() => vi.advanceTimersByTime(5000 * 8))

    expect(central()).toBe('A')
  })

  it('pausa quando o mouse está em cima', async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    montar()

    await usuario.hover(screen.getByRole('region', { name: 'Em destaque' }))
    act(() => vi.advanceTimersByTime(5000 * 3))

    // Sem a pausa, o cartaz que a pessoa ia clicar sai debaixo do cursor.
    expect(central()).toBe('A')
  })

  it('retoma quando o mouse sai', async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    montar()
    const area = screen.getByRole('region', { name: 'Em destaque' })

    await usuario.hover(area)
    await usuario.unhover(area)
    act(() => vi.advanceTimersByTime(5000))

    expect(central()).toBe('B')
  })

  it('avança e volta pelas setas', async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    montar()

    await usuario.click(screen.getByRole('button', { name: /Próximo cartaz/ }))
    expect(central()).toBe('B')

    await usuario.click(screen.getByRole('button', { name: /Cartaz anterior/ }))
    expect(central()).toBe('A')
  })

  it('a seta de voltar dá a volta para o fim da lista', async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    montar()

    await usuario.click(screen.getByRole('button', { name: /Cartaz anterior/ }))

    expect(central()).toBe('H')
  })

  it('a legenda leva ao evento central', () => {
    montar()

    expect(screen.getByRole('link', { name: 'A' })).toHaveAttribute('href', '/eventos/id-A')
  })

  it('os vizinhos não são alcançáveis por teclado', () => {
    montar()

    // Dois links: o cartaz central e o título na legenda. Os vizinhos estão
    // cortados, e tabular até eles levaria a um destino que não se vê.
    expect(screen.getAllByRole('link')).toHaveLength(2)
  })

  it('não mostra controles com um evento só', () => {
    montar([evento('Solo')])

    expect(central()).toBe('Solo')
    expect(screen.queryByRole('button', { name: /Próximo/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab')).not.toBeInTheDocument()
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

    act(() => vi.advanceTimersByTime(5000))
    expect(screen.getAllByRole('tab')[1]).toHaveAttribute('aria-selected', 'true')
  })

  it('clicar no indicador salta para aquele cartaz', async () => {
    const usuario = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    montar()

    await usuario.click(screen.getByRole('tab', { name: /Ver E/ }))

    expect(central()).toBe('E')
  })

  it('usa o venue quando não há cidade', () => {
    montar([{ ...evento('Sem Cidade'), city: null, venue: 'Casa de Shows X' }])

    expect(screen.getByText(/Casa de Shows X/)).toBeInTheDocument()
  })
})
