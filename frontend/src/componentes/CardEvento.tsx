/** Card da vitrine. O pôster carrega o peso visual; o texto acompanha. */

import { Link } from 'react-router-dom'

import { dataHora, moeda } from '../lib/formato'
import type { Evento } from '../lib/tipos'

export function CardEvento({ evento }: { evento: Evento }) {
  const esgotado = evento.available <= 0
  const ultimos = !esgotado && evento.available <= 10

  return (
    <Link to={`/eventos/${evento.id}`} className="card-evento">
      <div className="card-poster">
        {evento.poster_url ? (
          <img src={evento.poster_url} alt="" loading="lazy" />
        ) : (
          /* Sem pôster (comum em show), o título vira a arte: melhor do que um
             ícone genérico de imagem quebrada. */
          <div className="card-poster-vazio">
            <span className="serifa">{evento.title}</span>
          </div>
        )}

        <span className="card-tipo">{evento.layout === 'SEATED' ? 'Lugar marcado' : 'Pista'}</span>
      </div>

      <div className="card-corpo">
        <h3 className="card-titulo">{evento.title}</h3>
        <p className="card-meta texto-pp">
          {dataHora(evento.starts_at)}
          <br />
          {evento.venue}
        </p>

        <div className="linha-flex entre card-rodape">
          <span className="preco">{moeda(evento.price_cents)}</span>
          {esgotado ? (
            <span className="texto-pp" style={{ color: 'var(--erro)' }}>
              Esgotado
            </span>
          ) : ultimos ? (
            <span className="texto-pp" style={{ color: 'var(--alerta)' }}>
              Últimos {evento.available}
            </span>
          ) : (
            <span className="texto-pp texto-fraco">{evento.available} disponíveis</span>
          )}
        </div>
      </div>
    </Link>
  )
}
