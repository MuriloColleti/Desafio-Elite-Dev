/**
 * Vitrine — porta de entrada, sem exigir login.
 *
 * Duas abas, porque as duas coisas se compram de formas diferentes: cinema tem
 * lugar marcado e sessão; show tem pista e data única. Misturar os dois numa
 * lista só obrigaria a pessoa a filtrar mentalmente o que não quer.
 *
 * A aba escolhida vive na URL (`/cinema`, `/shows`), então o link é
 * compartilhável e o botão "voltar" do navegador funciona.
 */

import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { CardEvento } from '../componentes/CardEvento'
import { Destaques } from '../componentes/Destaques'
import { Recomendados } from '../componentes/Recomendados'
import { ApiError, api } from '../lib/api'
import { mensagemDeErro } from '../lib/formato'
import type { Evento } from '../lib/tipos'

type Aba = 'cinema' | 'shows'

const ABAS: Record<Aba, { titulo: string; icone: string; vazio: string }> = {
  cinema: {
    titulo: 'Cinema',
    icone: '🎬',
    vazio: 'Nenhuma sessão em cartaz no momento.',
  },
  shows: {
    titulo: 'Shows e festas',
    icone: '🎸',
    vazio: 'Nenhum show ou festa com ingressos abertos.',
  },
}

export function Vitrine() {
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const navegar = useNavigate()

  // A busca é do cabeçalho e chega por `?q=`: é ação global, funciona de
  // qualquer tela, e o termo na URL torna o resultado compartilhável.
  const busca = params.get('q') ?? ''

  // "/" e "/cinema" abrem cinema; "/shows" abre shows. Cinema é o padrão porque
  // é o fluxo com mapa de assentos, o mais rico de ver.
  const aba: Aba = pathname === '/shows' ? 'shows' : 'cinema'

  // Todos os eventos são carregados uma vez: são poucos, e ter a lista completa
  // em memória permite mostrar o contador de cada aba sem uma segunda chamada.
  const [eventos, setEventos] = useState<Evento[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    const t = setTimeout(() => {
      const qs = new URLSearchParams()
      if (busca.trim()) qs.set('q', busca.trim())

      api
        .get<Evento[]>(`/events?${qs}`)
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
  }, [busca])

  const porAba = useMemo(
    () => ({
      cinema: eventos.filter((e) => e.layout === 'SEATED'),
      shows: eventos.filter((e) => e.layout === 'GENERAL'),
    }),
    [eventos],
  )

  const lista = porAba[aba]
  const config = ABAS[aba]

  function trocarAba(nova: Aba) {
    // Preserva o termo ao trocar de aba: quem buscou "rock" em cinema quer ver
    // "rock" em shows, não a lista inteira.
    const qs = busca.trim() ? `?q=${encodeURIComponent(busca.trim())}` : ''
    navegar((nova === 'cinema' ? '/' : '/shows') + qs)
  }

  // Os destaques só aparecem na navegação livre: com busca ativa, quem procura
  // algo específico não quer uma parede de cartazes na frente do resultado.
  const destaques = busca.trim() ? [] : eventos.slice(0, 8)

  return (
    <div className="pilha pilha-32">
      {destaques.length > 0 && (
        <>
          <Destaques eventos={destaques} />
          <Recomendados eventos={eventos} />
        </>
      )}

      <header className="vitrine-cabeca">
        <h1>O que você vai ver hoje?</h1>
        <p className="texto-2">
          Sessões de cinema com lugar marcado e shows com pista. Escolha, reserve e receba seu
          ingresso na hora.
        </p>
      </header>

      <div className="vitrine-controles">
        <div className="abas" role="tablist" aria-label="Tipo de evento">
          {(Object.keys(ABAS) as Aba[]).map((chave) => {
            const info = ABAS[chave]
            const total = porAba[chave].length
            const ativa = aba === chave

            return (
              <button
                key={chave}
                type="button"
                role="tab"
                aria-selected={ativa}
                className={ativa ? 'aba ativa' : 'aba'}
                onClick={() => trocarAba(chave)}
              >
                <span className="aba-icone" aria-hidden="true">
                  {info.icone}
                </span>
                {info.titulo}
                {/* O contador evita o clique às cegas numa aba vazia. */}
                {!carregando && <span className="aba-contador">{total}</span>}
              </button>
            )
          })}
        </div>

        {busca.trim() && (
          <button
            type="button"
            className="filtro-ativo"
            onClick={() => navegar(aba === 'shows' ? '/shows' : '/')}
          >
            “{busca.trim()}” <span aria-hidden="true">✕</span>
          </button>
        )}
      </div>

      {erro && <div className="aviso aviso-erro">{erro}</div>}

      {carregando ? (
        <ul className="grade-eventos">
          {/* Esqueleto no lugar de "Carregando…": a grade não salta quando os
              dados chegam. */}
          {Array.from({ length: 4 }, (_, i) => (
            <li key={i} className="pilha pilha-8">
              <div className="esqueleto" style={{ aspectRatio: '2 / 3' }} />
              <div className="esqueleto" style={{ height: 16, width: '75%' }} />
              <div className="esqueleto" style={{ height: 13, width: '45%' }} />
            </li>
          ))}
        </ul>
      ) : lista.length === 0 ? (
        <div className="vazio">
          <span className="vazio-icone" aria-hidden="true">
            {busca.trim() ? '⌕' : config.icone}
          </span>
          {busca.trim() ? (
            <>
              <p className="forte">Nada encontrado para “{busca.trim()}”</p>
              <button
                type="button"
                className="btn btn-secundario"
                onClick={() => navegar(aba === 'shows' ? '/shows' : '/')}
              >
                Limpar busca
              </button>
            </>
          ) : (
            <>
              <p className="forte">{config.vazio}</p>
              {/* Se a outra aba tem eventos, oferece o caminho em vez de deixar
                  a pessoa em rua sem saída. */}
              {porAba[aba === 'cinema' ? 'shows' : 'cinema'].length > 0 && (
                <button
                  type="button"
                  className="btn btn-secundario"
                  onClick={() => trocarAba(aba === 'cinema' ? 'shows' : 'cinema')}
                >
                  Ver {aba === 'cinema' ? 'shows e festas' : 'sessões de cinema'}
                </button>
              )}
            </>
          )}
        </div>
      ) : (
        <ul className="grade-eventos">
          {lista.map((e) => (
            <li key={e.id}>
              <CardEvento evento={e} />
            </li>
          ))}
        </ul>
      )}

      {!carregando && eventos.length === 0 && !busca.trim() && !erro && (
        <p className="centro texto-p texto-3">
          É organizador?{' '}
          <Link to="/organizador/novo" className="btn-texto">
            Publique o primeiro evento
          </Link>
        </p>
      )}
    </div>
  )
}
