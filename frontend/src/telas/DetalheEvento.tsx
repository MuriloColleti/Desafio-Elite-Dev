/**
 * Detalhe do evento e escolha do lugar.
 *
 * Dois fluxos na mesma tela, porque a decisão é a mesma ("qual lugar quero"),
 * só a forma muda: mapa de assentos para lugar marcado, seletor de quantidade
 * para pista.
 */

import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useSessao } from '../auth/Sessao'
import { MapaAssentos } from '../componentes/MapaAssentos'
import { ApiError, api } from '../lib/api'
import { cidadeUf, dataHoraLonga, mensagemDeErro, moeda } from '../lib/formato'
import { rotuloGenero } from '../lib/generos'
import type { EventoDetalhe, GrupoReservas } from '../lib/tipos'

export function DetalheEvento() {
  const { id = '' } = useParams()
  const navegar = useNavigate()
  const { usuario } = useSessao()

  const [evento, setEvento] = useState<EventoDetalhe | null>(null)
  const [assentos, setAssentos] = useState<string[]>([])
  const [quantidade, setQuantidade] = useState(1)
  const [erro, setErro] = useState<string | null>(null)
  const [reservando, setReservando] = useState(false)
  const [carregando, setCarregando] = useState(true)

  const carregar = useCallback(() => {
    return api
      .get<EventoDetalhe>(`/events/${id}`)
      .then((e) => {
        setEvento(e)
        setErro(null)
      })
      .catch((e) =>
        setErro(
          e instanceof ApiError
            ? mensagemDeErro(e.code, e.message)
            : 'Não foi possível carregar o evento.',
        ),
      )
      .finally(() => setCarregando(false))
  }, [id])

  useEffect(() => {
    carregar()
  }, [carregar])

  async function reservar() {
    if (!evento) return

    if (!usuario) {
      navegar('/entrar', { state: { de: `/eventos/${id}` } })
      return
    }

    setReservando(true)
    setErro(null)

    try {
      const grupo = await api.post<GrupoReservas>('/reservations', {
        event_id: evento.id,
        seat_labels: evento.layout === 'SEATED' ? assentos : [],
        quantity: evento.layout === 'SEATED' ? 1 : quantidade,
      })

      // O checkout recebe os ids na URL e o prazo pelo sessionStorage: a
      // reserva pendente não tem endpoint próprio de leitura.
      const ids = grupo.reservations.map((r) => r.id)
      if (grupo.expires_at) {
        sessionStorage.setItem(`grupo:${ids.join(',')}`, grupo.expires_at)
      }
      navegar(`/checkout/${ids.join(',')}`)
    } catch (e) {
      if (e instanceof ApiError) {
        setErro(mensagemDeErro(e.code, e.message))
        // Perder um assento é o caso em que a tela precisa se atualizar: o
        // mapa mostrava o lugar como livre e ele não está mais. Limpa a escolha
        // inteira porque a reserva é tudo ou nada — nada ficou reservado.
        if (e.code === 'SEAT_TAKEN') {
          setAssentos([])
          await carregar()
        }
      } else {
        setErro('Não foi possível reservar.')
      }
    } finally {
      setReservando(false)
    }
  }

  if (carregando) return <div className="carregando">Carregando…</div>

  if (!evento) {
    return (
      <div className="pilha pilha-16">
        <div className="aviso aviso-erro">{erro ?? 'Evento não encontrado.'}</div>
        <Link to="/" className="btn-texto">
          ← Voltar para os eventos
        </Link>
      </div>
    )
  }

  const esgotado = evento.available <= 0
  const podeReservar =
    !esgotado && (evento.layout === 'SEATED' ? assentos.length > 0 : quantidade >= 1)
  const total =
    evento.price_cents * (evento.layout === 'SEATED' ? assentos.length : quantidade)
  const maxPorCompra = Math.min(10, evento.available)
  // Mesmo limite do back-end (MAX_ASSENTOS): mais que isso, uma pessoa
  // bloquearia meia fileira durante o hold.
  const maxAssentos = Math.min(6, evento.available)

  return (
    <div className="pilha pilha-24">
      <Link to="/" className="btn-texto texto-p">
        ← Todos os eventos
      </Link>

      <div className="evento-topo">
        {evento.poster_url ? (
          <img className="evento-poster" src={evento.poster_url} alt={`Pôster de ${evento.title}`} />
        ) : (
          <div className="evento-poster-vazio">{evento.title}</div>
        )}

        <div className="pilha pilha-16">
          <div className="pilha pilha-8">
            <div className="linha-flex" style={{ gap: 8 }}>
              <span className="etiqueta etiqueta-marca">
                {evento.layout === 'SEATED' ? '🎬 Lugar marcado' : '🎫 Sem lugar marcado'}
              </span>
              {rotuloGenero(evento.genre) && (
                <span className="etiqueta etiqueta-usado">{rotuloGenero(evento.genre)}</span>
              )}
            </div>
            <h1>{evento.title}</h1>
          </div>

          <dl className="evento-dados">
            <div className="dado-pilula">
              <span className="dado-pilula-icone" aria-hidden="true">🗓</span>
              <div>
                <dt>Quando</dt>
                <dd>{dataHoraLonga(evento.starts_at)}</dd>
              </div>
            </div>
            <div className="dado-pilula">
              <span className="dado-pilula-icone" aria-hidden="true">📍</span>
              <div>
                <dt>Onde</dt>
                {/* Cinema e cidade em linhas separadas: "Cine Odeon" sozinho não
                    diz onde é, e concatenar tudo numa linha só fica longo. */}
                <dd>
                  {evento.venue}
                  {cidadeUf(evento.city, evento.state) && (
                    <>
                      <br />
                      <span className="texto-pp texto-3">
                        {cidadeUf(evento.city, evento.state)}
                      </span>
                    </>
                  )}
                </dd>
              </div>
            </div>
            <div className="dado-pilula">
              <span className="dado-pilula-icone" aria-hidden="true">🎟</span>
              <div>
                <dt>Ingresso</dt>
                <dd>{moeda(evento.price_cents)}</dd>
              </div>
            </div>
          </dl>

          {evento.synopsis && (
            <p className="texto-2" style={{ margin: 0, maxWidth: '60ch' }}>
              {evento.synopsis}
            </p>
          )}
        </div>
      </div>

      <hr className="divisor" />

      {erro && <div className="aviso aviso-erro">{erro}</div>}

      {esgotado ? (
        <div className="vazio">
          <p style={{ margin: 0 }}>Os ingressos deste evento esgotaram.</p>
        </div>
      ) : (
        <div className="reserva-area">
          <div className="pilha pilha-16">
            <h2>{evento.layout === 'SEATED' ? 'Escolha seu lugar' : 'Quantos ingressos?'}</h2>

            {evento.layout === 'SEATED' && evento.seat_map ? (
              <>
                <MapaAssentos
                  mapa={evento.seat_map}
                  selecionados={assentos}
                  limite={maxAssentos}
                  onAlternar={(r) =>
                    setAssentos((atual) =>
                      atual.includes(r) ? atual.filter((a) => a !== r) : [...atual, r],
                    )
                  }
                />
                <p className="texto-pp texto-3 centro">
                  {assentos.length === 0
                    ? `Escolha até ${maxAssentos} assentos.`
                    : assentos.length >= maxAssentos
                      ? `Limite de ${maxAssentos} assentos por compra.`
                      : `${assentos.length} escolhido${assentos.length > 1 ? 's' : ''} · até ${maxAssentos}`}
                </p>
              </>
            ) : (
              <div className="quantidade">
                <button
                  type="button"
                  className="qtd-btn"
                  onClick={() => setQuantidade((q) => Math.max(1, q - 1))}
                  disabled={quantidade <= 1}
                  aria-label="Diminuir"
                >
                  −
                </button>
                <span className="quantidade-valor" aria-live="polite">
                  {quantidade}
                </span>
                <button
                  type="button"
                  className="qtd-btn"
                  onClick={() => setQuantidade((q) => Math.min(maxPorCompra, q + 1))}
                  disabled={quantidade >= maxPorCompra}
                  aria-label="Aumentar"
                >
                  +
                </button>
                <span className="texto-pp texto-3">
                  {maxPorCompra < 10
                    ? `${maxPorCompra} restantes`
                    : 'até 10 ingressos por compra'}
                </span>
              </div>
            )}
          </div>

          {/* Resumo fixo: o total tem de estar visível junto do botão, sem
              precisar rolar de volta ao preço. */}
          <aside className="resumo">
            <h3>Resumo</h3>
            <hr className="divisor" />

            <div className="linha-flex entre texto-p">
              <span className="texto-2">
                {evento.layout === 'SEATED'
                  ? assentos.length > 0
                    ? // Ordenado: a lista muda conforme a ordem dos cliques, e
                      // "F7, A1, C3" no resumo parece desorganizado.
                      `Assento${assentos.length > 1 ? 's' : ''} ${[...assentos].sort().join(', ')}`
                    : 'Nenhum assento'
                  : `${quantidade} × ingresso`}
              </span>
              <span>{moeda(total)}</span>
            </div>

            <div className="linha-flex entre">
              <strong>Total</strong>
              <strong className="preco" style={{ fontSize: '1.45rem' }}>
                {moeda(total)}
              </strong>
            </div>

            <button
              type="button"
              className="btn btn-principal btn-largo btn-grande"
              onClick={reservar}
              disabled={!podeReservar || reservando}
            >
              {reservando
                ? 'Reservando…'
                : !usuario
                  ? 'Entrar e reservar'
                  : assentos.length > 1
                    ? `Reservar ${assentos.length} assentos`
                    : 'Reservar'}
            </button>

            <p className="texto-pp texto-3" style={{ margin: 0 }}>
              {assentos.length > 1 ? 'Os lugares ficam' : 'O lugar fica'} reservado por 10 minutos
              para você concluir o pagamento.
            </p>
          </aside>
        </div>
      )}
    </div>
  )
}
