/**
 * Lista de recomendados.
 *
 * A ordenação é o que pode errar em silêncio: uma lista "mais procurados" na
 * ordem errada continua parecendo certa na tela. Por isso os testes afirmam a
 * ordem, e não só a presença.
 */

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { Evento } from '../lib/tipos'
import { Recomendados } from './Recomendados'

function evento(titulo: string, capacidade: number, disponivel: number, dias = 5): Evento {
  return {
    id: `id-${titulo}`,
    title: titulo,
    synopsis: null,
    poster_url: `https://img/${titulo}.jpg`,
    venue: 'Sala 1',
    starts_at: new Date(Date.now() + dias * 86_400_000).toISOString(),
    layout: 'SEATED',
    genre: 'DRAMA',
    price_cents: 3200,
    capacity: capacidade,
    status: 'PUBLISHED',
    available: disponivel,
  }
}

function montar(eventos: Evento[]) {
  return render(
    <MemoryRouter>
      <Recomendados eventos={eventos} />
    </MemoryRouter>,
  )
}

function titulos(): string[] {
  return screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent ?? '')
}

describe('Recomendados', () => {
  it('ordena do mais vendido para o menos vendido', () => {
    montar([
      evento('Vazio', 100, 100), // 0%
      evento('Cheio', 100, 5), // 95%
      evento('Meio', 100, 50), // 50%
    ])

    expect(titulos()).toEqual(['Cheio', 'Meio', 'Vazio'])
  })

  it('desempata pela data mais próxima', () => {
    // Sem critério de desempate a ordem variaria entre recarregamentos.
    montar([
      evento('Depois', 100, 50, 20),
      evento('Antes', 100, 50, 2),
    ])

    expect(titulos()).toEqual(['Antes', 'Depois'])
  })

  it('mostra no máximo cinco', () => {
    montar(Array.from({ length: 9 }, (_, n) => evento(`E${n}`, 100, n)))

    expect(titulos()).toHaveLength(5)
  })

  it('avisa quando faltam poucos ingressos', () => {
    montar([evento('Acabando', 100, 7)])

    expect(screen.getByText('Últimos 7 ingressos')).toBeInTheDocument()
  })

  it('mostra a porcentagem vendida quando passa da metade', () => {
    montar([evento('Meio', 100, 40)])

    expect(screen.getByText('60% vendido')).toBeInTheDocument()
  })

  it('mostra o tipo quando a procura é baixa', () => {
    // Sem número alarmista onde não há urgência: inventar escassez é mentira.
    montar([evento('Tranquilo', 100, 95)])

    expect(screen.getByText('Lugar marcado')).toBeInTheDocument()
  })

  it('cada item leva ao seu evento', () => {
    montar([evento('Filme', 100, 50)])

    expect(screen.getByRole('link')).toHaveAttribute('href', '/eventos/id-Filme')
  })

  it('não renderiza nada sem eventos', () => {
    const { container } = montar([])
    expect(container).toBeEmptyDOMElement()
  })

  it('não divide por zero com capacidade zerada', () => {
    // Dado inválido não pode virar NaN na tela.
    montar([evento('Estranho', 0, 0)])

    expect(titulos()).toEqual(['Estranho'])
    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument()
  })
})
