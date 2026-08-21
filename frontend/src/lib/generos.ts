/**
 * Rótulos dos gêneros de filme.
 *
 * O enum do back-end ainda carrega os gêneros musicais, de quando a plataforma
 * também vendia shows. Não foram removidos do banco porque isso exigiria uma
 * migration destrutiva sem ganho; a interface simplesmente não os oferece.
 */

import type { Genero } from './tipos'

const ROTULOS: Record<Genero, string> = {
  ACAO: 'Ação',
  AVENTURA: 'Aventura',
  ANIMACAO: 'Animação',
  COMEDIA: 'Comédia',
  DOCUMENTARIO: 'Documentário',
  DRAMA: 'Drama',
  FANTASIA: 'Fantasia',
  FICCAO: 'Ficção',
  ROMANCE: 'Romance',
  SUSPENSE: 'Suspense',
  TERROR: 'Terror',
}

/** Ordem alfabética: é como se procura numa lista de gêneros. */
const TODOS: Genero[] = [
  'ACAO',
  'AVENTURA',
  'ANIMACAO',
  'COMEDIA',
  'DOCUMENTARIO',
  'DRAMA',
  'FANTASIA',
  'FICCAO',
  'ROMANCE',
  'SUSPENSE',
  'TERROR',
]

export function rotuloGenero(g: Genero | null): string | null {
  return g ? (ROTULOS[g] ?? g) : null
}

export function generosDisponiveis(): Genero[] {
  return TODOS
}
