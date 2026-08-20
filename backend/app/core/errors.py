"""Erros de domínio e o formato único de resposta de erro.

O front reage por `code`, nunca por texto — mensagem é para humano, código é
para máquina. Por isso todo erro sai como:

    {"error": {"code": "SEAT_TAKEN", "message": "..."}}
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base de todo erro esperado da aplicação."""

    code = "INTERNAL_ERROR"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Erro inesperado."

    def __init__(self, message: str | None = None, **extra: object) -> None:
        self.message = message or self.message
        self.extra = extra
        super().__init__(self.message)

    def to_response(self) -> JSONResponse:
        payload: dict[str, object] = {"code": self.code, "message": self.message}
        if self.extra:
            payload.update(self.extra)
        return JSONResponse(status_code=self.status_code, content={"error": payload})


# --- Autenticação e autorização ---


class InvalidCredentials(AppError):
    code = "INVALID_CREDENTIALS"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "E-mail ou senha incorretos."


class NotAuthenticated(AppError):
    code = "NOT_AUTHENTICATED"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Sessão ausente ou expirada."


class Forbidden(AppError):
    code = "FORBIDDEN"
    status_code = status.HTTP_403_FORBIDDEN
    message = "Seu papel não permite esta ação."


# --- Genéricos ---


class NotFound(AppError):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Recurso não encontrado."


class ValidationFailed(AppError):
    code = "VALIDATION_FAILED"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "Dados inválidos."


# --- Reserva e pagamento ---


class SeatTaken(AppError):
    """Perdeu a corrida pelo assento — a constraint do banco decidiu."""

    code = "SEAT_TAKEN"
    status_code = status.HTTP_409_CONFLICT
    message = "Este lugar acabou de ser reservado por outra pessoa."


class SoldOut(AppError):
    code = "SOLD_OUT"
    status_code = status.HTTP_409_CONFLICT
    message = "Não há mais ingressos disponíveis para este evento."


class ReservationExpired(AppError):
    code = "RESERVATION_EXPIRED"
    status_code = status.HTTP_410_GONE
    message = "O tempo para concluir a reserva expirou."


class PaymentDeclined(AppError):
    code = "PAYMENT_DECLINED"
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    message = "Pagamento recusado."


# --- Portaria ---
#
# Os quatro estados que o PDF pede não são todos "erro": `válido` é sucesso e
# volta como 200. Os outros três viram resposta de negócio, também 200, porque
# a portaria precisa exibir o motivo — não tratar como falha de request.


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return exc.to_response()


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Erro inesperado."}},
    )
