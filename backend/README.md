# Back-end — FastAPI

Estrutura planejada (ver README na raiz):

```
app/
  main.py            # bootstrap do FastAPI
  config.py          # settings via pydantic-settings
  db.py              # engine e sessão SQLAlchemy
  models/            # entidades
  api/               # rotas + schemas Pydantic
  services/          # regras de domínio (reserva, pagamento, ingresso, portaria)
  repositories/      # acesso a dados
  providers/         # clientes TMDb e Ticketmaster + fixtures offline
  seed.py            # dados de teste
alembic/             # migrations
tests/
```
