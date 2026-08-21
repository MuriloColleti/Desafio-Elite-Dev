/**
 * Mapa de assentos.
 *
 * Dois comportamentos que erram em silêncio se quebrarem:
 *
 * - **Indisponibilidade.** Um assento ocupado precisa ser *impossível* de
 *   clicar, não apenas cinza — senão a pessoa escolhe um lugar vendido e só
 *   descobre no erro da API.
 * - **Limite.** Ao atingir o máximo, os livres param de aceitar clique, mas os
 *   já escolhidos continuam clicáveis — senão não haveria como desfazer.
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { MapaAssentos } from './MapaAssentos'

const MAPA = { rows: 3, seats_per_row: 4, taken: ['A1', 'B3'] }

function montar(selecionados: string[] = [], limite = 6, onAlternar = vi.fn()) {
  render(
    <MapaAssentos
      mapa={MAPA}
      selecionados={selecionados}
      limite={limite}
      onAlternar={onAlternar}
    />,
  )
  return onAlternar
}

describe('MapaAssentos', () => {
  it('desenha um botão por lugar do mapa', () => {
    montar()
    expect(screen.getAllByRole('button')).toHaveLength(3 * 4)
  })

  it('marca os ocupados como desabilitados', () => {
    montar()

    expect(screen.getByRole('button', { name: /Assento A1, ocupado/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Assento B3, ocupado/ })).toBeDisabled()
  })

  it('deixa os livres habilitados', () => {
    montar()
    expect(screen.getByRole('button', { name: /Assento A2, disponível/ })).toBeEnabled()
  })

  it('não chama onAlternar ao clicar num ocupado', async () => {
    const alternar = montar()

    await userEvent.click(screen.getByRole('button', { name: /Assento A1, ocupado/ }))

    expect(alternar).not.toHaveBeenCalled()
  })

  it('devolve o rótulo do assento clicado', async () => {
    const alternar = montar()

    await userEvent.click(screen.getByRole('button', { name: /Assento C4, disponível/ }))

    expect(alternar).toHaveBeenCalledWith('C4')
  })

  it('numera as fileiras a partir de A', () => {
    // O rótulo tem de casar com o que o back-end valida contra o mapa.
    render(
      <MapaAssentos
        mapa={{ rows: 2, seats_per_row: 2, taken: [] }}
        selecionados={[]}
        limite={6}
        onAlternar={() => {}}
      />,
    )

    for (const rotulo of ['A1', 'A2', 'B1', 'B2']) {
      expect(
        screen.getByRole('button', { name: new RegExp(`Assento ${rotulo},`) }),
      ).toBeInTheDocument()
    }
  })

  // --- Seleção múltipla ---

  it('marca vários assentos como escolhidos', () => {
    montar(['A2', 'B1'])

    expect(screen.getByRole('button', { name: /Assento A2, escolhido/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: /Assento B1, escolhido/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('desabilita os livres ao atingir o limite', () => {
    montar(['A2', 'A3'], 2)

    expect(screen.getByRole('button', { name: /Assento A4, disponível/ })).toBeDisabled()
  })

  it('mantém os escolhidos clicáveis no limite', async () => {
    // Sem isto a pessoa fica presa: escolheu o máximo e não consegue trocar.
    const alternar = montar(['A2', 'A3'], 2)

    const escolhido = screen.getByRole('button', { name: /Assento A2, escolhido/ })
    expect(escolhido).toBeEnabled()

    await userEvent.click(escolhido)
    expect(alternar).toHaveBeenCalledWith('A2')
  })

  it('não desabilita nada abaixo do limite', () => {
    montar(['A2'], 6)
    expect(screen.getByRole('button', { name: /Assento A3, disponível/ })).toBeEnabled()
  })

  it('anuncia o estado de cada assento por texto, não só por cor', () => {
    // Quem não distingue as cores precisa da informação no nome acessível.
    montar(['A2'])

    expect(screen.getByRole('button', { name: /A1, ocupado/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /A2, escolhido/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /A3, disponível/ })).toBeInTheDocument()
  })
})
