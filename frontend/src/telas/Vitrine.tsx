/**
 * Vitrine — porta de entrada, sem exigir login.
 *
 * A plataforma vende sessões de cinema, então não há abas: uma grade só, com
 * filtro por gênero e por cidade. As abas existiam quando havia shows do
 * Ticketmaster; sem a segunda fonte, uma aba solitária seria moldura vazia.
 *
 * **Todo o estado de navegação vive na URL** — busca em `?q=`, gênero em `?g=`,
 * cidade em `?cidade=`, estado em `?uf=`, página em `?p=`. Assim qualquer
 * combinação é compartilhável por link e o botão voltar desfaz um passo por
 * vez, em vez de jogar a pessoa fora da vitrine.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { CardEvento } from '../componentes/CardEvento'
import { Destaques } from '../componentes/Destaques'
import { EmCartaz } from '../componentes/EmCartaz'
import { Paginacao } from '../componentes/Paginacao'
import { Recomendados } from '../componentes/Recomendados'
import { ApiError, api } from '../lib/api'
import { mensagemDeErro } from '../lib/formato'
import { generosDisponiveis, rotuloGenero } from '../lib/generos'
import type { BuscaCatalogo, Evento, Genero, ItemCatalogo, PaginaEventos } from '../lib/tipos'

const POR_PAGINA = 12

export function Vitrine() {
  const [params] = useSearchParams()
  const navegar = useNavigate()

  const busca = params.get('q') ?? ''
  const genero = (params.get('g') as Genero | null) ?? null
  const pagina = Math.max(1, Number(params.get('p') ?? 1) || 1)
  const cidade = params.get('cidade')
  const uf = params.get('uf')

  // Página atual, já filtrada pelo servidor.
  const [resultado, setResultado] = useState<PaginaEventos | null>(null)
  // Lista sem filtro de gênero: alimenta as pílulas, os destaques e os
  // recomendados. Sem ela, filtrar por Terror faria as outras pílulas
  // desaparecerem — e não haveria como voltar.
  const [panorama, setPanorama] = useState<Evento[]>([])
  // Filmes em cartaz segundo o TMDb — contexto, não catálogo de venda.
  const [emCartaz, setEmCartaz] = useState<ItemCatalogo[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    // Rota pública e sem filtro: é o que está passando nos cinemas, não o que a
    // plataforma vende. Falha aqui só omite a seção — não é dado essencial.
    api
      .get<BuscaCatalogo>('/catalog/now-playing?limit=20')
      .then((r) => setEmCartaz(r.items))
      .catch(() => setEmCartaz([]))
  }, [])

  useEffect(() => {
    const qs = new URLSearchParams({ limit: '120' })
    if (busca.trim()) qs.set('q', busca.trim())
    // A localização entra aqui: as pílulas de gênero devem refletir o lugar
    // escolhido, senão ofereceriam "Terror" numa cidade que não tem nenhum.
    if (cidade) qs.set('city', cidade)
    if (uf) qs.set('state', uf)

    api
      .get<PaginaEventos>(`/events?${qs}`)
      .then((r) => setPanorama(r.items))
      .catch(() => setPanorama([]))
  }, [busca, cidade, uf])

  useEffect(() => {
    const t = setTimeout(() => {
      const qs = new URLSearchParams({
        limit: String(POR_PAGINA),
        offset: String((pagina - 1) * POR_PAGINA),
      })
      if (busca.trim()) qs.set('q', busca.trim())
      if (genero) qs.set('genre', genero)
      if (cidade) qs.set('city', cidade)
      if (uf) qs.set('state', uf)

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
              : 'Não foi possível carregar as sessões.',
          ),
        )
        .finally(() => setCarregando(false))
    }, 250)

    return () => clearTimeout(t)
  }, [busca, cidade, genero, pagina, uf])

  const generosComEvento = useMemo(
    () => new Set(panorama.map((e) => e.genre).filter((g): g is Genero => g !== null)),
    [panorama],
  )

  /** Monta a URL preservando o que ainda faz sentido. */
  const url = useCallback(
    (g: Genero | null, p: number): string => {
      const qs = new URLSearchParams()
      if (busca.trim()) qs.set('q', busca.trim())
      if (cidade) qs.set('cidade', cidade)
      if (uf) qs.set('uf', uf)
      if (g) qs.set('g', g)
      // Página 1 fica implícita: `?p=1` na URL é ruído.
      if (p > 1) qs.set('p', String(p))

      return qs.size > 0 ? `/?${qs}` : '/'
    },
    [busca, cidade, uf],
  )

  function irPara(p: number) {
    navegar(url(genero, p))
    // Sem isto a pessoa cai no meio da página seguinte, na mesma altura de
    // rolagem em que estava.
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const lista = resultado?.items ?? []
  const total = resultado?.total ?? 0
  const totalPaginas = Math.max(1, Math.ceil(total / POR_PAGINA))
  const filtrando = busca.trim() !== '' || genero !== null || cidade !== null || uf !== null

  // Destaques e recomendados só na navegação livre: quem procura algo
  // específico não quer uma parede de cartazes na frente do resultado.
  const destaques = filtrando || pagina > 1 ? [] : panorama.slice(0, 8)

  return (
    <div className="pilha pilha-32">
      {destaques.length > 0 && (
        <>
          <Destaques eventos={destaques} />
          {/* Entre o carrossel e os recomendados: sai do que a plataforma vende
              para o que está passando, e volta para o que está vendendo bem. */}
          <EmCartaz itens={emCartaz} sessoes={panorama} />
          <Recomendados eventos={panorama} />
        </>
      )}

      {/* Centralizado: sem abas, título e filtros ficam simétricos com a grade
          em vez de ancorados na margem esquerda. */}
      <div className="vitrine-topo">
        <header className="vitrine-cabeca">
          <h1>O que você vai assistir hoje?</h1>
          <p className="texto-2">
            Sessões de cinema com lugar marcado. Escolha o filme, reserve seu assento e receba o
            ingresso na hora.
          </p>
        </header>

        <div className="generos" role="group" aria-label="Filtrar por gênero">
          <button
            type="button"
            className={genero === null ? 'genero ativo' : 'genero'}
            onClick={() => navegar(url(null, 1))}
          >
            Todos
          </button>

          {/* Só os gêneros que têm sessão: oferecer um filtro que devolve lista
              vazia é armadilha, não escolha. */}
          {generosDisponiveis()
            .filter((g) => generosComEvento.has(g) || g === genero)
            .map((g) => (
              <button
                key={g}
                type="button"
                className={genero === g ? 'genero ativo' : 'genero'}
                // Trocar de gênero volta para a página 1: continuar na 4 depois
                // de filtrar mostraria vazio mesmo havendo resultado.
                onClick={() => navegar(url(genero === g ? null : g, 1))}
              >
                {rotuloGenero(g)}
              </button>
            ))}
        </div>

        {(busca.trim() || cidade || uf) && (
          <div className="vitrine-filtros-ativos">
            {busca.trim() && (
              <button
                type="button"
                className="filtro-ativo"
                onClick={() => {
                  const qs = new URLSearchParams()
                  if (cidade) qs.set('cidade', cidade)
                  if (uf) qs.set('uf', uf)
                  if (genero) qs.set('g', genero)
                  navegar(qs.size > 0 ? `/?${qs}` : '/')
                }}
              >
                “{busca.trim()}” <span aria-hidden="true">✕</span>
              </button>
            )}

            {(cidade || uf) && (
              <button
                type="button"
                className="filtro-ativo"
                onClick={() => {
                  const qs = new URLSearchParams()
                  if (busca.trim()) qs.set('q', busca.trim())
                  if (genero) qs.set('g', genero)
                  navegar(qs.size > 0 ? `/?${qs}` : '/')
                }}
              >
                📍 {cidade ?? uf} <span aria-hidden="true">✕</span>
              </button>
            )}
          </div>
        )}
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
            {filtrando ? '⌕' : '🎬'}
          </span>
          {filtrando ? (
            <>
              <p className="forte">Nada encontrado com esses filtros</p>
              <button type="button" className="btn btn-secundario" onClick={() => navegar('/')}>
                Limpar filtros
              </button>
            </>
          ) : (
            <p className="forte">Nenhuma sessão em cartaz no momento.</p>
          )}
        </div>
      ) : (
        <>
          <p className="centro texto-p texto-3">
            {total} {total === 1 ? 'sessão' : 'sessões'}
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
            Publique a primeira sessão
          </Link>
        </p>
      )}
    </div>
  )
}
