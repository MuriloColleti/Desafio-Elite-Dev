"""Testes da sessão opaca em Redis.

O que se prova aqui é a propriedade que motivou a escolha do desenho: o token
não carrega informação, e o servidor pode invalidá-lo a qualquer momento — as
duas coisas que um JWT não oferece.
"""

import json

import pytest

from app.core.config import settings
from app.models.enums import Role
from app.services import session_store


def test_cria_sessao_e_le_de_volta(redis_fake):
    sid = session_store.create("user-1", Role.CUSTOMER)

    data = session_store.get(sid)
    assert data is not None
    assert data.user_id == "user-1"
    assert data.role is Role.CUSTOMER


def test_session_id_e_opaco(redis_fake):
    """O token não pode conter nada sobre o usuário.

    Este é o ponto central: um JWT carregaria user_id e role em base64,
    legíveis por qualquer um. O session_id não pode revelar nem o id.
    """
    sid = session_store.create("user-cliente-42", Role.ORGANIZER)

    assert "user-cliente-42" not in sid
    assert "ORGANIZER" not in sid
    # Nem é decodificável como JWT (que teria três partes separadas por ponto).
    assert sid.count(".") == 0

    # E é longo o bastante para não ser adivinhável por força bruta.
    assert len(sid) >= 40


def test_dados_ficam_no_servidor_nao_no_token(redis_fake):
    """O estado mora no Redis, sob a chave da sessão."""
    sid = session_store.create("user-7", Role.GATE, gate_event_id="evt-1")

    raw = redis_fake.get(f"session:{sid}")
    assert raw is not None
    stored = json.loads(raw)
    assert stored["user_id"] == "user-7"
    assert stored["role"] == "GATE"
    assert stored["gate_event_id"] == "evt-1"


def test_logout_invalida_na_hora(redis_fake):
    """Revogação imediata — o que um JWT não permite antes de expirar."""
    sid = session_store.create("user-2", Role.CUSTOMER)
    assert session_store.get(sid) is not None

    session_store.destroy(sid)

    assert session_store.get(sid) is None


def test_revoga_todas_as_sessoes_do_usuario(redis_fake):
    """Login em três dispositivos, revogação de todos de uma vez."""
    sids = [session_store.create("user-3", Role.CUSTOMER) for _ in range(3)]
    assert all(session_store.get(s) is not None for s in sids)

    caidas = session_store.destroy_all_for_user("user-3")

    assert caidas == 3
    assert all(session_store.get(s) is None for s in sids)


def test_sessao_inexistente_devolve_none(redis_fake):
    assert session_store.get("nao-existe") is None
    assert session_store.get("") is None


def test_ttl_e_renovado_a_cada_uso(redis_fake):
    """Janela deslizante: usar a sessão empurra a expiração por inatividade."""
    sid = session_store.create("user-4", Role.CUSTOMER)

    # Encurta o TTL artificialmente para observar a renovação.
    redis_fake.expire(f"session:{sid}", 10)
    assert redis_fake.ttl(f"session:{sid}") <= 10

    session_store.get(sid)

    assert redis_fake.ttl(f"session:{sid}") > 10


def test_expiracao_absoluta_nao_e_renovavel(redis_fake, monkeypatch):
    """Sessão antiga morre mesmo com uso contínuo.

    Sem este teto, uma aba aberta indefinidamente manteria a sessão viva para
    sempre — e um token roubado valeria para sempre junto.
    """
    sid = session_store.create("user-5", Role.CUSTOMER)

    # Reescreve a sessão como se tivesse nascido muito tempo atrás.
    raw = json.loads(redis_fake.get(f"session:{sid}"))
    raw["created_at"] = "2020-01-01T00:00:00+00:00"
    redis_fake.set(f"session:{sid}", json.dumps(raw))

    assert session_store.get(sid) is None
    # E foi limpa, não só rejeitada.
    assert redis_fake.get(f"session:{sid}") is None


def test_payload_corrompido_e_descartado(redis_fake):
    sid = session_store.create("user-6", Role.CUSTOMER)
    redis_fake.set(f"session:{sid}", "isto-nao-e-json")

    assert session_store.get(sid) is None
    assert redis_fake.get(f"session:{sid}") is None


def test_tokens_sao_unicos(redis_fake):
    sids = {session_store.create("user-8", Role.CUSTOMER) for _ in range(50)}
    assert len(sids) == 50
