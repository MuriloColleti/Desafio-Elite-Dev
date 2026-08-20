/**
 * Card da vitrine.
 *
 * O pôster ocupa a maior parte e cresce no hover; o texto acompanha embaixo,
 * sem caixa. A data vai num selo sobre a imagem porque é a informação que
 * decide se a pessoa clica — mais até que o título, quando ela já sabe o que
 * quer assistir.
 */

import { Link } from 'react-router-dom'

import { moeda } from '../lib/formato'
import type { Evento } from '../lib/tipos'

/** "sáb, 23 ago" e "19:00" separados, para o selo ter duas linhas. */
function partesDaData(iso: string): { dia: string; hora: string } {
  const d = new Date(iso)
  return {
    dia: d
      .toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
      .replace('.', '')
      .toUpperCase(),
    hora: d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
  }
}

export function CardEvento({ evento }: { evento: Evento }) {
  const esgotado = evento.available <= 0
  const ultimos = !esgotado && evento.available <= 10
  const { dia, hora } = partesDaData(evento.starts_at)

  return (
    <Link to={`/eventos/${evento.id}`} className="card">
      <div className="card-arte">
        {evento.poster_url ? (
          <img src={evento.poster_url} alt="" loading="lazy" />
        ) : (
          /* Show raramente tem pôster: o título vira a arte, em degradê, em vez
             de um ícone de imagem quebrada.

             `aria-hidden` porque é repetição decorativa — o título já está no
             <h3> abaixo, e sem isto o leitor de tela o anunciaria duas vezes. */
          <div className="card-arte-vazia" aria-hidden="true">
            <span>{evento.title}</span>
          </div>
        )}

        <div className="card-data" aria-hidden="true">
          <strong>{dia}</strong>
          <span>{hora}</span>
        </div>

        {esgotado && <div className="card-selo esgotado">Esgotado</div>}
        {ultimos && <div className="card-selo ultimos">Últimos {evento.available}</div>}
      </div>

      <div className="card-info">
        <h3 className="card-titulo">{evento.title}</h3>
        <p className="card-local texto-pp texto-3">{evento.venue}</p>
        <div className="card-rodape">
          <span className="preco">{moeda(evento.price_cents)}</span>
          <span className="card-cta texto-pp">
            {evento.layout === 'SEATED' ? 'Escolher lugar' : 'Comprar'} →
          </span>
        </div>
      </div>
    </Link>
  )
}
