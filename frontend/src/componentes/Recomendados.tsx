/**
 * Lista de recomendados.
 *
 * Formato deliberadamente diferente do carrossel: ali são cartazes verticais
 * grandes; aqui são linhas horizontais compactas, com miniatura, posição e a
 * razão da recomendação. Repetir o mesmo card duas vezes na mesma tela não
 * acrescenta nada — muda o formato ou não vale a seção.
 *
 * O critério é derivado do que já temos, sem endpoint novo: os que estão mais
 * perto de esgotar aparecem primeiro. É a recomendação honesta que os dados
 * permitem — "está acabando" é informação útil de verdade, ao contrário de uma
 * ordem aleatória disfarçada de curadoria.
 */

import { Link } from 'react-router-dom'

import { moeda } from '../lib/formato'
import type { Evento } from '../lib/tipos'

const QUANTOS = 5

function dataCurta(iso: string): string {
  const d = new Date(iso)
  return `${d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }).replace('.', '')}, ${d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`
}

/** Fração vendida, de 0 a 1. */
function ocupacao(e: Evento): number {
  if (e.capacity <= 0) return 0
  return (e.capacity - e.available) / e.capacity
}

/** O motivo mostrado ao lado — o que justifica estar na lista. */
function motivo(e: Evento): { texto: string; tom: 'quente' | 'neutro' } {
  const taxa = ocupacao(e)

  if (e.available <= 10) {
    return { texto: `Últimos ${e.available} ingressos`, tom: 'quente' }
  }
  if (taxa >= 0.5) {
    return { texto: `${Math.round(taxa * 100)}% vendido`, tom: 'quente' }
  }
  return {
    texto: e.layout === 'SEATED' ? 'Lugar marcado' : 'Sem lugar marcado',
    tom: 'neutro',
  }
}

export function Recomendados({ eventos }: { eventos: Evento[] }) {
  // Mais procurados primeiro; empate resolvido pela data mais próxima, para a
  // ordem ser estável entre recarregamentos.
  const lista = [...eventos]
    .sort((a, b) => {
      const dif = ocupacao(b) - ocupacao(a)
      return dif !== 0 ? dif : a.starts_at.localeCompare(b.starts_at)
    })
    .slice(0, QUANTOS)

  if (lista.length === 0) return null

  return (
    <section className="recomendados" aria-labelledby="titulo-recomendados">
      <div className="recomendados-cabeca">
        <div>
          <span className="destaques-etiqueta">Recomendados</span>
          <h2 id="titulo-recomendados" className="destaques-titulo">
            Mais procurados agora
          </h2>
        </div>
      </div>

      <ol className="recomendados-lista">
        {lista.map((e, n) => {
          const razao = motivo(e)

          return (
            <li key={e.id}>
              <Link to={`/eventos/${e.id}`} className="recomendado">
                {/* A posição numerada é o que faz ler como ranking, e não como
                    uma segunda lista de eventos qualquer. */}
                <span className="recomendado-posicao" aria-hidden="true">
                  {n + 1}
                </span>

                <div className="recomendado-arte">
                  {e.poster_url ? (
                    <img src={e.poster_url} alt="" loading="lazy" />
                  ) : (
                    <div className="recomendado-arte-vazia" aria-hidden="true">
                      {e.layout === 'SEATED' ? '🎬' : '🎸'}
                    </div>
                  )}
                </div>

                <div className="recomendado-info">
                  <h3>{e.title}</h3>
                  <p className="recomendado-meta">
                    {dataCurta(e.starts_at)} · {e.venue}
                  </p>
                </div>

                <div className="recomendado-lado">
                  <span className={`recomendado-razao ${razao.tom}`}>{razao.texto}</span>
                  <span className="recomendado-preco">{moeda(e.price_cents)}</span>
                </div>
              </Link>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
