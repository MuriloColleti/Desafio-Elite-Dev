/**
 * Rótulos e agrupamento dos gêneros.
 *
 * O back-end usa um enum só para filme e show (a vitrine filtra por gênero
 * independentemente do tipo), mas a interface precisa mostrar apenas os
 * gêneros da aba aberta — oferecer "Pagode" em Cinema seria ruído.
 */

import type { Genero, Layout } from './tipos'

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
  AXE: 'Axé',
  ELETRONICA: 'Eletrônica',
  FORRO: 'Forró',
  FUNK: 'Funk',
  MPB: 'MPB',
  PAGODE: 'Pagode',
  RAP: 'Rap',
  REGGAE: 'Reggae',
  ROCK: 'Rock',
  SAMBA: 'Samba',
  SERTANEJO: 'Sertanejo',
}

const DE_FILME: Genero[] = [
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

const DE_SHOW: Genero[] = [
  'AXE',
  'ELETRONICA',
  'FORRO',
  'FUNK',
  'MPB',
  'PAGODE',
  'RAP',
  'REGGAE',
  'ROCK',
  'SAMBA',
  'SERTANEJO',
]

export function rotuloGenero(g: Genero | null): string | null {
  return g ? (ROTULOS[g] ?? g) : null
}

/** Gêneros que fazem sentido para o tipo de evento da aba. */
export function generosDe(layout: Layout): Genero[] {
  return layout === 'SEATED' ? DE_FILME : DE_SHOW
}
