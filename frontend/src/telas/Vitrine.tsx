/**
 * Vitrine — porta de entrada, sem exigir login.
 *
 * Duas abas, porque as duas coisas se compram de formas diferentes: cinema tem
 * lugar marcado e sessão; show tem pista e data única. Misturar os dois numa
 * lista só obrigaria a pessoa a filtrar mentalmente o que não quer.
 *
 * **Todo o estado de navegação vive na URL** — aba no caminho (`/`, `/shows`),
 * busca em `?q=`, gênero em `?g=`, página em `?p=`. Assim qualquer combinação é
 * compartilhável por link e o botão voltar desfaz um passo por vez, em vez de
 * jogar a pessoa fora da vitrine.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import { CardEvento } from '../componentes/CardEvento'
import { Destaques } from '../componentes/Destaques'
import { Paginacao } from '../componentes/Paginacao'
import { Recomendados } from '../componentes/Recomendados'
import { ApiError, api } from '../lib/api'
import { mensagemDeErro } from '../lib/formato'
import { generosDe, rotuloGenero } from '../lib/generos'
import type { Evento, Genero, PaginaEventos } from '../lib/tipos'

type Aba = 'cinema' | 'shows'

const POR_PAGINA = 12

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

  // "/" e "/cinema" abrem cinema; "/shows" abre shows. Cinema é o padrão porque
  // é o fluxo com mapa de assentos, o mais rico de ver.
  const aba: Aba = pathname === '/shows' ? 'shows' : 'cinema'
  const layout = aba === 'cinema' ? 'SEATED' : 'GENERAL'

  const busca = params.get('q') ?? ''
  const genero = (params.get('g') as Genero | null) ?? null
  const pagina = Math.max(1, Number(params.get('p') ?? 1) || 1)

  // Página atual, já filtrada pelo servidor.
  const [resultado, setResultado] = useState<PaginaEventos | null>(null)
  // Lista sem filtro de gênero e sem paginação: alimenta os contadores das
  // abas, as pílulas de gênero, os destaques e os recomendados. Sem ela,
  // filtrar por Terror faria o contador de Cinema virar 4 e as outras pílulas
  // desaparecerem.
  const [panorama, setPanorama] = useState<Evento[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    const qs = new URLSearchParams({ limit: '120' })
    if (busca.trim()) qs.set('q', busca.trim())

    api
      .get<PaginaEventos>(`/events?${qs}`)
      .then((r) => setPanorama(r.items))
      .catch(() => setPanorama([]))
  }, [busca])

  useEffect(() => {
    const t = setTimeout(() => {
      const qs = new URLSearchParams({
        layout,
        limit: String(POR_PAGINA),
        offset: String((pagina - 1) * POR_PAGINA),
      })
      if (busca.trim()) qs.set('q', busca.trim())
      if (genero) qs.set('genre', genero)

      setCarregando(true)
      api
        .get<PaginaEventos>(`/events?${qs}`)
        .then((r) => {
          setResultado(r)
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
  }, [busca, genero, layout, pagina])

  const totalPorAba = useMemo(
    () => ({
      cinema: panorama.filter((e) => e.layout === 'SEATED').length,
      shows: panorama.filter((e) => e.layout === 'GENERAL').length,
    }),
    [panorama],
  )

  const generosComEvento = useMemo(
    () =>
      new Set(
        panorama
          .filter((e) => e.layout === layout)
          .map((e) => e.genre)
          .filter((g): g is Genero => g !== null),
      ),
    [panorama, layout],
  )

  /** Monta a URL preservando o que ainda faz sentido. */
  const url = useCallback(
    (destino: Aba, g: Genero | null, p: number): string => {
      const qs = new URLSearchParams()
      if (busca.trim()) qs.set('q', busca.trim())
      // Gênero de filme não existe em shows: ao trocar de aba ele cai, em vez
      // de filtrar por algo impossível e mostrar lista vazia.
      if (g && generosDe(destino === 'cinema' ? 'SEATED' : 'GENERAL').includes(g)) {
        qs.set('g', g)
      }
      // Página 1 fica implícita: `?p=1` na URL é ruído.
      if (p > 1) qs.set('p', String(p))

      const base = destino === 'cinema' ? '/' : '/shows'
      return qs.size > 0 ? `${base}?${qs}` : base
    },
    [busca],
  )

  function irPara(p: number) {
    navegar(url(aba, genero, p))
    // Sem isto a pessoa cai no meio da página seguinte, na mesma altura de
    // rolagem em que estava.
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const lista = resultado?.items ?? []
  const total = resultado?.total ?? 0
  const totalPaginas = Math.max(1, Math.ceil(total / POR_PAGINA))
  const config = ABAS[aba]
  const filtrando = busca.trim() !== '' || genero !== null

  // Destaques e recomendados só na navegação livre: quem procura algo
  // específico não quer uma parede de cartazes na frente do resultado.
  const destaques = filtrando || pagina > 1 ? [] : panorama.slice(0, 8)

  return (
    <div className="pilha pilha-32">
      {destaques.length > 0 && (
        <>
          <Destaques eventos={destaques} />
          <Recomendados eventos={panorama} />
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
            const ativa = aba === chave

            return (
              <button
                key={chave}
                type="button"
                role="tab"
                aria-selected={ativa}
                className={ativa ? 'aba ativa' : 'aba'}
                onClick={() => navegar(url(chave, genero, 1))}
              >
                <span className="aba-icone" aria-hidden="true">
                  {info.icone}
                </span>
                {info.titulo}
                {/* Do total, não do filtrado: senão "Shows (0)" apareceria só
                    porque o gênero escolhido é de filme. */}
                <span className="aba-contador">{totalPorAba[chave]}</span>
              </button>
            )
          })}
        </div>

        {busca.trim() && (
          <button
            type="button"
            className="filtro-ativo"
            onClick={() => navegar(url(aba, genero, 1))}
          >
            “{busca.trim()}” <span aria-hidden="true">✕</span>
          </button>
        )}
      </div>

      {/* Gêneros da aba aberta. Só os que têm evento aparecem: oferecer um
          filtro que devolve lista vazia é armadilha, não escolha. */}
      <div className="generos" role="group" aria-label="Filtrar por gênero">
        <button
          type="button"
          className={genero === null ? 'genero ativo' : 'genero'}
          onClick={() => navegar(url(aba, null, 1))}
        >
          Todos
        </button>

        {generosDe(layout)
          .filter((g) => generosComEvento.has(g) || g === genero)
          .map((g) => (
            <button
              key={g}
              type="button"
              className={genero === g ? 'genero ativo' : 'genero'}
              // Trocar de gênero volta para a página 1: continuar na 4 depois de
              // filtrar mostraria vazio mesmo havendo resultado.
              onClick={() => navegar(url(aba, genero === g ? null : g, 1))}
            >
              {rotuloGenero(g)}
            </button>
          ))}
      </div>

      {erro && <div className="aviso aviso-erro">{erro}</div>}

      {carregando && lista.length === 0 ? (
        <ul className="grade-eventos">
          {Array.from({ length: POR_PAGINA }, (_, i) => (
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
            {filtrando ? '⌕' : config.icone}
          </span>
          {filtrando ? (
            <>
              <p className="forte">Nada encontrado com esses filtros</p>
              <button
                type="button"
                className="btn btn-secundario"
                onClick={() => navegar(aba === 'shows' ? '/shows' : '/')}
              >
                Limpar filtros
              </button>
            </>
          ) : (
            <>
              <p className="forte">{config.vazio}</p>
              {totalPorAba[aba === 'cinema' ? 'shows' : 'cinema'] > 0 && (
                <button
                  type="button"
                  className="btn btn-secundario"
                  onClick={() => navegar(url(aba === 'cinema' ? 'shows' : 'cinema', null, 1))}
                >
                  Ver {aba === 'cinema' ? 'shows e festas' : 'sessões de cinema'}
                </button>
              )}
            </>
          )}
        </div>
      ) : (
        <>
          <p className="texto-p texto-3">
            {total} {total === 1 ? 'evento' : 'eventos'}
            {totalPaginas > 1 && ` · página ${pagina} de ${totalPaginas}`}
          </p>

          <ul className="grade-eventos">
            {lista.map((e) => (
              <li key={e.id}>
                <CardEvento evento={e} />
              </li>
            ))}
          </ul>

          <Paginacao paginaAtual={pagina} totalPaginas={totalPaginas} onIr={irPara} />
        </>
      )}

      {!carregando && panorama.length === 0 && !busca.trim() && !erro && (
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
