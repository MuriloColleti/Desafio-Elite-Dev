/**
 * Carrossel de destaques.
 *
 * Um cartaz grande no centro e os vizinhos menores, cortados nas laterais — o
 * formato de vitrine de bilheteria. A perspectiva faz o olho ir direto ao
 * centro, e os cortes nas bordas comunicam que há mais coisa sem precisar de
 * texto explicando.
 *
 * Comportamento:
 * - Avança um cartaz a cada 5s, em laço infinito.
 * - Pausa no hover e no foco por teclado: ninguém perde o cartaz que ia clicar.
 * - Respeita `prefers-reduced-motion`.
 * - Setas sobre os vizinhos e indicadores abaixo, para controle manual.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { localCompleto, moeda } from '../lib/formato'
import type { Evento } from '../lib/tipos'

const INTERVALO_MS = 5000

/** Quantos vizinhos de cada lado entram na cena. */
const LADOS = 2

function dataLonga(iso: string): string {
  const d = new Date(iso)
  return `${d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }).replace('.', '')} · ${d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`
}



export function Destaques({ eventos }: { eventos: Evento[] }) {
  const [centro, setCentro] = useState(0)
  const [pausado, setPausado] = useState(false)
  const reduzido = useRef(false)

  useEffect(() => {
    reduzido.current = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  }, [])

  const total = eventos.length

  const avancar = useCallback(() => setCentro((i) => (i + 1) % total), [total])
  const voltar = useCallback(() => setCentro((i) => (i - 1 + total) % total), [total])

  useEffect(() => {
    if (pausado || total <= 1 || reduzido.current) return
    const t = setInterval(avancar, INTERVALO_MS)
    return () => clearInterval(t)
  }, [pausado, total, avancar])

  if (total === 0) return null

  const emDestaque = eventos[centro]

  // Cada posição visível recebe um deslocamento relativo ao centro (-2..+2).
  // A cena é montada por posição, e não pela lista, para o cartaz central estar
  // sempre no meio independentemente de onde o índice esteja.
  const cena = Array.from({ length: LADOS * 2 + 1 }, (_, n) => {
    const desvio = n - LADOS
    const evento = eventos[(centro + desvio + total * 2) % total]
    return { evento, desvio }
  })

  return (
    <section
      className="palco"
      aria-label="Em destaque"
      onMouseEnter={() => setPausado(true)}
      onMouseLeave={() => setPausado(false)}
      onFocusCapture={() => setPausado(true)}
      onBlurCapture={() => setPausado(false)}
    >
      <div className="palco-cena">
        {cena.map(({ evento, desvio }) => {
          const central = desvio === 0

          return (
            <div
              key={`${evento.id}-${desvio}`}
              className={central ? 'palco-carta central' : 'palco-carta'}
              style={{ '--desvio': desvio } as React.CSSProperties}
              // Só o cartaz central é alcançável: tabular pelos vizinhos
              // cortados levaria a um link que a pessoa não vê por inteiro.
              aria-hidden={!central}
            >
              {central ? (
                <Link to={`/eventos/${evento.id}`} className="palco-arte">
                  {evento.poster_url ? (
                    <img src={evento.poster_url} alt="" />
                  ) : (
                    <div className="palco-arte-vazia">
                      <span>{evento.title}</span>
                    </div>
                  )}
                  <span className="palco-preco">{moeda(evento.price_cents)}</span>
                </Link>
              ) : (
                <div className="palco-arte">
                  {evento.poster_url ? (
                    <img src={evento.poster_url} alt="" loading="lazy" />
                  ) : (
                    <div className="palco-arte-vazia">
                      <span>{evento.title}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {total > 1 && (
          <>
            <button
              type="button"
              className="palco-seta esquerda"
              onClick={voltar}
              aria-label="Cartaz anterior"
            >
              ‹
            </button>
            <button
              type="button"
              className="palco-seta direita"
              onClick={avancar}
              aria-label="Próximo cartaz"
            >
              ›
            </button>
          </>
        )}
      </div>

      {/* Legenda embaixo do central, como na bilheteria: o cartaz chama, o
          texto confirma o que é. `aria-live` porque muda sozinho. */}
      <div className="palco-legenda" aria-live="polite">
        <h2>
          <Link to={`/eventos/${emDestaque.id}`}>{emDestaque.title}</Link>
        </h2>
        <p className="palco-meta">
          <span>📍 {localCompleto(emDestaque.venue, emDestaque.city, emDestaque.state)}</span>
          <span>🗓 {dataLonga(emDestaque.starts_at)}</span>
        </p>
      </div>

      {total > 1 && (
        <div className="palco-pontos" role="tablist" aria-label="Posição no carrossel">
          {eventos.map((e, n) => (
            <button
              key={e.id}
              type="button"
              role="tab"
              aria-selected={n === centro}
              aria-label={`Ver ${e.title}`}
              className={n === centro ? 'ponto ativo' : 'ponto'}
              onClick={() => setCentro(n)}
            />
          ))}
        </div>
      )}
    </section>
  )
}
