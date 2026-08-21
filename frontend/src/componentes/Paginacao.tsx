/**
 * Barra de páginas.
 *
 * Numerada, e não "carregar mais", por três razões: dá noção de quanto existe,
 * permite voltar direto a uma página, e a posição vive na URL — então o link é
 * compartilhável e o botão voltar funciona.
 *
 * Com muitas páginas, mostra uma janela em volta da atual com elipses. Trinta
 * botões numerados seriam pior que nenhum.
 */

const VIZINHOS = 1

/**
 * Números a exibir, com `null` no lugar das elipses.
 *
 * Primeira e última sempre aparecem: são os destinos mais pedidos depois da
 * vizinhança imediata.
 */
function janela(atual: number, total: number): (number | null)[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, n) => n + 1)
  }

  const paginas = new Set<number>([1, total, atual])
  for (let d = 1; d <= VIZINHOS; d++) {
    if (atual - d > 1) paginas.add(atual - d)
    if (atual + d < total) paginas.add(atual + d)
  }

  const ordenadas = [...paginas].sort((a, b) => a - b)
  const saida: (number | null)[] = []

  ordenadas.forEach((p, i) => {
    // Buraco entre dois números vira elipse; um único número faltando é
    // mostrado, porque "… 5 …" ocupa mais espaço que o próprio 5.
    if (i > 0) {
      const anterior = ordenadas[i - 1]
      if (p - anterior === 2) saida.push(anterior + 1)
      else if (p - anterior > 2) saida.push(null)
    }
    saida.push(p)
  })

  return saida
}

type Props = {
  paginaAtual: number
  totalPaginas: number
  onIr: (pagina: number) => void
}

export function Paginacao({ paginaAtual, totalPaginas, onIr }: Props) {
  // Uma página só não precisa de navegação.
  if (totalPaginas <= 1) return null

  const primeira = paginaAtual <= 1
  const ultima = paginaAtual >= totalPaginas

  return (
    <nav className="paginacao" aria-label="Páginas de eventos">
      <button
        type="button"
        className="pg-seta"
        onClick={() => onIr(paginaAtual - 1)}
        disabled={primeira}
        aria-label="Página anterior"
      >
        ‹
      </button>

      {janela(paginaAtual, totalPaginas).map((p, i) =>
        p === null ? (
          <span key={`gap-${i}`} className="pg-elipse" aria-hidden="true">
            …
          </span>
        ) : (
          <button
            key={p}
            type="button"
            className={p === paginaAtual ? 'pg-num ativo' : 'pg-num'}
            onClick={() => onIr(p)}
            aria-label={`Página ${p}`}
            aria-current={p === paginaAtual ? 'page' : undefined}
          >
            {p}
          </button>
        ),
      )}

      <button
        type="button"
        className="pg-seta"
        onClick={() => onIr(paginaAtual + 1)}
        disabled={ultima}
        aria-label="Próxima página"
      >
        ›
      </button>
    </nav>
  )
}
