/**
 * Barra de páginas.
 *
 * A janela com elipses é lógica que erra em silêncio: uma barra mostrando os
 * números errados continua parecendo uma barra. Por isso os testes afirmam
 * exatamente quais botões aparecem.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Paginacao } from './Paginacao'

function montar(paginaAtual: number, totalPaginas: number, onIr = vi.fn()) {
  render(<Paginacao paginaAtual={paginaAtual} totalPaginas={totalPaginas} onIr={onIr} />)
  return onIr
}

/** Números visíveis, na ordem. */
function numeros(): string[] {
  return screen
    .getAllByRole('button')
    .map((b) => b.textContent ?? '')
    .filter((t) => /^\d+$/.test(t))
}

describe('Paginacao', () => {
  it('não aparece com uma página só', () => {
    const { container } = render(
      <Paginacao paginaAtual={1} totalPaginas={1} onIr={vi.fn()} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('mostra todas as páginas quando são poucas', () => {
    montar(1, 5)
    expect(numeros()).toEqual(['1', '2', '3', '4', '5'])
  })

  it('resume com elipses quando são muitas', () => {
    montar(10, 20)

    // Primeira e última sempre presentes: são os destinos mais pedidos depois
    // da vizinhança imediata.
    expect(numeros()).toEqual(['1', '9', '10', '11', '20'])
    expect(screen.getAllByText('…')).toHaveLength(2)
  })

  it('não abre elipse no começo quando a atual está perto dele', () => {
    montar(2, 20)
    expect(numeros()).toEqual(['1', '2', '3', '20'])
  })

  it('mostra o número solto em vez de elipse de um só', () => {
    // Com a atual em 4, a janela é 3-4-5 e sobra o 2 entre ela e a primeira.
    // "… 2 …" ocuparia mais espaço que o próprio 2, então ele aparece.
    montar(4, 20)
    expect(numeros()).toEqual(['1', '2', '3', '4', '5', '20'])
    expect(screen.getAllByText('…')).toHaveLength(1)
  })

  it('marca a página atual', () => {
    montar(3, 10)

    const atual = screen.getByRole('button', { name: 'Página 3' })
    expect(atual).toHaveAttribute('aria-current', 'page')
    expect(atual).toHaveClass('ativo')
  })

  it('desabilita a seta anterior na primeira página', () => {
    montar(1, 10)
    expect(screen.getByRole('button', { name: 'Página anterior' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Próxima página' })).toBeEnabled()
  })

  it('desabilita a seta seguinte na última página', () => {
    montar(10, 10)
    expect(screen.getByRole('button', { name: 'Próxima página' })).toBeDisabled()
  })

  it('avisa qual página foi pedida ao clicar no número', async () => {
    const onIr = montar(1, 5)

    await userEvent.click(screen.getByRole('button', { name: 'Página 3' }))

    expect(onIr).toHaveBeenCalledWith(3)
  })

  it('as setas andam uma página', async () => {
    const onIr = montar(5, 10)

    await userEvent.click(screen.getByRole('button', { name: 'Próxima página' }))
    expect(onIr).toHaveBeenCalledWith(6)

    await userEvent.click(screen.getByRole('button', { name: 'Página anterior' }))
    expect(onIr).toHaveBeenCalledWith(4)
  })

  it('a última página é alcançável mesmo estando longe', () => {
    montar(1, 50)
    expect(screen.getByRole('button', { name: 'Página 50' })).toBeInTheDocument()
  })
})
