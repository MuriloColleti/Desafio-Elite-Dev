/**
 * Painel do organizador.
 *
 * Diferente da vitrine, mostra todos os estados — inclusive rascunho e
 * cancelado, e eventos que já passaram. É o histórico de quem produz, não a
 * lista de quem compra.
 */

import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { ApiError, api } from '../lib/api'
import { dataHora, localCompleto, mensagemDeErro, moeda } from '../lib/formato'
import type { Evento } from '../lib/tipos'

const ETIQUETA = {
  PUBLISHED: { classe: 'etiqueta-publicado', texto: 'Publicado' },
  DRAFT: { classe: 'etiqueta-rascunho', texto: 'Rascunho' },
  CANCELLED: { classe: 'etiqueta-cancelado', texto: 'Cancelado' },
} as const

export function PainelOrganizador() {
  const [eventos, setEventos] = useState<Evento[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)
  const [ocupado, setOcupado] = useState<string | null>(null)

  const carregar = useCallback(() => {
    setCarregando(true)
    return api
      .get<Evento[]>('/organizer/events')
      .then((r) => {
        setEventos(r)
        setErro(null)
      })
      .catch((e) =>
        setErro(
          e instanceof ApiError
            ? mensagemDeErro(e.code, e.message)
            : 'Não foi possível carregar seus eventos.',
        ),
      )
      .finally(() => setCarregando(false))
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  async function agir(id: string, acao: 'publicar' | 'cancelar') {
    if (acao === 'cancelar' && !confirm('Cancelar este evento? Ele sai da vitrine.')) return

    setOcupado(id)
    setErro(null)
    try {
      if (acao === 'publicar') {
        await api.patch(`/organizer/events/${id}`, { status: 'PUBLISHED' })
      } else {
        await api.delete(`/organizer/events/${id}`)
      }
      await carregar()
    } catch (e) {
      setErro(e instanceof ApiError ? mensagemDeErro(e.code, e.message) : 'Ação não concluída.')
    } finally {
      setOcupado(null)
    }
  }

  if (carregando && eventos.length === 0) return <div className="carregando">Carregando…</div>

  return (
    <div className="pilha pilha-24">
      <div className="linha-flex entre" style={{ flexWrap: 'wrap', gap: 16 }}>
        <h1>Meus eventos</h1>
        <Link to="/organizador/novo" className="btn btn-principal">
          Criar evento
        </Link>
      </div>

      {erro && <div className="aviso aviso-erro">{erro}</div>}

      {eventos.length === 0 && !erro && (
        <div className="vazio">
          <p style={{ margin: '0 0 12px' }}>Você ainda não criou nenhum evento.</p>
          <Link to="/organizador/novo" className="btn btn-principal">
            Criar o primeiro
          </Link>
        </div>
      )}

      {eventos.length > 0 && (
        <table className="tabela">
          <thead>
            <tr>
              <th>Evento</th>
              <th>Quando</th>
              <th>Tipo</th>
              <th>Preço</th>
              <th>Ocupação</th>
              <th>Situação</th>
              <th aria-label="Ações" />
            </tr>
          </thead>
          <tbody>
            {eventos.map((e) => {
              const vendidos = e.capacity - e.available
              const etiqueta = ETIQUETA[e.status]

              return (
                <tr key={e.id}>
                  <td>
                    <strong>{e.title}</strong>
                    <br />
                    <span className="texto-pp texto-3">{localCompleto(e.venue, e.city, e.state)}</span>
                  </td>
                  <td className="texto-p">{dataHora(e.starts_at)}</td>
                  <td className="texto-p">{e.layout === 'SEATED' ? 'Assento' : 'Pista'}</td>
                  <td className="texto-p">{moeda(e.price_cents)}</td>
                  <td className="texto-p">
                    {/* Barra de ocupação: o número sozinho não dá noção de
                        quanto falta encher a casa. */}
                    <div className="ocupacao" title={`${vendidos} de ${e.capacity}`}>
                      <div
                        className="ocupacao-preenchida"
                        style={{ width: `${(vendidos / e.capacity) * 100}%` }}
                      />
                    </div>
                    <span className="texto-pp texto-3">
                      {vendidos}/{e.capacity}
                    </span>
                  </td>
                  <td>
                    <span className={`etiqueta ${etiqueta.classe}`}>{etiqueta.texto}</span>
                  </td>
                  <td>
                    <div className="linha-flex" style={{ gap: 8, justifyContent: 'flex-end' }}>
                      {e.status === 'DRAFT' && (
                        <button
                          type="button"
                          className="btn btn-secundario texto-pp"
                          disabled={ocupado === e.id}
                          onClick={() => agir(e.id, 'publicar')}
                        >
                          Publicar
                        </button>
                      )}
                      {e.status === 'PUBLISHED' && (
                        <>
                          <Link to={`/eventos/${e.id}`} className="btn-texto texto-pp">
                            Ver
                          </Link>
                          <button
                            type="button"
                            className="btn-texto texto-pp"
                            disabled={ocupado === e.id}
                            onClick={() => agir(e.id, 'cancelar')}
                          >
                            Cancelar
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
