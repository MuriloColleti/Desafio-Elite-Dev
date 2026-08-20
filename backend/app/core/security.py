"""Primitivas de segurança: hash de senha, token de sessão, HMAC do ingresso.

Três mecanismos distintos, de propósito, porque os três problemas são
diferentes:

- **Senha** → Argon2id. Precisa ser lenta e irreversível.
- **session_id** → token aleatório opaco. Não carrega dado, então não há o que
  assinar; a segurança vem de ser imprevisível e de o servidor ser a única
  fonte de verdade sobre ele.
- **Código do QR** → HMAC-SHA256. O código viaja fora do nosso controle e
  precisa ser verificável por assinatura, sem consulta.
"""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()


# --- Senha ---


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


# --- Sessão ---


def new_session_id() -> str:
    """256 bits de entropia, URL-safe.

    Opaco de propósito: o front recebe isto e nada mais. Não é um JWT nem
    contém um — se contivesse, o cliente poderia ler os claims e o token
    valeria mesmo depois de revogado, que é exatamente o que queremos evitar.
    """
    return secrets.token_urlsafe(32)


# --- Código do ingresso ---


def sign_ticket_code(ticket_id: str) -> str:
    """Devolve `<ticket_id>.<hmac>`, o conteúdo do QR.

    Curto o suficiente para virar um QR de baixa densidade, que é o que permite
    ler com câmera de celular em porta de cinema.
    """
    mac = hmac.new(
        settings.ticket_hmac_secret.encode(),
        ticket_id.encode(),
        hashlib.sha256,
    ).hexdigest()[:32]
    return f"{ticket_id}.{mac}"


def verify_ticket_code(code: str) -> str | None:
    """Valida o HMAC e devolve o ticket_id, ou None se o código não confere."""
    if "." not in code:
        return None
    ticket_id, _, mac = code.rpartition(".")
    if not ticket_id or not mac:
        return None
    expected = sign_ticket_code(ticket_id).rpartition(".")[2]
    # compare_digest: comparação em tempo constante, para não vazar o prefixo
    # correto do MAC por diferença de tempo de resposta.
    return ticket_id if hmac.compare_digest(mac, expected) else None
