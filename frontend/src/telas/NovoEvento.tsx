/**
 * Criação de evento a partir do catálogo externo.
 *
 * Dois passos, e não um formulário só: escolher a obra é uma decisão diferente
 * de definir sessão. Juntar tudo numa tela obrigaria a olhar 8 campos antes de
 * saber qual filme está montando.
 *
 * O item do catálogo preenche o que ele sabe (título, sinopse, pôster e
 * gênero) e sugere o layout. O organizador decide o resto — data, sala,
 * cidade, preço — e pode mudar qualquer sugestão.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ApiError, api } from '../lib/api'
import { mensagemDeErro } from '../lib/formato'
import { generosDisponiveis, rotuloGenero } from '../lib/generos'
import type { BuscaCatalogo, Evento, Genero, ItemCatalogo, Layout } from '../lib/tipos'

export function NovoEvento() {
  const navegar = useNavigate()

  const [termo, setTermo] = useState('')
  const [itens, setItens] = useState<ItemCatalogo[]>([])
  const [offline, setOffline] = useState(false)
  const [buscando, setBuscando] = useState(false)
  const [escolhido, setEscolhido] = useState<ItemCatalogo | null>(null)

  const [local, setLocal] = useState('')
  const [quando, setQuando] = useState('')
  const [layout, setLayout] = useState<Layout>('SEATED')
  const [preco, setPreco] = useState('')
  const [fileiras, setFileiras] = useState('8')
  const [porFileira, setPorFileira] = useState('12')
  const [capacidade, setCapacidade] = useState('300')
  const [genero, setGenero] = useState<Genero | ''>('')
  const [cidade, setCidade] = useState('')
  const [estado, setEstado] = useState('')
  const [publicar, setPublicar] = useState(true)

  const [erro, setErro] = useState<string | null>(null)
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => {
      setBuscando(true)
      api
        .get<BuscaCatalogo>(`/catalog/search?q=${encodeURIComponent(termo)}`)
        .then((r) => {
          setItens(r.items)
          setOffline(r.offline)
        })
        .catch(() => setItens([]))
        .finally(() => setBuscando(false))
    }, 300)

    return () => clearTimeout(t)
  }, [termo])

  function escolher(item: ItemCatalogo) {
    setEscolhido(item)
    setLayout(item.suggested_layout)
    if (item.suggested_venue) setLocal(item.suggested_venue)
    // O catálogo classifica o filme; o organizador pode discordar no seletor.
    if (item.suggested_genre) setGenero(item.suggested_genre)
    if (item.suggested_city) setCidade(item.suggested_city)
    if (item.suggested_state) setEstado(item.suggested_state)
    if (item.suggested_starts_at) {
      // <input type="datetime-local"> só aceita "YYYY-MM-DDTHH:mm".
      setQuando(item.suggested_starts_at.slice(0, 16))
    }
  }

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    setErro(null)
    setSalvando(true)

    try {
      const evento = await api.post<Evento>('/organizer/events', {
        catalog_ref: escolhido?.ref ?? null,
        title: escolhido ? null : 'Evento sem título',
        venue: local,
        // O input devolve hora local sem fuso; o `new Date` interpreta como
        // local e o toISOString converte para UTC, que é o que a API espera.
        starts_at: new Date(quando).toISOString(),
        layout,
        genre: genero || null,
        city: cidade.trim() || null,
        state: estado.trim().toUpperCase() || null,
        price_cents: Math.round(parseFloat(preco.replace(',', '.')) * 100),
        seat_rows: layout === 'SEATED' ? Number(fileiras) : null,
        seats_per_row: layout === 'SEATED' ? Number(porFileira) : null,
        capacity: layout === 'GENERAL' ? Number(capacidade) : null,
        publish: publicar,
      })
      navegar(publicar ? `/eventos/${evento.id}` : '/organizador')
    } catch (err) {
      setErro(
        err instanceof ApiError
          ? mensagemDeErro(err.code, err.message)
          : 'Não foi possível criar o evento.',
      )
    } finally {
      setSalvando(false)
    }
  }

  const lugares =
    layout === 'SEATED' ? Number(fileiras) * Number(porFileira) : Number(capacidade) || 0

  return (
    <div className="pilha pilha-24">
      <div className="pilha pilha-8">
        <h1>Criar evento</h1>
        <p className="texto-2 texto-p" style={{ margin: 0 }}>
          Escolha um filme do catálogo e defina a sessão.
        </p>
      </div>

      {offline && (
        <div className="aviso aviso-alerta">
          Catálogo em <strong>modo offline</strong>: nenhuma chave de API configurada, então a busca
          usa um conjunto local de exemplo. O fluxo funciona normalmente.
        </div>
      )}

      {erro && <div className="aviso aviso-erro">{erro}</div>}

      {/* Passo 1 — a obra */}
      <section className="pilha pilha-16">
        <h2 className="passo-titulo">
          <span className="passo-numero">1</span> O que vai acontecer
        </h2>

        {escolhido ? (
          <div className="escolhido">
            {escolhido.poster_url && <img src={escolhido.poster_url} alt="" />}
            <div className="pilha pilha-8">
              <strong style={{ fontSize: '1.15rem' }}>
                {escolhido.title}
              </strong>
              <span className="texto-pp texto-3">
                Filme · TMDb
              </span>
              <button type="button" className="btn-texto texto-pp" onClick={() => setEscolhido(null)}>
                Trocar
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="campo">
              <label htmlFor="busca">Buscar no catálogo</label>
              <input
                id="busca"
                type="search"
                placeholder="nome do filme"
                value={termo}
                onChange={(e) => setTermo(e.target.value)}
              />
            </div>

            {buscando && <p className="texto-pp texto-3">Buscando…</p>}

            <ul className="catalogo-lista">
              {itens.map((i) => (
                <li key={i.ref}>
                  <button type="button" className="catalogo-item" onClick={() => escolher(i)}>
                    {i.poster_url ? (
                      <img src={i.poster_url} alt="" loading="lazy" />
                    ) : (
                      <span className="catalogo-sem-poster" aria-hidden="true" />
                    )}
                    <span className="pilha pilha-8" style={{ textAlign: 'left' }}>
                      <strong className="texto-p">{i.title}</strong>
                      <span className="texto-pp texto-3">
                        Filme
                        {i.suggested_venue ? ` · ${i.suggested_venue}` : ''}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>

            {!buscando && itens.length === 0 && termo && (
              <p className="texto-p texto-3">Nada encontrado para “{termo}”.</p>
            )}
          </>
        )}
      </section>

      {/* Passo 2 — a sessão */}
      {escolhido && (
        <form className="pilha pilha-16" onSubmit={salvar}>
          <h2 className="passo-titulo">
            <span className="passo-numero">2</span> Quando, onde e quanto
          </h2>

          <div className="grade-form">
            <div className="campo">
              <label htmlFor="local">Local</label>
              <input
                id="local"
                required
                placeholder="Cine Belas Artes — Sala 1"
                value={local}
                onChange={(e) => setLocal(e.target.value)}
              />
            </div>

            <div className="campo">
              <label htmlFor="cidade">Cidade</label>
              <input
                id="cidade"
                required
                placeholder="São Paulo"
                value={cidade}
                onChange={(e) => setCidade(e.target.value)}
              />
              <span className="campo-dica">É o que permite filtrar por localização.</span>
            </div>

            <div className="campo">
              <label htmlFor="estado">Estado (UF)</label>
              <input
                id="estado"
                required
                maxLength={2}
                placeholder="SP"
                value={estado}
                onChange={(e) => setEstado(e.target.value.toUpperCase())}
              />
            </div>

            <div className="campo">
              <label htmlFor="genero">Gênero</label>
              <select
                id="genero"
                value={genero}
                onChange={(e) => setGenero(e.target.value as Genero | '')}
              >
                <option value="">Sem gênero</option>
                {generosDisponiveis().map((g) => (
                  <option key={g} value={g}>
                    {rotuloGenero(g)}
                  </option>
                ))}
              </select>
              <span className="campo-dica">Sugerido pelo catálogo; você pode mudar.</span>
            </div>

            <div className="campo">
              <label htmlFor="quando">Data e hora</label>
              <input
                id="quando"
                type="datetime-local"
                required
                value={quando}
                onChange={(e) => setQuando(e.target.value)}
              />
            </div>

            <div className="campo">
              <label htmlFor="preco">Preço do ingresso (R$)</label>
              <input
                id="preco"
                required
                inputMode="decimal"
                placeholder="32,00"
                value={preco}
                onChange={(e) => setPreco(e.target.value)}
              />
            </div>

            <div className="campo">
              <label htmlFor="layout">Tipo de lugar</label>
              <select
                id="layout"
                value={layout}
                onChange={(e) => setLayout(e.target.value as Layout)}
              >
                <option value="SEATED">Lugar marcado (mapa de assentos)</option>
                <option value="GENERAL">Sem lugar marcado (por quantidade)</option>
              </select>
            </div>

            {layout === 'SEATED' ? (
              <>
                <div className="campo">
                  <label htmlFor="fileiras">Fileiras</label>
                  <input
                    id="fileiras"
                    type="number"
                    min={1}
                    max={26}
                    required
                    value={fileiras}
                    onChange={(e) => setFileiras(e.target.value)}
                  />
                  <span className="campo-dica">Máximo 26 (A–Z).</span>
                </div>
                <div className="campo">
                  <label htmlFor="porFileira">Assentos por fileira</label>
                  <input
                    id="porFileira"
                    type="number"
                    min={1}
                    max={99}
                    required
                    value={porFileira}
                    onChange={(e) => setPorFileira(e.target.value)}
                  />
                </div>
              </>
            ) : (
              <div className="campo">
                <label htmlFor="capacidade">Capacidade</label>
                <input
                  id="capacidade"
                  type="number"
                  min={1}
                  required
                  value={capacidade}
                  onChange={(e) => setCapacidade(e.target.value)}
                />
              </div>
            )}
          </div>

          <div className="aviso aviso-neutro">
            {lugares > 0 ? (
              <>
                Serão <strong>{lugares}</strong> lugares
                {layout === 'SEATED' && ' (a capacidade vem do mapa)'}.
              </>
            ) : (
              'Informe as dimensões para calcular a capacidade.'
            )}
          </div>

          <label className="linha-flex texto-p" style={{ gap: 8 }}>
            <input
              type="checkbox"
              checked={publicar}
              onChange={(e) => setPublicar(e.target.checked)}
            />
            Publicar na vitrine agora
          </label>

          <div className="linha-flex" style={{ gap: 10 }}>
            <button type="submit" className="btn btn-principal" disabled={salvando}>
              {salvando ? 'Criando…' : publicar ? 'Criar e publicar' : 'Salvar como rascunho'}
            </button>
            <button
              type="button"
              className="btn btn-secundario"
              onClick={() => navegar('/organizador')}
            >
              Cancelar
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
