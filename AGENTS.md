# Palco — Guia para Agentes de IA e Desenvolvedores

Plataforma de eventos e ingressos: o organizador publica eventos a partir de um catálogo externo
(TMDb, Ticketmaster), o cliente reserva lugar e paga de forma simulada, e a portaria valida o
ingresso na entrada por QR. Entrega do **Desafio Elite Dev (Verzel)**.

Este arquivo é a fonte única de convenções do projeto. Leia antes de escrever qualquer código.
O **README.md** é a documentação voltada ao avaliador (setup, decisões, status); este arquivo é a
regra para quem escreve código.

---

## 1. Premissas globais (inegociáveis)

1. **Idioma:** comunicação, documentação e nomes de domínio em **português do Brasil**. Código
   (identificadores) em inglês; mensagens e labels de usuário em pt-BR.
2. **Qualidade:** todo código é nível **arquiteto sênior** — **SOLID, SRP, DRY, DI, Clean Code**.
   Sem exceção.
3. **Sem "AI smell":** proibido comentário óbvio que só repete o código, código morto, `print`/
   `console.log` de debug esquecido, ou qualquer marca de geração automática. Comentário só quando
   expressa uma restrição que o código não mostra — **por que**, não *o que*.
4. **Commits:** mensagens naturais de desenvolvedor humano. **Nunca** citar IA/Claude/assistente,
   nem `Co-Authored-By` de IA, nem emojis de robô, nem "generated with". Formato:
   `tipo(escopo): descrição` (Conventional Commits), imperativo, em pt-BR.
5. **Divulgação de IA é no README, não no histórico.** O enunciado do desafio pede explicitamente
   que se conte quais ferramentas de IA foram usadas e em quais partes — e isso pontua. Essa
   divulgação vive na seção *Uso de IA* do `README.md`. A premissa 4 continua valendo para
   mensagens de commit: as duas coisas não se contradizem, apenas moram em lugares diferentes.

---

## 2. Contexto do desafio (restrições que vêm de fora)

Regras do enunciado que não são escolha nossa e não devem ser "melhoradas" sem necessidade:

- **Três papéis distintos:** `ORGANIZER` (cria e gerencia eventos), `CUSTOMER` (reserva, paga,
  recebe ingresso), `GATE` (valida na entrada). São disjuntos.
- **Portaria responde quatro estados:** válido, inválido, já utilizado, evento errado. Cada um tem
  causa distinta e precisa ser distinguível na tela.
- **Pagamento é simulado**, contemplando aprovação **e recusa**. Sem transação financeira real.
- **O mesmo lugar não pode ser vendido duas vezes**, e o mesmo ingresso não pode ser validado
  duas vezes.
- **O QR não pode ser forjável.**
- **Dados semeados obrigatórios:** um organizador, dois clientes, um usuário de portaria e ao
  menos um evento publicado com ingressos disponíveis.
- **README é avaliado.** O que não funciona precisa estar dito lá; ausência de explicação reduz a
  nota. A tabela *Status de implementação* é a fonte de verdade e deve refletir a realidade a cada
  commit.
- **Escopo fechado:** não fazer nota fiscal, revenda entre usuários, app nativo, recuperação de
  senha ou envio de ingresso por e-mail.

---

## 3. Arquitetura

Front-end React/Vite separado + back-end **FastAPI em camadas** (um app, um deploy).

```
Browser → frontend (React + Vite :5173)
            → backend (FastAPI :8000)
               app/
                 main.py          bootstrap, CORS, handlers de erro, /health
                 core/            config (Pydantic Settings), db, redis, security, errors
                 api/             rotas + schemas Pydantic + deps (guardas de papel)
                 services/        regra de negócio (reserva, pagamento, ingresso, portaria)
                 repositories/    acesso a dados via SQLAlchemy
                 providers/       clientes TMDb e Ticketmaster + fixtures offline
                 models/          entidades e enums
                 seed.py          dados de teste
               alembic/           migrations
               tests/
Infra: PostgreSQL 16 (schema único via Alembic) · Redis 7 (sessão + cache de catálogo)
```

**Raiz só orquestra.** `backend/` e `frontend/` são autônomos — cada um com seu próprio gerenciador
de dependências, `.env.example` e (quando houver) `Dockerfile`. A instalação roda **dentro** de cada
pasta. A raiz guarda `docker-compose.yml`, `docs/`, o PDF do enunciado e este guia.

---

## 4. Stack

- **Front:** React 18, TypeScript estrito, Vite, React Router, `html5-qrcode` (leitura do QR).
- **Back:** Python 3.12+, FastAPI, Pydantic v2 + pydantic-settings, SQLAlchemy 2.0, Alembic,
  `psycopg` 3, `redis`, `argon2-cffi`, `httpx`, `qrcode`.
- **Infra:** PostgreSQL 16, Redis 7, Docker Compose.

Versões exatas e verificadas em `backend/requirements.txt`. Não bumpar pin sem rodar a suíte.

---

## 5. Comandos

**Com Docker:**

```bash
docker compose up --build                        # db + redis + api + web
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
```

**Sem Docker:**

```bash
# infra
docker run -d --name palco-pg -e POSTGRES_USER=palco -e POSTGRES_PASSWORD=palco \
  -e POSTGRES_DB=palco -p 5432:5432 postgres:16-alpine
docker run -d --name palco-redis -p 6379:6379 redis:7-alpine

# backend  :8000
cd backend && python -m venv .venv && .venv/Scripts/Activate.ps1   # Windows
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload --port 8000

# frontend :5173
cd frontend && npm install && npm run dev
```

**Testes:** `cd backend && pytest`. Os testes de concorrência exigem Postgres real via
`TEST_DATABASE_URL` — sem ela são **pulados**, nunca aprovados em silêncio. Ver seção 9.

---

## 6. Decisões de arquitetura firmadas (seguir sempre)

O *porquê* de cada uma está no `README.md`; aqui fica a regra a obedecer.

- **Separação back/front rígida.** O front não guarda token autocontido, não decodifica claims e
  não mantém dado de permissão em `localStorage`. Toda autorização é decidida no backend.
- **Sessão server-side (reference token).** O cliente guarda apenas um **`session_id` opaco** —
  256 bits aleatórios, sem estrutura — em cookie `HttpOnly` + `SameSite=Lax` (+ `Secure` em
  produção). O estado da sessão vive no Redis sob `session:<id>`.
  **Não existe JWT em nenhum ponto do fluxo de autenticação** — nem no cliente, nem guardado
  dentro do Redis: um JWT devolvido ao front seria autocontido e não-revogável, anulando o ganho.
- **Duas janelas de expiração de sessão:** inatividade renovável a cada request
  (`SESSION_TTL_SECONDS`) e teto absoluto **não** renovável (`SESSION_ABSOLUTE_TTL_SECONDS`).
- **Assento único é garantido pelo banco, não pelo código.** Índice `UNIQUE` parcial
  (`uq_seat_active`) sobre reservas em `PENDING`/`PAID` com `seat_label` não nulo. Proibido
  resolver disputa de assento com checagem prévia em Python ou lock de aplicação.
- **Hold de assento mora no Postgres, não no Redis.** É estado que não pode se perder e pertence à
  mesma transação que garante o assento. Redis guarda só o que é descartável (sessão, cache).
- **Expiração de hold é avaliada na leitura** (`expires_at < now()` conta como livre). Proibido
  depender de job de background para o estoque ficar correto.
- **`Event` é entidade nossa, desacoplada do catálogo externo.** Referencia `catalog_ref`
  (`tmdb:movie:550`) e guarda snapshot de título/pôster/sinopse. A vitrine nunca depende de a API
  externa estar de pé.
- **Provedores externos entram por interface única** (`CatalogProvider` → `CatalogItem`
  normalizado). O resto da aplicação não sabe a origem do item.
- **Código do ingresso é `<ticket_id>.<hmac>`** (HMAC-SHA256). Curto de propósito: QR de baixa
  densidade é legível por câmera de celular. Proibido JWT no QR.
- **Link de compartilhamento é token opaco separado** do código de validação, e dá acesso
  **somente leitura**. Compartilhar não transfere o ingresso.

---

## 7. Convenções de código

- **Camadas:** rota (valida DTO Pydantic + orquestra) → **service** (regra de negócio) →
  **repository** (SQLAlchemy). Proibido query direta no handler de rota.
- **A regra de negócio não importa FastAPI.** É o que mantém o domínio testável sem servidor.
- **Erros:** lançar as classes de `app/core/errors.py` (`AppError` e derivadas); o handler central
  traduz para HTTP. Proibido montar `JSONResponse` de erro na mão espalhado pelas rotas.
  Todo erro sai no formato único `{"error": {"code", "message"}}` — o front reage por `code`,
  nunca por texto.
- **Tipagem:** proibido `Any` em caminho de negócio. Tipos derivam dos schemas Pydantic e dos
  modelos SQLAlchemy (`Mapped[...]`).
- **Config:** todo `os.environ` passa por `app/core/config.py` (Pydantic Settings, fail-fast).
  **Sem default para segredo** em produção.
- **Dinheiro em centavos, sempre inteiro** (`price_cents`, `amount_cents`). Proibido float.
- **Datas em UTC com timezone** (`DateTime(timezone=True)`, `datetime.now(UTC)`). Proibido
  `datetime.now()` sem tz.
- **Enums de domínio** em `app/models/enums.py`, persistidos como string (`native_enum=False`).
- **Logging:** estruturado. Proibido `print` em código de produção.
- **Migrations:** toda mudança de modelo gera migration Alembic, e ela é validada em ciclo
  `upgrade → downgrade → upgrade` antes de commitar. **Nunca confiar no autogenerate sem ler o
  arquivo gerado** — ver seção 9.

---

## 8. Segurança — invariantes

- Nenhum endpoint confia em identidade vinda do corpo ou da query do cliente. O papel usado para
  autorizar vem **sempre** da sessão no Redis.
- **Autorização por lista branca explícita de papel** por rota (`RequireOrganizer`,
  `RequireCustomer`, `RequireGate`). Os três papéis são disjuntos: não há hierarquia de permissão.
- Todo acesso a recurso valida **ownership**: cliente só vê os próprios ingressos, organizador só
  gerencia os próprios eventos.
- A portaria é vinculada a um evento (`users.gate_event_id`); validar ingresso de outro evento
  responde **evento errado**, nunca sucesso.
- **Login não revela quais e-mails têm conta:** e-mail inexistente e senha errada devolvem
  resposta idêntica.
- Senha com **Argon2id**. Hash corrompido no banco vira "credencial inválida", nunca erro 500.
- Comparação de MAC com `hmac.compare_digest` (tempo constante).
- **Marcar ingresso como usado é operação condicional** (`UPDATE ... WHERE status = 'VALID'` com
  checagem de linhas afetadas): dois scanners lendo o mesmo QR no mesmo instante, só um vê válido.
- Segredos só via env validada; nada hardcoded. `TICKET_HMAC_SECRET` previsível torna o QR
  forjável — trocar em produção é obrigatório, não recomendação.
- `.env` reais nunca versionados (só `.env.example`).
- `SESSION_COOKIE_SECURE=true` em produção.

---

## 9. Testes

- **Unit obrigatório** para o que é regra de alto valor: sessão (criação, revogação, expiração
  dupla), HMAC do ingresso (código forjado, id trocado, malformado), e transições de estado de
  reserva/pagamento/ingresso.
- **A garantia de assento único é testada contra Postgres real**, com inserções concorrentes de
  verdade (`ThreadPoolExecutor`), verificando que exatamente uma vence. O índice parcial *é* a
  regra: testá-lo contra banco falso não provaria nada.
- **Teste que precisa de infra é pulado, nunca aprovado em silêncio.** Sem `TEST_DATABASE_URL`,
  `pytest.mark.skipif` marca como skip — um teste que passa por ausência de banco é pior que
  nenhum teste.
- Sessão é testada com `fakeredis` (o comportamento sob teste é do nosso código, não do servidor
  Redis).
- **Warnings do nosso código são erro** (`filterwarnings = error::DeprecationWarning` em
  `pytest.ini`); warnings de dependência de terceiros ficam em `default`.
- **Verificar no banco, não no arquivo gerado.** Já houve caso real neste projeto: o Alembic
  escreveu uma FK inline no `create_table` passando `use_alter=True`, que é silenciosamente
  ignorado — a coluna existia e a constraint **não**. Confirmar em `pg_constraint`/`pg_indexes`
  depois de aplicar a migration.

---

## 10. Fluxo de trabalho

- **Commits pequenos e descritivos ao longo do desenvolvimento** — o enunciado avalia o histórico
  como evidência de processo. Um commit gigante no último dia conta contra.
- **Manter a tabela *Status de implementação* do README sincronizada** com a realidade em cada
  commit. Marcar como pronto o que não está verificado é o pior erro possível aqui.
- Antes de declarar algo pronto: rodar `pytest` e, se a mudança toca schema, aplicar a migration
  em banco limpo.
- Artefatos de processo (specs, notas de decisão, contexto de IA) ficam versionados em `docs/`.
