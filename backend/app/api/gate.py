"""Rota da portaria: validação do ingresso na entrada."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import DbSession, RequireGate
from app.models.enums import GateResult
from app.services import tickets

router = APIRouter(prefix="/gate", tags=["gate"])


class GateRequest(BaseModel):
    # Vem da câmera ou da digitação manual — o back não distingue, e não
    # precisa: o código é o mesmo nos dois caminhos.
    code: str = Field(min_length=1, max_length=200)


class GateResponse(BaseModel):
    """Resposta da validação.

    Os quatro resultados voltam com **200**, inclusive as três recusas: a
    portaria precisa exibir o motivo na tela, e tratar "já utilizado" como erro
    de requisição faria o front cair no caminho de falha genérica em vez de
    mostrar quando o ingresso foi usado.
    """

    result: GateResult
    message: str

    # Preenchidos quando o ingresso existe, para a tela dar contexto a quem
    # está na porta: qual evento, qual assento, quando foi usado.
    event_title: str | None = None
    holder_name: str | None = None
    seat_label: str | None = None
    quantity: int | None = None
    used_at: datetime | None = None


_MENSAGENS = {
    GateResult.VALID: "Ingresso válido. Entrada liberada.",
    GateResult.INVALID: "Ingresso inválido.",
    GateResult.ALREADY_USED: "Este ingresso já foi utilizado.",
    GateResult.WRONG_EVENT: "Este ingresso é de outro evento.",
}


@router.post("/validate", response_model=GateResponse)
def validar(payload: GateRequest, session: RequireGate, db: DbSession) -> GateResponse:
    """Valida o código lido na entrada.

    Marcar como usado é atômico: dois scanners na mesma porta lendo o mesmo QR
    no mesmo instante, e só um recebe `VALID`.
    """
    resultado, ingresso = tickets.validar(
        db,
        codigo_lido=payload.code,
        gate_user_id=session.user_id,
        gate_event_id=session.gate_event_id,
    )

    resposta = GateResponse(result=resultado, message=_MENSAGENS[resultado])

    if ingresso is not None:
        resposta.event_title = ingresso.reservation.event.title
        resposta.holder_name = ingresso.reservation.customer.name
        resposta.seat_label = ingresso.reservation.seat_label
        resposta.quantity = ingresso.reservation.quantity
        resposta.used_at = ingresso.used_at

    return resposta
