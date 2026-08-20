"""Dependências de autenticação e autorização.

O session_id chega por cookie httponly (caminho normal do navegador) ou pelo
header `Authorization: Bearer <session_id>` (útil para testes e curl). O cookie
é o preferido: httponly tira o token do alcance de JavaScript, o que neutraliza
roubo de sessão por XSS — vantagem que um JWT em localStorage não tem.
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import Forbidden, NotAuthenticated
from app.models.enums import Role
from app.services import session_store
from app.services.session_store import SessionData

DbSession = Annotated[Session, Depends(get_db)]


def _extract_session_id(request: Request) -> str | None:
    cookie = request.cookies.get(settings.session_cookie_name)
    if cookie:
        return cookie

    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()

    return None


def current_session(request: Request) -> SessionData:
    """Sessão válida, ou 401."""
    session_id = _extract_session_id(request)
    if not session_id:
        raise NotAuthenticated()

    data = session_store.get(session_id)
    if data is None:
        raise NotAuthenticated()

    return data


CurrentSession = Annotated[SessionData, Depends(current_session)]


def require_role(*allowed: Role):
    """Fábrica de guarda por papel.

    Os três papéis do PDF são de fato disjuntos — organizador não compra,
    cliente não valida — então a checagem é lista branca explícita por rota,
    não hierarquia de permissão.
    """

    def guard(session: CurrentSession) -> SessionData:
        if session.role not in allowed:
            raise Forbidden(
                f"Esta ação exige o papel: {', '.join(str(r) for r in allowed)}."
            )
        return session

    return guard


RequireOrganizer = Annotated[SessionData, Depends(require_role(Role.ORGANIZER))]
RequireCustomer = Annotated[SessionData, Depends(require_role(Role.CUSTOMER))]
RequireGate = Annotated[SessionData, Depends(require_role(Role.GATE))]
