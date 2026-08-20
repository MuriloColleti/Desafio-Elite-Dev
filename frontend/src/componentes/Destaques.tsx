/**
 * Carrossel de destaques — a primeira coisa que se vê.
 *
 * A intenção é a sensação de chegar ao cinema: a parede de cartazes é o que
 * marca a entrada, antes de qualquer texto ou formulário. Por isso o bloco
 * ocupa a largura da tela, tem fundo escuro (o cartaz brilha sobre ele, como
 * numa sala de projeção) e os pôsteres deslizam sozinhos.
 *
 * Comportamento:
 * - Mostra 4 por vez e avança **um** a cada 4s, em laço infinito.
 * - Pausa ao passar o mouse ou focar por teclado: ninguém perde o cartaz que
 *   estava tentando clicar.
 * - Respeita `prefers-reduced-motion` — sem animação para quem pediu.
 * - Setas e indicadores para controle manual, porque animação automática sem
 *   controle é frustrante.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { moeda } from '../lib/formato'
import type { Evento } from '../lib/tipos'

const VISIVEIS = 4
const INTERVALO_MS = 4000

function dataCurta(iso: string): string {
  return new Date(iso)
    .toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
    .replace('.', '')
}

export function Destaques({ eventos }: { eventos: Evento[] }) {
  const [inicio, setInicio] = useState(0)
  const [pausado, setPausado] = useState(false)
  const reduzido = useRef(false)

  useEffect(() => {
    // `matchMedia` pode não existir (jsdom, navegador antigo). Sem ele o padrão
    // é animar — quem pediu movimento reduzido tem também a regra CSS.
    reduzido.current =
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  }, [])

  const total = eventos.length

  const avancar = useCallback(() => {
    setInicio((i) => (i + 1) % total)
  }, [total])

  const voltar = useCallback(() => {
    setInicio((i) => (i - 1 + total) % total)
  }, [total])

  useEffect(() => {
    // Menos cartazes que o visível: não há o que rodar.
    if (pausado || total <= VISIVEIS || reduzido.current) return

    const t = setInterval(avancar, INTERVALO_MS)
    return () => clearInterval(t)
  }, [pausado, total, avancar])

  if (total === 0) return null

  // A janela dá a volta: com 8 cartazes e início em 6, mostra 6,7,0,1. É o que
  // faz o laço parecer infinito sem duplicar a lista no DOM.
  const janela = Array.from({ length: Math.min(VISIVEIS, total) }, (_, n) => {
    const evento = eventos[(inicio + n) % total]
    return { evento, chave: `${evento.id}-${n}` }
  })

  const rodando = total > VISIVEIS

  return (
    <section
      className="destaques"
      aria-label="Em destaque"
      onMouseEnter={() => setPausado(true)}
      onMouseLeave={() => setPausado(false)}
      onFocusCapture={() => setPausado(true)}
      onBlurCapture={() => setPausado(false)}
    >
      <div className="destaques-interno">
        <div className="destaques-cabeca">
          <div>
            <span className="destaques-etiqueta">Em destaque</span>
            <h2 className="destaques-titulo">Escolha sua próxima sessão</h2>
          </div>

          {rodando && (
            <div className="destaques-setas">
              <button type="button" onClick={voltar} aria-label="Cartazes anteriores">
                ‹
              </button>
              <button type="button" onClick={avancar} aria-label="Próximos cartazes">
                ›
              </button>
            </div>
          )}
        </div>

        <ul className="destaques-trilha">
          {janela.map(({ evento, chave }) => (
            /* `key` inclui a posição: sem isso o React reaproveitaria o nó ao
               deslizar e a transição de entrada não dispararia. */
            <li key={chave} className="destaque-item">
              <Link to={`/eventos/${evento.id}`} className="destaque">
                <div className="destaque-arte">
                  {evento.poster_url ? (
                    <img src={evento.poster_url} alt="" loading="lazy" />
                  ) : (
                    <div className="destaque-arte-vazia" aria-hidden="true">
                      <span>{evento.title}</span>
                    </div>
                  )}

                  {/* Véu escuro na base: o texto precisa ser legível sobre
                      qualquer cartaz, inclusive os claros. */}
                  <div className="destaque-veu" />

                  <div className="destaque-texto">
                    <h3>{evento.title}</h3>
                    <p className="destaque-meta">
                      {dataCurta(evento.starts_at)} · {evento.venue}
                    </p>
                    <span className="destaque-preco">{moeda(evento.price_cents)}</span>
                  </div>

                  <span className="destaque-tipo">
                    {evento.layout === 'SEATED' ? 'Lugar marcado' : 'Pista'}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>

        {rodando && (
          <div className="destaques-pontos" role="tablist" aria-label="Posição no carrossel">
            {eventos.map((e, n) => (
              <button
                key={e.id}
                type="button"
                role="tab"
                aria-selected={n === inicio}
                aria-label={`Ir para ${e.title}`}
                className={n === inicio ? 'ponto ativo' : 'ponto'}
                onClick={() => setInicio(n)}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
