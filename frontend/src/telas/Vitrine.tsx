/**
 * Vitrine — a porta de entrada, sem exigir login.
 *
 * O pôster manda na composição: é o que o usuário reconhece antes de ler
 * qualquer texto. Por isso o card é dominado pela imagem, e não uma linha de
 * tabela com um ícone ao lado.
 */

import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { CardEvento } from '../componentes/CardEvento'
import { ApiError, api } from '../lib/api'
import { mensagemDeErro } from '../lib/formato'
import type { Evento, Layout } from '../lib/tipos'

export function Vitrine() {
  const [eventos, setEventos] = useState<Evento[]>([])
  const [busca, setBusca] = useState('')
  const [layout, setLayout] = useState<Layout | ''>('')
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  // A busca vai ao servidor (é ele que sabe filtrar por título e local), com
  // um atraso para não disparar uma requisição por tecla digitada.
  useEffect(() => {
    const t = setTimeout(() => {
      const params = new URLSearchParams()
      if (busca.trim()) params.set('q', busca.trim())
      if (layout) params.set('layout', layout)

      setCarregando(true)
      api
        .get<Evento[]>(`/events?${params}`)
        .then((r) => {
          setEventos(r)
          setErro(null)
        })
        .catch((e) =>
          setErro(
            e instanceof ApiError
              ? mensagemDeErro(e.code, e.message)
              : 'Não foi possível carregar os eventos.',
          ),
        )
        .finally(() => setCarregando(false))
    }, 250)

    return () => clearTimeout(t)
  }, [busca, layout])

  const filtrando = useMemo(() => busca.trim() !== '' || layout !== '', [busca, layout])

  return (
    <div className="pilha pilha-32">
      <div className="pilha pilha-8">
        <h1>Em cartaz</h1>
        <p className="texto-medio" style={{ margin: 0, maxWidth: '52ch' }}>
          Sessões de cinema com lugar marcado e shows com pista. Escolha o seu e reserve.
        </p>
      </div>

      <div className="vitrine-filtros">
        <input
          type="search"
          placeholder="Buscar por filme, show ou local…"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          aria-label="Buscar eventos"
        />
        <div className="vitrine-abas" role="group" aria-label="Filtrar por tipo">
          <button
            type="button"
            className={layout === '' ? 'aba ativa' : 'aba'}
            onClick={() => setLayout('')}
          >
            Tudo
          </button>
          <button
            type="button"
            className={layout === 'SEATED' ? 'aba ativa' : 'aba'}
            onClick={() => setLayout('SEATED')}
          >
            Lugar marcado
          </button>
          <button
            type="button"
            className={layout === 'GENERAL' ? 'aba ativa' : 'aba'}
            onClick={() => setLayout('GENERAL')}
          >
            Pista
          </button>
        </div>
      </div>

      {erro && <div className="aviso aviso-erro">{erro}</div>}

      {carregando && eventos.length === 0 && <div className="carregando">Carregando eventos…</div>}

      {!carregando && eventos.length === 0 && !erro && (
        <div className="vazio">
          {filtrando ? (
            <>
              <p style={{ margin: 0 }}>Nada encontrado para esta busca.</p>
              <button
                type="button"
                className="btn-texto"
                onClick={() => {
                  setBusca('')
                  setLayout('')
                }}
              >
                Limpar filtros
              </button>
            </>
          ) : (
            <p style={{ margin: 0 }}>
              Nenhum evento publicado ainda. Se você é organizador,{' '}
              <Link to="/organizador/novo" className="btn-texto">
                crie o primeiro
              </Link>
              .
            </p>
          )}
        </div>
      )}

      {eventos.length > 0 && (
        <ul className="grade-eventos">
          {eventos.map((e) => (
            <li key={e.id}>
              <CardEvento evento={e} />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
