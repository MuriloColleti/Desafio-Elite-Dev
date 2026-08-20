/**
 * Portaria — validação na entrada.
 *
 * A tela é pensada para quem está de pé na porta, com fila esperando: o
 * resultado ocupa a tela inteira, com cor e ícone, para ser lido de relance a
 * um braço de distância. Nada de mensagem discreta.
 *
 * Câmera é o caminho principal; digitação manual é a alternativa que o
 * enunciado exige — e a que funciona quando o navegador nega a câmera ou o
 * acesso não é por HTTPS.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import { useSessao } from '../auth/Sessao'
import { ApiError, api } from '../lib/api'
import { dataHoraLonga, mensagemDeErro } from '../lib/formato'
import type { RespostaPortaria, ResultadoPortaria } from '../lib/tipos'

const APARENCIA: Record<ResultadoPortaria, { classe: string; icone: string; titulo: string }> = {
  VALID: { classe: 'valido', icone: '✓', titulo: 'Entrada liberada' },
  ALREADY_USED: { classe: 'usado', icone: '!', titulo: 'Já utilizado' },
  WRONG_EVENT: { classe: 'errado', icone: '⤫', titulo: 'Evento errado' },
  INVALID: { classe: 'invalido', icone: '✕', titulo: 'Ingresso inválido' },
}

export function Portaria() {
  const { usuario } = useSessao()
  const [codigo, setCodigo] = useState('')
  const [resposta, setResposta] = useState<RespostaPortaria | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [validando, setValidando] = useState(false)
  const [camera, setCamera] = useState(false)
  const [erroCamera, setErroCamera] = useState<string | null>(null)

  const leitorRef = useRef<{ stop: () => Promise<void> } | null>(null)
  const ultimoLido = useRef<string>('')

  const validar = useCallback(async (valor: string) => {
    const limpo = valor.trim()
    if (!limpo) return

    setValidando(true)
    setErro(null)

    try {
      const r = await api.post<RespostaPortaria>('/gate/validate', { code: limpo })
      setResposta(r)
      setCodigo('')
    } catch (e) {
      setResposta(null)
      setErro(
        e instanceof ApiError ? mensagemDeErro(e.code, e.message) : 'Não foi possível validar.',
      )
    } finally {
      setValidando(false)
    }
  }, [])

  // A câmera é carregada só quando ligada: `html5-qrcode` puxa bastante código,
  // e a portaria pode operar inteira pela digitação manual.
  useEffect(() => {
    if (!camera) return

    let cancelado = false

    async function iniciar() {
      try {
        const { Html5Qrcode } = await import('html5-qrcode')
        if (cancelado) return

        const leitor = new Html5Qrcode('leitor-qr')
        leitorRef.current = leitor

        await leitor.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 240, height: 240 } },
          (texto) => {
            // A câmera dispara várias leituras do mesmo QR por segundo.
            // Sem este bloqueio, uma leitura marcaria como usado e as
            // seguintes responderiam "já utilizado" na cara do operador.
            if (texto === ultimoLido.current) return
            ultimoLido.current = texto
            void validar(texto)
            setTimeout(() => {
              ultimoLido.current = ''
            }, 3000)
          },
          () => {
            /* quadro sem QR: silencioso, acontece a cada frame */
          },
        )
      } catch {
        if (!cancelado) {
          setErroCamera(
            'Não foi possível abrir a câmera. Isso acontece se o acesso não for por HTTPS ou ' +
              'localhost, ou se a permissão foi negada. Use a digitação manual abaixo.',
          )
          setCamera(false)
        }
      }
    }

    void iniciar()

    return () => {
      cancelado = true
      leitorRef.current?.stop().catch(() => undefined)
      leitorRef.current = null
    }
  }, [camera, validar])

  const aparencia = resposta ? APARENCIA[resposta.result] : null

  return (
    <div className="portaria">
      <div className="pilha pilha-8">
        <h1>Portaria</h1>
        <p className="texto-medio texto-p" style={{ margin: 0 }}>
          {usuario?.gate_event_id
            ? 'Valide os ingressos da entrada deste evento.'
            : 'Esta portaria não está vinculada a um evento; qualquer ingresso legítimo será aceito.'}
        </p>
      </div>

      {/* Resultado em destaque: é o que o operador olha, não o formulário. */}
      {aparencia && resposta && (
        <div className={`resultado ${aparencia.classe}`} role="status" aria-live="assertive">
          <span className="resultado-icone" aria-hidden="true">
            {aparencia.icone}
          </span>
          <strong className="resultado-titulo">{aparencia.titulo}</strong>
          <p className="resultado-msg">{resposta.message}</p>

          {(resposta.holder_name || resposta.event_title) && (
            <dl className="resultado-dados">
              {resposta.holder_name && (
                <div>
                  <dt>Titular</dt>
                  <dd>{resposta.holder_name}</dd>
                </div>
              )}
              {resposta.event_title && (
                <div>
                  <dt>Evento</dt>
                  <dd>{resposta.event_title}</dd>
                </div>
              )}
              {resposta.seat_label && (
                <div>
                  <dt>Assento</dt>
                  <dd>{resposta.seat_label}</dd>
                </div>
              )}
              {!resposta.seat_label && resposta.quantity && (
                <div>
                  <dt>Ingressos</dt>
                  <dd>{resposta.quantity}</dd>
                </div>
              )}
              {resposta.used_at && (
                <div>
                  <dt>Utilizado em</dt>
                  <dd>{dataHoraLonga(resposta.used_at)}</dd>
                </div>
              )}
            </dl>
          )}

          <button
            type="button"
            className="btn btn-secundario"
            onClick={() => {
              setResposta(null)
              ultimoLido.current = ''
            }}
          >
            Validar o próximo
          </button>
        </div>
      )}

      {!resposta && (
        <div className="pilha pilha-24">
          {erro && <div className="aviso aviso-erro">{erro}</div>}
          {erroCamera && <div className="aviso aviso-alerta">{erroCamera}</div>}

          <div className="leitor-area">
            {camera ? (
              <>
                <div id="leitor-qr" className="leitor-video" />
                <button
                  type="button"
                  className="btn btn-secundario"
                  onClick={() => setCamera(false)}
                >
                  Desligar câmera
                </button>
              </>
            ) : (
              <button
                type="button"
                className="btn btn-principal btn-largo"
                onClick={() => {
                  setErroCamera(null)
                  setCamera(true)
                }}
              >
                Ler QR com a câmera
              </button>
            )}
          </div>

          <div className="separador-ou">
            <span>ou digite o código</span>
          </div>

          <form
            className="pilha pilha-16"
            onSubmit={(e) => {
              e.preventDefault()
              void validar(codigo)
            }}
          >
            <div className="campo">
              <label htmlFor="codigo">Código do ingresso</label>
              <input
                id="codigo"
                className="mono"
                placeholder="cole ou digite o código"
                value={codigo}
                onChange={(e) => setCodigo(e.target.value)}
                autoComplete="off"
              />
            </div>
            <button
              type="submit"
              className="btn btn-secundario btn-largo"
              disabled={validando || !codigo.trim()}
            >
              {validando ? 'Validando…' : 'Validar'}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
