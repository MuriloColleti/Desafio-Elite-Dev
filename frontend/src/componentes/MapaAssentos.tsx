/**
 * Mapa de assentos.
 *
 * O back-end manda dimensões + lista de ocupados; a grade é montada aqui. A
 * tela imita a orientação real de uma sala: a tela do cinema no topo, e as
 * fileiras numeradas de A (frente) para trás.
 *
 * Escolhas de interação:
 * - **Vários assentos por compra.** Clicar alterna; o limite é do chamador.
 * - Assento ocupado não é clicável nem focável — ninguém deveria "tentar" um
 *   lugar vendido e receber erro.
 * - Rótulo de fileira nas duas laterais, como em sala de verdade: o olho
 *   procura à esquerda ou à direita dependendo de onde está o assento.
 * - Legenda embaixo, porque cor sozinha não comunica estado (e quem não
 *   distingue as cores precisa da forma e do texto).
 */

import { rotuloAssento } from '../lib/formato'
import type { MapaAssentos as Mapa } from '../lib/tipos'

type Props = {
  mapa: Mapa
  selecionados: string[]
  /** Quantos ainda cabem. Ao chegar a zero, os livres ficam desabilitados. */
  limite: number
  onAlternar: (rotulo: string) => void
}

export function MapaAssentos({ mapa, selecionados, limite, onAlternar }: Props) {
  const ocupados = new Set(mapa.taken)
  const escolhidos = new Set(selecionados)
  const cheio = selecionados.length >= limite

  return (
    <div className="mapa">
      <div className="mapa-tela" aria-hidden="true">
        <span>tela</span>
      </div>

      <div className="mapa-grade" role="group" aria-label="Escolha dos assentos">
        {Array.from({ length: mapa.rows }, (_, fileira) => (
          <div className="mapa-fileira" key={fileira}>
            <span className="mapa-letra" aria-hidden="true">
              {String.fromCharCode(65 + fileira)}
            </span>

            {Array.from({ length: mapa.seats_per_row }, (_, numero) => {
              const rotulo = rotuloAssento(fileira, numero)
              const ocupado = ocupados.has(rotulo)
              const ativo = escolhidos.has(rotulo)
              // No limite, os livres param de aceitar clique — mas os já
              // escolhidos seguem clicáveis, senão não haveria como desfazer.
              const bloqueado = ocupado || (cheio && !ativo)

              return (
                <button
                  key={rotulo}
                  type="button"
                  className={
                    'assento' + (ocupado ? ' ocupado' : '') + (ativo ? ' selecionado' : '')
                  }
                  disabled={bloqueado}
                  aria-label={
                    ocupado
                      ? `Assento ${rotulo}, ocupado`
                      : ativo
                        ? `Assento ${rotulo}, escolhido`
                        : `Assento ${rotulo}, disponível`
                  }
                  aria-pressed={ativo}
                  onClick={() => onAlternar(rotulo)}
                >
                  {numero + 1}
                </button>
              )
            })}

            <span className="mapa-letra" aria-hidden="true">
              {String.fromCharCode(65 + fileira)}
            </span>
          </div>
        ))}
      </div>

      <ul className="mapa-legenda">
        <li>
          <span className="amostra livre" /> Disponível
        </li>
        <li>
          <span className="amostra selecionada" /> Sua escolha
        </li>
        <li>
          <span className="amostra tomada" /> Ocupado
        </li>
      </ul>
    </div>
  )
}
