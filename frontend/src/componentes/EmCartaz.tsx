/**
 * Em cartaz hoje — direto do TMDb.
 *
 * Diferente das outras duas seções: o carrossel e os recomendados mostram
 * **sessões** da plataforma (com sala, horário e preço), esta mostra o que está
 * passando nos cinemas segundo o TMDb. É contexto, não catálogo de venda.
 *
 * O que evita a seção ser decorativa: os filmes que **já têm sessão** aqui
 * levam à compra. Os outros ficam visíveis com a marca de "sem sessão" — é
 * informação honesta, e para o organizador é uma dica do que falta publicar.
 */

import { Link } from 'react-router-dom'

import { rotuloGenero } from '../lib/generos'
import type { Evento, ItemCatalogo } from '../lib/tipos'

type Props = {
  itens: ItemCatalogo[]
  /** Sessões publicadas, para ligar o filme à compra quando existir. */
  sessoes: Evento[]
}

export function EmCartaz({ itens, sessoes }: Props) {
  if (itens.length === 0) return null

  // Indexa por `catalog_ref`: é a única coisa que atravessa a fronteira entre o
  // provedor e o nosso domínio, então é por ela que se liga um ao outro.
  const porRef = new Map<string, Evento>()
  for (const s of sessoes) {
    if (s.catalog_ref && !porRef.has(s.catalog_ref)) porRef.set(s.catalog_ref, s)
  }

  return (
    <section className="cartazes" aria-labelledby="titulo-cartazes">
      <div className="cartazes-cabeca">
        <span className="destaques-etiqueta">Em cartaz</span>
        <h2 id="titulo-cartazes" className="destaques-titulo">
          Passando nos cinemas hoje
        </h2>
        <p className="texto-p texto-3">
          Direto do TMDb. Os que já têm sessão na plataforma levam à compra.
        </p>
      </div>

      {/* Faixa rolável na horizontal: doze cartazes numa grade empurrariam as
          outras seções para muito abaixo da dobra. */}
      <ul className="cartazes-faixa">
        {itens.map((item) => {
          const sessao = porRef.get(item.ref)

          const conteudo = (
            <>
              <div className="cartaz-arte">
                {item.poster_url ? (
                  <img src={item.poster_url} alt="" loading="lazy" />
                ) : (
                  <div className="cartaz-arte-vazia" aria-hidden="true">
                    🎬
                  </div>
                )}

                {sessao ? (
                  <span className="cartaz-selo tem-sessao">Ingressos</span>
                ) : (
                  <span className="cartaz-selo sem-sessao">Sem sessão</span>
                )}
              </div>

              <p className="cartaz-titulo">{item.title}</p>
              {rotuloGenero(item.suggested_genre) && (
                <p className="cartaz-genero texto-pp texto-3">
                  {rotuloGenero(item.suggested_genre)}
                </p>
              )}
            </>
          )

          return (
            <li key={item.ref} className={sessao ? 'cartaz' : 'cartaz inativo'}>
              {sessao ? (
                <Link to={`/eventos/${sessao.id}`} aria-label={`Comprar ingresso: ${item.title}`}>
                  {conteudo}
                </Link>
              ) : (
                // Sem sessão não há para onde ir. Um `<div>` em vez de link
                // desabilitado: link que não navega frustra mais que texto.
                <div>{conteudo}</div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
