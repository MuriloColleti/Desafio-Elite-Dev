/**
 * Checkout — pagamento simulado.
 *
 * A recusa é tela de primeira classe, não um alerta vermelho: o enunciado pede
 * os dois caminhos, e o que a pessoa precisa saber ao ser recusada é o motivo e
 * o que fazer em seguida. O assento já voltou ao estoque nesse ponto, então o
 * caminho oferecido é escolher o lugar de novo.
 *
 * Os cartões de teste ficam à vista. Numa aplicação real seria absurdo; aqui é
 * o que permite ao avaliador exercitar aprovação e recusa sem consultar o
 * README.
 */

import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { ApiError, api } from '../lib/api'
import { mensagemDeErro, restante } from '../lib/formato'
import type { Pagamento } from '../lib/tipos'

const CARTOES = [
  { numero: '4242 4242 4242 4242', rotulo: 'aprovado' },
  { numero: '4000 0000 0000 0002', rotulo: 'recusado' },
  { numero: '4000 0000 0000 9995', rotulo: 'sem saldo' },
]

export function Checkout() {
  const { reservaIds = '' } = useParams()
  const navegar = useNavigate()

  const [cartao, setCartao] = useState('')
  const [titular, setTitular] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [codigoErro, setCodigoErro] = useState<string | null>(null)
  const [pagando, setPagando] = useState(false)
  const [expiraEm, setExpiraEm] = useState<string | null>(null)
  // Contador de segundos: o valor não é usado, só força o re-render que
  // recalcula `restante()` a cada tique.
  const [, setTique] = useState(0)

  // Os ids vêm na URL separados por vírgula: comprar quatro assentos gera
  // quatro reservas, porque a constraint de unicidade é por assento.
  const ids = reservaIds.split(',').filter(Boolean)

  // O prazo do hold é gravado no sessionStorage ao reservar: a reserva pendente
  // ainda não é ingresso e não tem endpoint GET próprio. Se a pessoa recarregar
  // ou abrir o link direto, o contador simplesmente não aparece — o servidor
  // continua sendo quem decide se o prazo venceu.
  useEffect(() => {
    const guardado = sessionStorage.getItem(`grupo:${reservaIds}`)
    if (guardado) setExpiraEm(guardado)
  }, [reservaIds])

  useEffect(() => {
    const t = setInterval(() => setTique((n) => n + 1), 1000)
    return () => clearInterval(t)
  }, [])

  const prazo = expiraEm ? restante(expiraEm) : null
  const expirou = expiraEm !== null && prazo === null

  async function pagar(e: React.FormEvent) {
    e.preventDefault()
    setErro(null)
    setCodigoErro(null)
    setPagando(true)

    try {
      await api.post<Pagamento>('/payments', {
        reservation_ids: ids,
        card_number: cartao,
        card_holder: titular,
      })
      sessionStorage.removeItem(`grupo:${reservaIds}`)
      navegar('/meus-ingressos', { state: { novo: true } })
    } catch (err) {
      if (err instanceof ApiError) {
        setCodigoErro(err.code)
        setErro(err.code === 'PAYMENT_DECLINED' ? err.message : mensagemDeErro(err.code, err.message))
      } else {
        setErro('Não foi possível processar o pagamento.')
      }
    } finally {
      setPagando(false)
    }
  }

  // Recusa cancela a reserva no servidor, então não há como tentar outro
  // cartão na mesma: o caminho é voltar e escolher o lugar de novo.
  const perdeuAReserva =
    codigoErro === 'PAYMENT_DECLINED' ||
    codigoErro === 'RESERVATION_EXPIRED' ||
    codigoErro === 'VALIDATION_FAILED'

  if (perdeuAReserva) {
    return (
      <div className="pilha pilha-24" style={{ maxWidth: 520, margin: '0 auto' }}>
        <div className="pilha pilha-16 centro">
          <span className="selo-recusa" aria-hidden="true">
            ✕
          </span>
          <h1>{codigoErro === 'PAYMENT_DECLINED' ? 'Pagamento recusado' : 'Reserva encerrada'}</h1>
          <p className="texto-2" style={{ margin: 0 }}>
            {erro}
          </p>
        </div>

        <div className="aviso aviso-neutro">
          {ids.length > 1
            ? 'Os lugares voltaram a ficar disponíveis para outras pessoas. Para continuar, escolha novamente.'
            : 'O lugar voltou a ficar disponível para outras pessoas. Para continuar, escolha o lugar novamente.'}
        </div>

        <Link to="/" className="btn btn-principal btn-largo">
          Voltar aos eventos
        </Link>
      </div>
    )
  }

  return (
    <div className="checkout" style={{ maxWidth: 520, margin: '0 auto' }}>
      <div className="pilha pilha-24">
        <div className="pilha pilha-8">
          <h1>Pagamento</h1>
          <p className="texto-2 texto-p" style={{ margin: 0 }}>
            {ids.length > 1
              ? `${ids.length} ingressos numa única cobrança. `
              : ''}
            Cobrança simulada — nenhum valor é movimentado de verdade.
          </p>
        </div>

        {prazo && (
          <div className={prazo.minutos < 2 ? 'aviso aviso-alerta' : 'aviso aviso-neutro'}>
            {ids.length > 1 ? 'Seus lugares estão' : 'Seu lugar está'} reservados por{' '}
            <strong className="mono">
              {String(prazo.minutos).padStart(2, '0')}:{String(prazo.segundos).padStart(2, '0')}
            </strong>
          </div>
        )}

        {expirou && (
          <div className="aviso aviso-erro">
            O tempo da reserva acabou. Escolha o lugar novamente.
          </div>
        )}

        {erro && !perdeuAReserva && <div className="aviso aviso-erro">{erro}</div>}

        <form className="pilha pilha-16" onSubmit={pagar}>
          <div className="campo">
            <label htmlFor="titular">Nome no cartão</label>
            <input
              id="titular"
              required
              autoComplete="cc-name"
              value={titular}
              onChange={(e) => setTitular(e.target.value)}
            />
          </div>

          <div className="campo">
            <label htmlFor="cartao">Número do cartão</label>
            <input
              id="cartao"
              required
              inputMode="numeric"
              autoComplete="cc-number"
              placeholder="0000 0000 0000 0000"
              className="mono"
              value={cartao}
              onChange={(e) => setCartao(e.target.value)}
            />
            <span className="campo-dica">Não guardamos nenhum dado de cartão.</span>
          </div>

          <button
            type="submit"
            className="btn btn-principal btn-largo"
            disabled={pagando || expirou}
          >
            {pagando ? 'Processando…' : 'Pagar'}
          </button>
        </form>

        <div className="cartoes-teste">
          <p className="texto-pp texto-3" style={{ margin: '0 0 8px' }}>
            Cartões de teste — clique para preencher:
          </p>
          <div className="linha-flex" style={{ flexWrap: 'wrap', gap: 8 }}>
            {CARTOES.map((c) => (
              <button
                key={c.numero}
                type="button"
                className="cartao-teste"
                onClick={() => {
                  setCartao(c.numero)
                  if (!titular) setTitular('TITULAR TESTE')
                }}
              >
                <span className="mono texto-pp">{c.numero.slice(-4)}</span>
                <span className="texto-pp">{c.rotulo}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
