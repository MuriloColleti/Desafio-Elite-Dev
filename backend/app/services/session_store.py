"""Sessões em Redis, endereçadas por um session_id opaco.

## Como funciona

O front recebe **apenas** um `session_id`: 256 bits aleatórios, sem estrutura e
sem significado. Todo o estado da sessão (quem é, qual papel, quando expira)
fica no Redis, sob a chave `session:<id>`. Para o front o session_id ocupa o
lugar que um JWT ocuparia — é o que ele guarda e reenvia — mas as propriedades
são opostas.

## Por que não um JWT (nem um JWT guardado aqui dentro)

Um JWT é autocontido: quem tem o token tem os claims, e o servidor não
consegue invalidá-lo antes de expirar. Isso troca uma consulta por três
problemas — logout que não desloga, mudança de papel que só vale no próximo
login, e claims legíveis por qualquer um que intercepte o token.

Com token opaco o servidor é a única fonte de verdade: `DEL session:<id>`
encerra a sessão naquele instante. E como o token não carrega nada, não há o
que assinar nem o que vazar.

Vale registrar o que **não** fazemos: guardar um JWT dentro do Redis e devolver
esse JWT ao front. Isso anularia o ganho — o cliente voltaria a ter um token
autocontido, decodificável e não-revogável, e o Redis seria só um armário
inútil no caminho. O JWT não existe em lugar nenhum deste fluxo.

## Expiração dupla

Duas janelas, porque resolvem coisas diferentes:

- **Inatividade** (`session_ttl_seconds`): renovada a cada request. Quem parou
  de usar perde a sessão.
- **Absoluta** (`session_absolute_ttl_seconds`): nunca renovada. Impede que uma
  sessão viva para sempre só porque alguém mantém uma aba aberta — que é o
  cenário em que um token roubado valeria indefinidamente.
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import redis

from app.core.config import settings
from app.core.redis_client import client
from app.core.security import new_session_id
from app.models.enums import Role

_PREFIX = "session:"
_USER_INDEX_PREFIX = "user_sessions:"


@dataclass(slots=True)
class SessionData:
    """O que guardamos no Redis. Mínimo necessário para autorizar um request.

    Não guardamos nome nem e-mail: são dados que mudam e que o front busca em
    /auth/me. Sessão guarda identidade e permissão, não perfil.
    """

    user_id: str
    role: Role
    created_at: str  # ISO 8601, para calcular a expiração absoluta
    gate_event_id: str | None = None

    def to_json(self) -> str:
        data = asdict(self)
        data["role"] = str(self.role)
        return json.dumps(data)

    @classmethod
    def from_json(cls, raw: str) -> "SessionData":
        data = json.loads(raw)
        return cls(
            user_id=data["user_id"],
            role=Role(data["role"]),
            created_at=data["created_at"],
            gate_event_id=data.get("gate_event_id"),
        )

    @property
    def age_seconds(self) -> float:
        created = datetime.fromisoformat(self.created_at)
        return (datetime.now(UTC) - created).total_seconds()


def create(user_id: str, role: Role, gate_event_id: str | None = None) -> str:
    """Abre uma sessão e devolve o session_id opaco."""
    session_id = new_session_id()
    data = SessionData(
        user_id=user_id,
        role=role,
        created_at=datetime.now(UTC).isoformat(),
        gate_event_id=gate_event_id,
    )

    pipe = client.pipeline()
    pipe.set(_PREFIX + session_id, data.to_json(), ex=settings.session_ttl_seconds)
    # Índice reverso: permite revogar todas as sessões de um usuário de uma vez
    # (troca de senha, mudança de papel). Sem ele seria preciso varrer o Redis.
    pipe.sadd(_USER_INDEX_PREFIX + user_id, session_id)
    pipe.expire(_USER_INDEX_PREFIX + user_id, settings.session_absolute_ttl_seconds)
    pipe.execute()

    return session_id


def get(session_id: str) -> SessionData | None:
    """Lê a sessão e renova a janela de inatividade.

    Devolve None se não existe, expirou, ou passou do limite absoluto.
    """
    if not session_id:
        return None

    key = _PREFIX + session_id
    try:
        raw = client.get(key)
    except redis.RedisError:
        # Redis fora do ar não deve virar 500: para o usuário é "sessão
        # inválida", e o /health é que diz que a infra está com problema.
        return None

    if raw is None:
        return None

    try:
        data = SessionData.from_json(raw)
    except (json.JSONDecodeError, KeyError, ValueError):
        client.delete(key)  # payload corrompido: descarta
        return None

    # Teto absoluto: não renovável, por definição.
    if data.age_seconds > settings.session_absolute_ttl_seconds:
        destroy(session_id)
        return None

    # Sliding window: cada uso empurra a expiração por inatividade.
    client.expire(key, settings.session_ttl_seconds)
    return data


def destroy(session_id: str) -> None:
    """Logout. Efeito imediato — é o que um JWT não permite."""
    key = _PREFIX + session_id
    raw = client.get(key)
    if raw:
        try:
            data = SessionData.from_json(raw)
            client.srem(_USER_INDEX_PREFIX + data.user_id, session_id)
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    client.delete(key)


def destroy_all_for_user(user_id: str) -> int:
    """Encerra todas as sessões de um usuário. Devolve quantas caíram."""
    index_key = _USER_INDEX_PREFIX + user_id
    session_ids = client.smembers(index_key)
    if not session_ids:
        return 0

    pipe = client.pipeline()
    for sid in session_ids:
        pipe.delete(_PREFIX + sid)
    pipe.delete(index_key)
    pipe.execute()
    return len(session_ids)
