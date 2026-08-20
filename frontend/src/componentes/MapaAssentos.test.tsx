/**
 * Mapa de assentos.
 *
 * O que importa aqui é a indisponibilidade: um assento ocupado precisa ser
 * impossível de escolher, não apenas cinza. Se ele fosse clicável, a pessoa
 * escolheria um lugar vendido e só descobriria no erro da API.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { MapaAssentos } from './MapaAssentos'

const MAPA = { rows: 3, seats_per_row: 4, taken: ['A1', 'B3'] }

describe('MapaAssentos', () => {
  it('desenha um botão por lugar do mapa', () => {
    render(<MapaAssentos mapa={MAPA} selecionado={null} onSelecionar={() => {}} />)
    expect(screen.getAllByRole('button')).toHaveLength(3 * 4)
  })

  it('marca os ocupados como desabilitados', () => {
    render(<MapaAssentos mapa={MAPA} selecionado={null} onSelecionar={() => {}} />)

    expect(screen.getByRole('button', { name: /Assento A1, ocupado/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Assento B3, ocupado/ })).toBeDisabled()
  })

  it('deixa os livres habilitados', () => {
    render(<MapaAssentos mapa={MAPA} selecionado={null} onSelecionar={() => {}} />)
    expect(screen.getByRole('button', { name: /Assento A2, disponível/ })).toBeEnabled()
  })

  it('não chama onSelecionar ao clicar num ocupado', async () => {
    const escolher = vi.fn()
    render(<MapaAssentos mapa={MAPA} selecionado={null} onSelecionar={escolher} />)

    await userEvent.click(screen.getByRole('button', { name: /Assento A1, ocupado/ }))

    expect(escolher).not.toHaveBeenCalled()
  })

  it('devolve o rótulo do assento escolhido', async () => {
    const escolher = vi.fn()
    render(<MapaAssentos mapa={MAPA} selecionado={null} onSelecionar={escolher} />)

    await userEvent.click(screen.getByRole('button', { name: /Assento C4, disponível/ }))

    expect(escolher).toHaveBeenCalledWith('C4')
  })

  it('anuncia o assento selecionado por aria-pressed', () => {
    render(<MapaAssentos mapa={MAPA} selecionado="A2" onSelecionar={() => {}} />)

    const escolhido = screen.getByRole('button', { name: /Assento A2/ })
    expect(escolhido).toHaveAttribute('aria-pressed', 'true')
  })

  it('numera as fileiras a partir de A', () => {
    // O rótulo tem de casar com o que o back-end valida contra o mapa.
    render(<MapaAssentos mapa={{ rows: 2, seats_per_row: 2, taken: [] }} selecionado={null} onSelecionar={() => {}} />)

    for (const rotulo of ['A1', 'A2', 'B1', 'B2']) {
      expect(screen.getByRole('button', { name: new RegExp(`Assento ${rotulo},`) })).toBeInTheDocument()
    }
  })
})
