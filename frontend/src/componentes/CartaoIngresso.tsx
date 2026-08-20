/** Ingresso desenhado como bilhete: talão com o QR, separado por picotado. */

import { useState } from 'react'

import { urlApi } from '../lib/api'
import { dataHoraLonga } from '../lib/formato'
import type { Ingresso } from '../lib/tipos'

export function CartaoIngresso({ ingresso }: { ingresso: Ingresso }) {
  const [copiado, setCopiado] = useState(false)
  const usado = ingresso.status === 'USED'
  const cancelado = ingresso.status === 'CANCELLED'

  async function copiarLink() {
    try {
      await navigator.clipboard.writeText(ingresso.share_url)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2200)
    } catch {
      // clipboard exige contexto seguro; sem ele o link fica visível para
      // seleção manual, então não vale interromper com um alerta.
    }
  }

  return (
    <article className={'bilhete' + (usado || cancelado ? ' bilhete-inativo' : '')}>
      <div className="bilhete-corpo">
        <div className="linha-flex entre" style={{ alignItems: 'flex-start' }}>
          <div className="pilha pilha-8">
            <h2 className="bilhete-titulo">{ingresso.event_title}</h2>
            <p className="texto-p texto-2" style={{ margin: 0 }}>
              {dataHoraLonga(ingresso.event_starts_at)}
              <br />
              {ingresso.event_venue}
            </p>
          </div>

          {usado && <span className="etiqueta etiqueta-usado">Utilizado</span>}
          {cancelado && <span className="etiqueta etiqueta-cancelado">Cancelado</span>}
        </div>

        <hr className="divisor" />

        <dl className="bilhete-dados">
          <div>
            <dt>{ingresso.seat_label ? 'Assento' : 'Ingressos'}</dt>
            <dd className="bilhete-destaque">
              {ingresso.seat_label ?? `${ingresso.quantity}×`}
            </dd>
          </div>
          <div>
            <dt>Tipo</dt>
            <dd>{ingresso.event_layout === 'SEATED' ? 'Lugar marcado' : 'Pista'}</dd>
          </div>
          {usado && ingresso.used_at && (
            <div>
              <dt>Entrada em</dt>
              <dd>{dataHoraLonga(ingresso.used_at)}</dd>
            </div>
          )}
        </dl>

        <div className="linha-flex" style={{ gap: 10, flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secundario texto-p" onClick={copiarLink}>
            {copiado ? 'Link copiado' : 'Compartilhar'}
          </button>
          <span className="texto-pp texto-3">
            Quem abrir o link vê o ingresso, mas não pode usá-lo para entrar.
          </span>
        </div>
      </div>

      {/* Talão: a linha picotada é o que faz ler como bilhete e não como card. */}
      <div className="bilhete-talao">
        {usado || cancelado ? (
          <div className="qr-invalidado">
            <span className="texto-pp">{usado ? 'Já utilizado' : 'Cancelado'}</span>
          </div>
        ) : (
          <img
            className="qr"
            src={urlApi(`/tickets/${ingresso.id}/qr`)}
            alt={`Código QR do ingresso para ${ingresso.event_title}`}
          />
        )}

        {/* Código legível: a portaria pode digitar se a câmera falhar, e é o
            caminho alternativo que o enunciado exige. */}
        <code className="bilhete-codigo mono">{ingresso.code.slice(0, 8)}…</code>
      </div>
    </article>
  )
}
