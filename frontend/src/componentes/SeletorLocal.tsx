/**
 * Seletor de localização.
 *
 * Lista só cidades **onde há evento publicado**, com a contagem ao lado:
 * oferecer um lugar sem nada para comprar é armadilha, e o número ajuda a
 * escolher. As cidades vêm agrupadas por estado, porque é assim que as pessoas
 * pensam localização no Brasil.
 *
 * Um menu, e não um `<select>`, para caber a contagem e o agrupamento — e para
 * o rótulo do botão poder mostrar a escolha atual de forma legível.
 */

import { useEffect, useRef, useState } from 'react'

import { api } from '../lib/api'
import type { Localizacao } from '../lib/tipos'

type Props = {
  cidade: string | null
  uf: string | null
  onEscolher: (cidade: string | null, uf: string | null) => void
}

export function SeletorLocal({ cidade, uf, onEscolher }: Props) {
  const [locais, setLocais] = useState<Localizacao[]>([])
  const [aberto, setAberto] = useState(false)
  const caixa = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api
      .get<Localizacao[]>('/locations')
      .then(setLocais)
      // Falha aqui não pode quebrar a navegação: sem a lista o seletor
      // simplesmente não oferece filtro.
      .catch(() => setLocais([]))
  }, [])

  // Fecha ao clicar fora e ao apertar Esc — o que se espera de um menu.
  useEffect(() => {
    if (!aberto) return

    function foraDaCaixa(e: MouseEvent) {
      if (caixa.current && !caixa.current.contains(e.target as Node)) setAberto(false)
    }
    function escapou(e: KeyboardEvent) {
      if (e.key === 'Escape') setAberto(false)
    }

    document.addEventListener('mousedown', foraDaCaixa)
    document.addEventListener('keydown', escapou)
    return () => {
      document.removeEventListener('mousedown', foraDaCaixa)
      document.removeEventListener('keydown', escapou)
    }
  }, [aberto])

  // Agrupa por UF preservando a ordem que o servidor deu (mais eventos
  // primeiro), então o estado com mais oferta aparece no topo.
  const porEstado = new Map<string, Localizacao[]>()
  for (const l of locais) {
    const chave = l.state ?? '—'
    const atual = porEstado.get(chave) ?? []
    atual.push(l)
    porEstado.set(chave, atual)
  }

  const rotulo = cidade ?? (uf ? `Estado: ${uf}` : 'Todos os lugares')

  function escolher(c: string | null, u: string | null) {
    onEscolher(c, u)
    setAberto(false)
  }

  return (
    <div className="local" ref={caixa}>
      <button
        type="button"
        className={cidade || uf ? 'local-botao ativo' : 'local-botao'}
        onClick={() => setAberto((a) => !a)}
        aria-expanded={aberto}
        aria-haspopup="listbox"
      >
        <span aria-hidden="true">📍</span>
        <span className="local-rotulo">{rotulo}</span>
        <span className="local-flecha" aria-hidden="true">
          {aberto ? '▴' : '▾'}
        </span>
      </button>

      {aberto && (
        <div className="local-menu" role="listbox" aria-label="Escolha o lugar">
          <button
            type="button"
            role="option"
            aria-selected={!cidade && !uf}
            className={!cidade && !uf ? 'local-item ativo' : 'local-item'}
            onClick={() => escolher(null, null)}
          >
            Todos os lugares
          </button>

          {locais.length === 0 ? (
            <p className="local-vazio texto-pp texto-3">Nenhuma cidade com evento.</p>
          ) : (
            [...porEstado.entries()].map(([estado, cidades]) => (
              <div key={estado} className="local-grupo">
                <p className="local-estado">
                  {estado}
                  {/* Filtrar pelo estado inteiro: quem mora em cidade vizinha
                      costuma aceitar ir à capital. */}
                  <button
                    type="button"
                    className="local-todo-estado"
                    onClick={() => escolher(null, estado)}
                  >
                    ver tudo
                  </button>
                </p>

                {cidades.map((l) => (
                  <button
                    key={`${l.city}-${l.state}`}
                    type="button"
                    role="option"
                    aria-selected={cidade === l.city}
                    className={cidade === l.city ? 'local-item ativo' : 'local-item'}
                    onClick={() => escolher(l.city, null)}
                  >
                    <span>{l.city}</span>
                    <span className="local-total">{l.total}</span>
                  </button>
                ))}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
