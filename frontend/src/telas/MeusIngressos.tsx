/**
 * Meus ingressos.
 *
 * O ingresso é desenhado como bilhete: recorte lateral, linha picotada e o QR
 * no talão. É a metáfora que a pessoa reconhece, e diferencia visualmente de
 * "mais um card numa lista".
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { CartaoIngresso } from '../componentes/CartaoIngresso'
import { ApiError, api } from '../lib/api'
import { mensagemDeErro } from '../lib/formato'
import type { Ingresso } from '../lib/tipos'

export function MeusIngressos() {
  const [ingressos, setIngressos] = useState<Ingresso[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<Ingresso[]>('/tickets/me')
      .then(setIngressos)
      .catch((e) =>
        setErro(
          e instanceof ApiError
            ? mensagemDeErro(e.code, e.message)
            : 'Não foi possível carregar seus ingressos.',
        ),
      )
      .finally(() => setCarregando(false))
  }, [])

  if (carregando) return <div className="carregando">Carregando seus ingressos…</div>

  return (
    <div className="pilha pilha-24">
      <h1>Meus ingressos</h1>

      {erro && <div className="aviso aviso-erro">{erro}</div>}

      {!erro && ingressos.length === 0 && (
        <div className="vazio">
          <p style={{ margin: '0 0 12px' }}>Você ainda não tem ingressos.</p>
          <Link to="/" className="btn btn-principal">
            Ver eventos
          </Link>
        </div>
      )}

      <div className="pilha pilha-24">
        {ingressos.map((i) => (
          <CartaoIngresso key={i.id} ingresso={i} />
        ))}
      </div>
    </div>
  )
}
