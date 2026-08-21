/**
 * Em cartaz.
 *
 * O que importa é o casamento entre o filme do TMDb e a sessão da plataforma:
 * quem tem sessão leva à compra, quem não tem fica visível mas inerte. Errar
 * isso produziria links que não vendem nada ou filmes compráveis escondidos.
 */

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import type { Evento, ItemCatalogo } from '../lib/tipos'
import { EmCartaz } from './EmCartaz'

function item(titulo: string, ref: string): ItemCatalogo {
  return {
    ref,
    source: 'tmdb',
    title: titulo,
    synopsis: null,
    poster_url: `https://img/${titulo}.jpg`,
    suggested_starts_at: null,
    suggested_venue: null,
    suggested_city: null,
    suggested_state: null,
    suggested_layout: 'SEATED',
    suggested_genre: 'TERROR',
  }
}

function sessao(id: string, ref: string | null): Evento {
  return {
    id,
    catalog_ref: ref,
    title: 'Sessão',
    synopsis: null,
    poster_url: null,
    venue: 'Sala 1',
    city: 'São Paulo',
    state: 'SP',
    country: 'BR',
    starts_at: new Date(Date.now() + 86_400_000).toISOString(),
    layout: 'SEATED',
    genre: 'TERROR',
    price_cents: 3200,
    capacity: 96,
    status: 'PUBLISHED',
    available: 50,
  }
}

function montar(itens: ItemCatalogo[], sessoes: Evento[] = []) {
  return render(
    <MemoryRouter>
      <EmCartaz itens={itens} sessoes={sessoes} />
    </MemoryRouter>,
  )
}

describe('EmCartaz', () => {
  it('não renderiza nada sem filmes', () => {
    const { container } = montar([])
    expect(container).toBeEmptyDOMElement()
  })

  it('lista os filmes em cartaz', () => {
    montar([item('Corra!', 'tmdb:movie:1'), item('Duna', 'tmdb:movie:2')])

    expect(screen.getByText('Corra!')).toBeInTheDocument()
    expect(screen.getByText('Duna')).toBeInTheDocument()
  })

  it('filme com sessão leva à compra', () => {
    montar([item('Corra!', 'tmdb:movie:1')], [sessao('evt-1', 'tmdb:movie:1')])

    expect(screen.getByRole('link', { name: /Comprar ingresso: Corra!/ })).toHaveAttribute(
      'href',
      '/eventos/evt-1',
    )
    expect(screen.getByText('Ingressos')).toBeInTheDocument()
  })

  it('filme sem sessão não é link', () => {
    // Link que não navega frustra mais que texto simples.
    montar([item('Duna', 'tmdb:movie:2')], [sessao('evt-1', 'tmdb:movie:1')])

    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.getByText('Sem sessão')).toBeInTheDocument()
  })

  it('casa pelo catalog_ref, não pelo título', () => {
    // O título do evento é um snapshot e pode ter sido editado; o `ref` é a
    // única ligação estável entre o provedor e o nosso domínio.
    montar([item('Corra!', 'tmdb:movie:1')], [{ ...sessao('evt-9', 'tmdb:movie:1'), title: 'Outro Nome' }])

    expect(screen.getByRole('link')).toHaveAttribute('href', '/eventos/evt-9')
  })

  it('ignora sessão sem catalog_ref', () => {
    // Evento criado com título livre não tem par no catálogo.
    montar([item('Corra!', 'tmdb:movie:1')], [sessao('evt-1', null)])

    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('usa a primeira sessão quando há várias do mesmo filme', () => {
    // Duas sessões do mesmo filme é normal num cinema; o cartaz leva a uma.
    montar(
      [item('Corra!', 'tmdb:movie:1')],
      [sessao('evt-1', 'tmdb:movie:1'), sessao('evt-2', 'tmdb:movie:1')],
    )

    expect(screen.getByRole('link')).toHaveAttribute('href', '/eventos/evt-1')
  })

  it('marca visualmente quem não tem sessão', () => {
    const { container } = montar(
      [item('Corra!', 'tmdb:movie:1'), item('Duna', 'tmdb:movie:2')],
      [sessao('evt-1', 'tmdb:movie:1')],
    )

    expect(container.querySelectorAll('.cartaz.inativo')).toHaveLength(1)
  })

  it('mostra o gênero do filme', () => {
    montar([item('Corra!', 'tmdb:movie:1')])
    expect(screen.getByText('Terror')).toBeInTheDocument()
  })
})
