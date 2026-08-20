/**
 * Ingresso compartilhado por link — sem autenticação.
 *
 * Somente leitura, e sem QR: a API não devolve o código nesta rota, e a tela
 * diz isso em vez de deixar a pessoa procurando onde está o código. Compartilhar
 * mostra o ingresso; não transfere o direito de entrar.
 */

import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ApiError, api } from '../lib/api'
import { dataHoraLonga } from '../lib/formato'
import type { IngressoPublico as Publico } from '../lib/tipos'

export function IngressoPublico() {
  const { token = '' } = useParams()
  const [ingresso, setIngresso] = useState<Publico | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    api
      .get<Publico>(`/public/tickets/${token}`)
      .then(setIngresso)
      .catch((e) =>
        setErro(
          e instanceof ApiError && e.code === 'NOT_FOUND'
            ? 'Este link não corresponde a nenhum ingresso.'
            : 'Não foi possível carregar o ingresso.',
        ),
      )
      .finally(() => setCarregando(false))
  }, [token])

  if (carregando) return <div className="carregando">Carregando…</div>

  if (!ingresso) {
    return (
      <div className="pilha pilha-16" style={{ maxWidth: 460, margin: '48px auto' }}>
        <div className="aviso aviso-erro">{erro}</div>
        <Link to="/" className="btn btn-secundario">
          Ver eventos
        </Link>
      </div>
    )
  }

  return (
    <div className="pilha pilha-24" style={{ maxWidth: 460, margin: '24px auto' }}>
      <article className="bilhete bilhete-publico">
        <div className="bilhete-corpo">
          <span className="etiqueta etiqueta-usado">Ingresso compartilhado</span>

          <h1 className="bilhete-titulo" style={{ marginTop: 12 }}>
            {ingresso.event_title}
          </h1>

          <p className="texto-p texto-medio" style={{ margin: '8px 0 0' }}>
            {dataHoraLonga(ingresso.event_starts_at)}
            <br />
            {ingresso.event_venue}
          </p>

          <hr className="divisor" style={{ margin: '16px 0' }} />

          <dl className="bilhete-dados">
            <div>
              <dt>{ingresso.seat_label ? 'Assento' : 'Ingressos'}</dt>
              <dd className="serifa" style={{ fontSize: '1.35rem' }}>
                {ingresso.seat_label ?? `${ingresso.quantity}×`}
              </dd>
            </div>
            <div>
              <dt>Titular</dt>
              <dd>{ingresso.holder_name}</dd>
            </div>
            <div>
              <dt>Situação</dt>
              <dd>{ingresso.status === 'USED' ? 'Já utilizado' : 'Válido'}</dd>
            </div>
          </dl>
        </div>
      </article>

      <div className="aviso aviso-neutro">
        Esta é uma visualização. O código de entrada fica apenas com{' '}
        {ingresso.holder_name.split(' ')[0]} — este link não dá acesso ao evento.
      </div>

      <Link to="/" className="btn-texto centro">
        Conhecer o Palco
      </Link>
    </div>
  )
}
