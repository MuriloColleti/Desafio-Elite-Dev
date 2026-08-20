/** Formatação — a borda onde centavos e ISO viram texto para humano. */

import { describe, expect, it } from 'vitest'

import { mensagemDeErro, moeda, restante, rotuloAssento } from './formato'

describe('moeda', () => {
  it('converte centavos inteiros em reais', () => {
    // O back-end só trabalha com inteiro; a divisão acontece aqui, uma vez.
    expect(moeda(3200)).toMatch(/32,00/)
    expect(moeda(9000)).toMatch(/90,00/)
  })

  it('lida com zero e com valor quebrado', () => {
    expect(moeda(0)).toMatch(/0,00/)
    expect(moeda(1)).toMatch(/0,01/)
    expect(moeda(12345)).toMatch(/123,45/)
  })
})

describe('rotuloAssento', () => {
  it('usa a mesma regra do back-end', () => {
    // Se divergir, o front pediria um assento que a validação do servidor
    // rejeita — e o mapa ficaria inutilizável sem erro visível no cliente.
    expect(rotuloAssento(0, 0)).toBe('A1')
    expect(rotuloAssento(0, 11)).toBe('A12')
    expect(rotuloAssento(7, 0)).toBe('H1')
    expect(rotuloAssento(25, 98)).toBe('Z99')
  })
})

describe('restante', () => {
  it('devolve minutos e segundos até o prazo', () => {
    const daquiA5min = new Date(Date.now() + 5 * 60_000 + 1_000).toISOString()
    const r = restante(daquiA5min)

    expect(r).not.toBeNull()
    expect(r!.minutos).toBe(5)
  })

  it('devolve null quando o prazo já passou', () => {
    // É o sinal que o checkout usa para bloquear o botão de pagar.
    expect(restante(new Date(Date.now() - 1000).toISOString())).toBeNull()
  })
})

describe('mensagemDeErro', () => {
  it('traduz os códigos que a interface trata', () => {
    expect(mensagemDeErro('SEAT_TAKEN', 'x')).toContain('outra pessoa')
    expect(mensagemDeErro('NETWORK_ERROR', 'x')).toContain('servidor')
  })

  it('cai no texto do servidor quando o código é desconhecido', () => {
    // Nunca mostrar o código cru: se aparecer algo novo, o texto da API já é
    // em português e serve melhor que "UNKNOWN_ERROR".
    expect(mensagemDeErro('CODIGO_NOVO', 'mensagem do servidor')).toBe('mensagem do servidor')
  })
})
