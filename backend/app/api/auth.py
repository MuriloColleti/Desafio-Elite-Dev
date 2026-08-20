"""Rotas de autenticação: registro, login, logout, quem sou eu.

O login devolve o session_id de duas formas: cookie httponly (o que o front
usa) e no corpo da resposta (para curl e testes). O corpo é conveniência de
desenvolvimento; em produção com HTTPS o cookie é o que importa.
"""

from fastapi import APIRouter, Response
from typing import Literal

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from app.api.deps import CurrentSession, DbSession
from app.core.config import settings
from app.core.errors import EmailInUse, InvalidCredentials, ValidationFailed
from app.core.security import hash_password, verify_password
from app.models.entities import User
from app.models.enums import Role
from app.services import session_store

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    # 8 caracteres é o mínimo que ainda vale exigir. Não pedimos símbolo nem
    # maiúscula: regra de composição empurra as pessoas para senha previsível
    # com um "!" no fim, e o Argon2 já protege o armazenamento.
    password: str = Field(min_length=8, max_length=128)
    # Portaria fica de fora de propósito: é conta operacional da casa de
    # espetáculo, não algo que se cria numa tela pública. Quem pudesse se
    # cadastrar como portaria validaria ingressos de eventos alheios.
    role: Literal[Role.CUSTOMER, Role.ORGANIZER] = Role.CUSTOMER


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    session_id: str
    user_id: str
    name: str
    role: Role
    gate_event_id: str | None = None


class MeResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: Role
    gate_event_id: str | None = None


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,  # invisível para JavaScript: XSS não rouba a sessão
        secure=settings.session_cookie_secure,  # True em produção
        # Cross-site exige "none"; ver comentário em Settings.
        samesite=settings.session_cookie_samesite,  # type: ignore[arg-type]
        path="/",
    )


@router.post("/register", response_model=LoginResponse, status_code=201)
def registrar(payload: RegisterRequest, response: Response, db: DbSession) -> LoginResponse:
    """Cria a conta e **já abre a sessão**.

    Cadastrar e depois pedir para entrar de novo é um passo sem propósito: a
    pessoa acabou de provar quem é ao definir a senha.
    """
    email = payload.email.lower().strip()

    # Comparação case-insensitive: "Ana@x.com" e "ana@x.com" são a mesma conta,
    # e sem isso o banco aceitaria as duas (o UNIQUE é sensível a caixa).
    existente = db.scalar(select(User).where(func.lower(User.email) == email))
    if existente is not None:
        raise EmailInUse()

    nome = payload.name.strip()
    if not nome:
        raise ValidationFailed("Informe seu nome.")

    usuario = User(
        name=nome,
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    session_id = session_store.create(user_id=usuario.id, role=usuario.role)
    _set_session_cookie(response, session_id)

    return LoginResponse(
        session_id=session_id,
        user_id=usuario.id,
        name=usuario.name,
        role=usuario.role,
        gate_event_id=None,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: DbSession) -> LoginResponse:
    user = db.scalar(
        select(User).where(func.lower(User.email) == payload.email.lower().strip())
    )

    # Mesma resposta para e-mail inexistente e senha errada: não confirmamos
    # quais e-mails têm conta.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise InvalidCredentials()

    session_id = session_store.create(
        user_id=user.id,
        role=user.role,
        gate_event_id=user.gate_event_id,
    )
    _set_session_cookie(response, session_id)

    return LoginResponse(
        session_id=session_id,
        user_id=user.id,
        name=user.name,
        role=user.role,
        gate_event_id=user.gate_event_id,
    )


@router.post("/logout", status_code=204)
def logout(request_session: CurrentSession, response: Response) -> None:
    """Encerra a sessão no servidor — não só no cliente.

    É a diferença prática do token opaco: aqui o token deixa de valer neste
    instante, mesmo que alguém já o tenha copiado.
    """
    # O session_id não vem em SessionData (ela guarda o conteúdo, não a chave),
    # então revogamos todas as sessões do usuário. Para este escopo é o
    # comportamento desejado de qualquer forma: logout que desloga de tudo.
    session_store.destroy_all_for_user(request_session.user_id)
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=MeResponse)
def me(session: CurrentSession, db: DbSession) -> MeResponse:
    """Perfil do usuário atual.

    Buscamos no banco em vez de devolver o que está na sessão: nome e e-mail
    mudam, e a sessão guarda identidade e permissão, não perfil.
    """
    user = db.get(User, session.user_id)
    if user is None:
        # Usuário removido com sessão viva: limpa o rastro.
        session_store.destroy_all_for_user(session.user_id)
        raise InvalidCredentials("Usuário não encontrado.")

    return MeResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        gate_event_id=user.gate_event_id,
    )
