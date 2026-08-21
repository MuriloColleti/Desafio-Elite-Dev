/** Contratos da API. Espelham os schemas Pydantic do back-end. */

export type Papel = 'ORGANIZER' | 'CUSTOMER' | 'GATE'
export type Layout = 'SEATED' | 'GENERAL'

/** Gêneros de filme e de show no mesmo tipo — a vitrine filtra por gênero
 *  independentemente do tipo de evento. */
export type Genero =
  | 'ACAO'
  | 'AVENTURA'
  | 'ANIMACAO'
  | 'COMEDIA'
  | 'DOCUMENTARIO'
  | 'DRAMA'
  | 'FANTASIA'
  | 'FICCAO'
  | 'ROMANCE'
  | 'SUSPENSE'
  | 'TERROR'
  | 'AXE'
  | 'ELETRONICA'
  | 'FORRO'
  | 'FUNK'
  | 'MPB'
  | 'PAGODE'
  | 'RAP'
  | 'REGGAE'
  | 'ROCK'
  | 'SAMBA'
  | 'SERTANEJO'
export type StatusEvento = 'DRAFT' | 'PUBLISHED' | 'CANCELLED'
export type StatusIngresso = 'VALID' | 'USED' | 'CANCELLED'
export type ResultadoPortaria = 'VALID' | 'INVALID' | 'ALREADY_USED' | 'WRONG_EVENT'

export type Usuario = {
  user_id: string
  name: string
  email: string
  role: Papel
  gate_event_id: string | null
}

export type Evento = {
  id: string
  title: string
  synopsis: string | null
  poster_url: string | null
  venue: string
  starts_at: string
  layout: Layout
  genre: Genero | null
  price_cents: number
  capacity: number
  status: StatusEvento
  available: number
}

export type MapaAssentos = {
  rows: number
  seats_per_row: number
  taken: string[]
}

export type EventoDetalhe = Evento & {
  seat_map: MapaAssentos | null
}

export type Reserva = {
  id: string
  event_id: string
  seat_label: string | null
  quantity: number
  status: 'PENDING' | 'PAID' | 'CANCELLED' | 'EXPIRED'
  expires_at: string | null
  total_cents: number
}

export type Pagamento = {
  payment_id: string
  status: 'APPROVED' | 'DECLINED'
  amount_cents: number
  ticket_id: string
  ticket_code: string
}

export type Ingresso = {
  id: string
  code: string
  status: StatusIngresso
  used_at: string | null
  event_id: string
  event_title: string
  event_venue: string
  event_starts_at: string
  event_poster_url: string | null
  event_layout: Layout
  seat_label: string | null
  quantity: number
  share_url: string
}

/** Versão pública: sem `code`, porque o link não dá direito de entrada. */
export type IngressoPublico = {
  status: StatusIngresso
  event_title: string
  event_venue: string
  event_starts_at: string
  event_poster_url: string | null
  seat_label: string | null
  quantity: number
  holder_name: string
}

export type RespostaPortaria = {
  result: ResultadoPortaria
  message: string
  event_title: string | null
  holder_name: string | null
  seat_label: string | null
  quantity: number | null
  used_at: string | null
}

export type ItemCatalogo = {
  ref: string
  source: 'tmdb' | 'ticketmaster'
  title: string
  synopsis: string | null
  poster_url: string | null
  suggested_starts_at: string | null
  suggested_venue: string | null
  suggested_layout: Layout
  suggested_genre: Genero | null
}

export type BuscaCatalogo = {
  items: ItemCatalogo[]
  offline: boolean
}
