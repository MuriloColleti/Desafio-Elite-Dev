/** Formatação para exibição. Tudo em pt-BR. */

/** Centavos → "R$ 32,00". O back-end nunca manda float; aqui converte na borda. */
export function moeda(centavos: number): string {
  return (centavos / 100).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  })
}

/** "2026-08-23T22:00:00Z" → "sáb, 23 ago · 19:00" (no fuso do navegador). */
export function dataHora(iso: string): string {
  const d = new Date(iso)
  const dia = d.toLocaleDateString('pt-BR', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
  })
  const hora = d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  return `${dia.replace('.', '')} · ${hora}`
}

/** Versão longa, para a tela de detalhe do evento. */
export function dataHoraLonga(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Minutos e segundos restantes até `iso`, ou null se já passou. */
export function restante(iso: string): { minutos: number; segundos: number } | null {
  const ms = new Date(iso).getTime() - Date.now()
  if (ms <= 0) return null
  const total = Math.floor(ms / 1000)
  return { minutos: Math.floor(total / 60), segundos: total % 60 }
}

/** (0,0) → "A1". Mesma regra do back-end (`rotulo_assento`). */
export function rotuloAssento(fileira: number, numero: number): string {
  return `${String.fromCharCode(65 + fileira)}${numero + 1}`
}

/** Mensagem para o usuário a partir do código de erro da API. */
export function mensagemDeErro(codigo: string, fallback: string): string {
  const mapa: Record<string, string> = {
    NETWORK_ERROR: 'Não foi possível falar com o servidor. Ele está rodando?',
    INVALID_CREDENTIALS: 'E-mail ou senha incorretos.',
    NOT_AUTHENTICATED: 'Sua sessão expirou. Entre novamente.',
    FORBIDDEN: 'Seu perfil não tem acesso a esta ação.',
    SEAT_TAKEN: 'Este lugar acabou de ser reservado por outra pessoa. Escolha outro.',
    SOLD_OUT: 'Os ingressos deste evento esgotaram.',
    RESERVATION_EXPIRED: 'O tempo para concluir a reserva expirou. Escolha o lugar de novo.',
    PAYMENT_DECLINED: 'Pagamento recusado.',
    NOT_FOUND: 'Não encontramos o que você procura.',
    EMAIL_IN_USE: 'Este e-mail já tem conta. Tente entrar.',
  }
  return mapa[codigo] ?? fallback
}
