# Palco — Plataforma de Eventos e Ingressos

Desafio Elite Dev (Verzel). Uma plataforma onde um **organizador** publica eventos a partir de um
catálogo externo (filmes do TMDb, shows do Ticketmaster), um **cliente** reserva lugar, paga de
forma simulada e recebe um ingresso com QR, e a **portaria** valida esse ingresso na entrada.

> **Status:** o **back-end está completo e testado** (182 testes) — todo o fluxo do enunciado
> funciona pela API: catálogo, evento, reserva, pagamento com recusa, ingresso com QR, link de
> compartilhamento e os quatro resultados da portaria. O **front-end ainda não existe**; até lá o
> fluxo é percorrível pelo `/docs` (Swagger). Ver
> [Status de implementação](#status-de-implementação).

---

## Sumário

- [Por que essas escolhas](#por-que-essas-escolhas)
- [Arquitetura](#arquitetura)
- [Stack](#stack)
- [Como rodar](#como-rodar)
- [Banco de dados](#banco-de-dados)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Chaves das APIs externas](#chaves-das-apis-externas)
- [Dados semeados (seed)](#dados-semeados-seed)
- [Percorrendo o fluxo completo](#percorrendo-o-fluxo-completo)
- [Autenticação: sessão opaca em Redis](#autenticação-sessão-opaca-em-redis)
- [Decisões de domínio](#decisões-de-domínio)
- [API](#api)
- [Testes](#testes)
- [Uso de IA](#uso-de-ia)
- [Status de implementação](#status-de-implementação)

---

## Por que essas escolhas

O enunciado diz que o escopo é pequeno de propósito e que o que interessa é o raciocínio. Então
registro aqui as decisões que tomei antes de escrever código, e o que descartei.

**Duas APIs externas, um catálogo só.** Usei TMDb *e* Ticketmaster porque os dois fluxos de
reserva do PDF pedem naturezas diferentes de evento: filme quer **mapa de assentos** (cinema tem
lugar marcado), show quer **quantidade** (pista não tem lugar). Em vez de dois caminhos paralelos
no sistema, os dois provedores entram por uma interface única `CatalogProvider` e viram um
`CatalogItem` normalizado. O resto da aplicação não sabe de onde o item veio — e é isso que
permite que o mesmo formulário de criação de evento sirva para filme e para show.

**O evento não é o item do catálogo.** Um filme do TMDb não tem data, local, capacidade nem
preço — isso é decisão do organizador. Então `Event` é uma entidade nossa que *referencia* um
`catalog_ref` (`tmdb:movie:550`), guardando um snapshot de título/pôster/sinopse no momento da
criação. Duas razões: a listagem de eventos não depende de a API externa estar de pé, e um
evento publicado não muda de cara se o TMDb editar o registro depois.

**Assento único: o banco decide, não o código.** Vender o mesmo lugar duas vezes é uma condição
de corrida, e checar "está livre?" antes de inserir não resolve — duas requisições simultâneas
passam pelo check as duas. A garantia é uma constraint `UNIQUE` parcial sobre as reservas ativas,
dentro de uma transação: quem chega em segundo lugar recebe violação de unicidade do Postgres e o
handler traduz isso em `409 SEAT_TAKEN`. Não se ganha essa corrida com esperteza no código de
aplicação; ganha-se delegando ao único componente que serializa de fato.

**Ingresso não-forjável sem estado extra.** O QR não carrega o id do ingresso em texto puro —
carrega `<ticket_id>.<hmac>`, onde o HMAC-SHA256 é assinado com um segredo do servidor. Assim a
portaria confirma a autenticidade sem depender de adivinhação, e ninguém fabrica um código válido
incrementando número. Descartei JWT no QR: o payload ficaria grande e o QR denso demais para ler
com câmera de celular em porta de cinema.

**Compartilhar não é transferir.** O link de compartilhamento (`/i/<token>`) é um token opaco,
separado do código de validação, e abre uma página **somente leitura** do ingresso. Quem recebe o
link vê o ingresso, não ganha o direito de entrar como se fosse dono — e revogar o link não
invalida o ingresso. Revenda entre usuários está explicitamente fora do escopo no PDF.

**Recusa de pagamento é caminho de primeira classe.** O PDF pede confirmação *e* recusa. A
reserva nasce `PENDING` com expiração curta; a recusa não é um erro genérico de tela, é uma
transição de estado que devolve o assento ao estoque. Isso é o que evita o assento fantasma:
reservado por alguém cujo cartão falhou e nunca liberado.

**FastAPI + React/Vite.** Python no back porque é onde tenho mais fluência para escrever a lógica
de domínio com cuidado no tempo do desafio. Vite em vez de Next porque aqui não há necessidade de
SSR nem SEO — é uma aplicação autenticada — e um SPA magro tira uma camada de complexidade de
build do caminho.

**Sobre o "AI slop".** Usei IA no projeto (detalhado em [Uso de IA](#uso-de-ia)), mas as decisões
de produto e de interface são minhas e estão justificadas aqui. A UI não usa tema escuro com
gradiente roxo e cards de vidro; é clara, tipográfica, com o pôster do evento carregando o peso
visual — a imagem do filme/show é o que o usuário reconhece, então ela manda na tela.

---

## Arquitetura

```
┌─────────────────────────┐         ┌──────────────────────────────────────┐
│  frontend (React/Vite)  │         │  backend (FastAPI)                   │
│                         │         │                                      │
│  /              vitrine │  HTTP   │  /auth        login, /me             │
│  /eventos/:id   reserva │ ──────► │  /catalog     busca nos provedores   │
│  /checkout      pgto    │  JSON   │  /events      CRUD do organizador    │
│  /meus-ingressos   QR   │         │  /reservations  hold + expiração     │
│  /portaria      scanner │         │  /payments    simulado (aprova/nega) │
│  /i/:token      público │         │  /tickets     emissão, QR, share     │
└─────────────────────────┘         │  /gate        validação na portaria  │
                                    └───────────────┬──────────────────────┘
                                                    │
                          ┌─────────────────────────┼─────────────────────┐
                          ▼                         ▼                     ▼
    ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐  ┌───────────────┐
    │   PostgreSQL    │  │    Redis     │  │  TMDb (filmes)   │  │ Ticketmaster  │
    │  eventos,       │  │  sessões,    │  │                  │  │   (shows)     │
    │  reservas,      │  │  cache do    │  └──────────────────┘  └───────────────┘
    │  ingressos      │  │  catálogo    │        via CatalogProvider
    └─────────────────┘  └──────────────┘
```

Camadas no back-end: `api/` (rotas e schemas Pydantic) → `services/` (regras de domínio, onde
mora a transação de reserva) → `repositories/` (acesso via SQLAlchemy) → `providers/` (clientes
HTTP das APIs externas). A regra de negócio não importa nada de FastAPI, o que mantém os testes de
domínio sem servidor no meio.

---

## Stack

| Camada        | Escolha                                                 |
| ------------- | ------------------------------------------------------- |
| Front-end     | React 18, TypeScript, Vite, React Router                |
| Back-end      | Python 3.12+, FastAPI, Pydantic v2                       |
| ORM           | SQLAlchemy 2.0 + Alembic (migrations)                   |
| Banco         | PostgreSQL 16                                           |
| Sessão        | Redis 7                                                 |
| Auth          | Sessão opaca em Redis, 3 papéis: ORGANIZER, CUSTOMER, GATE |
| QR            | `qrcode` (geração), `html5-qrcode` (leitura via câmera)  |
| Catálogo      | TMDb API + Ticketmaster Discovery API v2                 |
| Testes        | pytest (back), Vitest (front)                            |
| Infra local   | Docker Compose                                           |

---

## Como rodar

Pré-requisitos: **Docker + Docker Compose**, ou então **Python 3.12+**, **Node 20+**, um
**PostgreSQL 16** e um **Redis 7** acessíveis.

### Opção 1 — Docker Compose (recomendado)

```bash
git clone https://github.com/MuriloColleti/Desafio-Elite-Dev.git
cd Desafio-Elite-Dev

# 1. configure as chaves das APIs externas (ver seção abaixo)
cp .env.example .env
#    edite .env e preencha TMDB_API_KEY e TICKETMASTER_API_KEY

# 2. suba tudo (banco + api + web)
docker compose up --build

# 3. em outro terminal: migrations + dados de teste
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
```

| Serviço      | URL                        |
| ------------ | -------------------------- |
| Front-end    | http://localhost:5173      |
| API          | http://localhost:8000      |
| Docs da API  | http://localhost:8000/docs |
| PostgreSQL   | localhost:5432             |

### Opção 2 — Local, sem Docker

**Back-end:**

```bash
cd backend
python -m venv .venv

# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

cp .env.example .env      # ajuste DATABASE_URL e REDIS_URL

alembic upgrade head      # cria o schema
python -m app.seed        # popula os dados de teste

uvicorn app.main:app --reload --port 8000
```

**Front-end** (em outro terminal):

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL=http://localhost:8000
npm run dev
```

---

## Banco de dados

**PostgreSQL 16.** A escolha não é gosto: a garantia de assento único depende de constraint
`UNIQUE` parcial e de transação, e eu queria isso resolvido pelo banco em vez de por lock na
aplicação. SQLite não daria conta do teste de concorrência.

**Subindo só banco e Redis, via Docker:**

```bash
docker compose up -d db redis
```

Ou, sem Compose:

```bash
docker run -d --name palco-pg -e POSTGRES_USER=palco -e POSTGRES_PASSWORD=palco   -e POSTGRES_DB=palco -p 5432:5432 postgres:16-alpine
docker run -d --name palco-redis -p 6379:6379 redis:7-alpine
```

**Ou aponte para um Postgres seu** em `backend/.env`:

```
DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/palco
```

**Comandos úteis:**

```bash
alembic upgrade head                      # aplica todas as migrations
alembic revision --autogenerate -m "..."  # cria uma migration nova
alembic downgrade -1                      # desfaz a última
python -m app.seed                        # (re)popula os dados de teste
python -m app.seed --reset                # limpa e repopula
```

**Modelo de dados:**

```
User        id, name, email, password_hash, role(ORGANIZER|CUSTOMER|GATE)
Event       id, organizer_id, catalog_ref, title, poster_url, synopsis,
            venue, starts_at, layout(SEATED|GENERAL), capacity, price_cents,
            status(DRAFT|PUBLISHED|CANCELLED)
Seat        id, event_id, label, row, number            -- só quando layout=SEATED
Reservation id, event_id, customer_id, seat_label|null, quantity,
            status(PENDING|PAID|CANCELLED|EXPIRED), expires_at
Payment     id, reservation_id, status(APPROVED|DECLINED), amount_cents, reason
Ticket      id, reservation_id, code_hmac, share_token,
            status(VALID|USED|CANCELLED), used_at, used_by_id
```

A unicidade do assento é uma constraint no banco:

```sql
CREATE UNIQUE INDEX uq_seat_active
  ON reservations (event_id, seat_label)
  WHERE status IN ('PENDING', 'PAID') AND seat_label IS NOT NULL;
```

Reserva cancelada, expirada ou com pagamento recusado sai do índice e o assento volta ao estoque —
sem job de limpeza para devolver estoque.

---

## Variáveis de ambiente

`backend/.env`:

| Variável                  | Para quê                                            | Padrão                  |
| ------------------------- | --------------------------------------------------- | ----------------------- |
| `DATABASE_URL`            | Conexão com o Postgres                              | —                       |
| `REDIS_URL`               | Conexão com o Redis (sessões)                       | —                       |
| `SESSION_TTL_SECONDS`     | Expiração por inatividade, renovada a cada uso      | `28800` (8 h)           |
| `SESSION_ABSOLUTE_TTL_SECONDS` | Teto absoluto da sessão, não renovável         | `604800` (7 d)          |
| `SESSION_COOKIE_SECURE`   | `true` em produção (exige HTTPS no cookie)          | `false`                 |
| `TICKET_HMAC_SECRET`      | Assinatura do código do QR (**troque em produção**) | —                       |
| `TMDB_API_KEY`            | Catálogo de filmes                                  | —                       |
| `TICKETMASTER_API_KEY`    | Catálogo de shows                                   | —                       |
| `RESERVATION_TTL_MINUTES` | Tempo que o assento fica em hold antes de expirar   | `10`                    |
| `PAYMENT_DECLINE_RATE`    | Recusa aleatória no pagamento simulado (0 desliga)  | `0`                     |
| `CORS_ORIGINS`            | Origens liberadas para o front                      | `http://localhost:5173` |

`frontend/.env`:

| Variável       | Para quê    | Padrão                  |
| -------------- | ----------- | ----------------------- |
| `VITE_API_URL` | Base da API | `http://localhost:8000` |

---

## Chaves das APIs externas

Ambas são gratuitas e saem na hora.

**TMDb** — crie conta em [themoviedb.org](https://www.themoviedb.org/signup), vá em
*Settings → API*, peça uma chave de uso pessoal e copie a **API Key (v3 auth)** para
`TMDB_API_KEY`.

**Ticketmaster** — crie conta em
[developer.ticketmaster.com](https://developer.ticketmaster.com/), a app padrão já vem com uma
chave; copie o **Consumer Key** para `TICKETMASTER_API_KEY`.

**Sem as chaves a aplicação sobe.** O catálogo cai para um conjunto de itens de exemplo em
`backend/app/providers/fixtures/`, e a busca avisa na tela que está em modo offline. Isso é
proposital: quem avalia consegue percorrer todo o fluxo de compra e validação sem cadastrar chave
em serviço nenhum. O que não funciona sem chave é apenas a busca por títulos reais.

---

## Dados semeados (seed)

`python -m app.seed` cria os usuários pedidos no PDF. Senha igual para todos: **`senha123`**.

| Papel       | E-mail                  | Para quê                                  |
| ----------- | ----------------------- | ----------------------------------------- |
| Organizador | `organizador@palco.dev` | Cria e gerencia eventos                   |
| Cliente 1   | `ana@palco.dev`         | Já tem um ingresso pago para testar QR    |
| Cliente 2   | `bruno@palco.dev`       | Começa sem ingresso, para testar a compra |
| Portaria    | `portaria@palco.dev`    | Valida ingressos na entrada               |

E também:

- **2 eventos publicados com ingressos disponíveis:**
  - um **filme** (TMDb) com mapa de assentos — 8 fileiras × 12 lugares, alguns já ocupados de
    propósito, para o mapa não parecer vazio;
  - um **show** (Ticketmaster) com pista por quantidade — 500 lugares.
- **1 evento em rascunho**, para se ver o painel do organizador com estado misto.
- **1 ingresso já pago** da Ana no evento de cinema, com QR válido — dá para ir direto na portaria
  validar sem passar pelo checkout.
- **1 ingresso já utilizado**, para ver a resposta `já utilizado` da portaria.
- **1 ingresso de outro evento**, para ver a resposta `evento errado`.

Ao terminar, o seed **imprime os códigos dos três ingressos** — dá para colar direto na
digitação manual da portaria e ver as quatro respostas sem passar pelo checkout:

```
  válido .......... 7ca0a5b7-…-b23048439780.5102cb4ec5e915254664cdf55716caa3
  já utilizado .... 9c0b5f4b-…-d030775d8cbb.cdb7d54f5dfdb5939d10873989f96d02
  evento errado ... f8319efe-…-6ec4fd1e9f03.f9ffbd556699e81911bbcfe8ca78fc4d
  inválido ........ qualquer texto
```

---

## Percorrendo o fluxo completo

Roteiro sugerido para avaliação, cerca de 5 minutos:

1. **Vitrine** — abra http://localhost:5173. Os eventos publicados aparecem com data, local e
   preço. Busque e filtre.
2. **Organizador** — entre como `organizador@palco.dev`. Em *Criar evento*, busque um título no
   catálogo (filme ou show), defina data, local, capacidade e preço, publique. Ele aparece na
   vitrine.
3. **Cliente** — entre como `bruno@palco.dev`, abra o evento de cinema, escolha um assento no
   mapa (os ocupados estão bloqueados) e siga para o checkout.
4. **Pagamento recusado** — no checkout, use o cartão `4000 0000 0000 0002`. A recusa aparece e o
   assento volta a ficar disponível no mapa.

   | Cartão                | Resultado                     |
   | --------------------- | ----------------------------- |
   | `4242 4242 4242 4242` | aprovado                      |
   | `4000 0000 0000 0002` | recusado pelo emissor         |
   | `4000 0000 0000 9995` | saldo insuficiente            |
   | `4000 0000 0000 0069` | cartão expirado               |
   | `4000 0000 0000 0127` | código de segurança inválido  |

   Qualquer outro número é aprovado. A decisão é **determinística** pelo número, e não aleatória,
   para os dois caminhos serem reproduzíveis. Os números seguem a convenção dos provedores reais.
5. **Pagamento aprovado** — repita com `4242 4242 4242 4242`. O ingresso é emitido.
6. **Meus ingressos** — veja o ingresso com o QR. Copie o link de compartilhamento e abra numa
   janela anônima: mostra o ingresso, somente leitura.
7. **Portaria** — entre como `portaria@palco.dev`, aponte a câmera para o QR (ou digite o código).
   Resposta: **válido**. Escaneie de novo: **já utilizado**. Escaneie o ingresso de outro evento:
   **evento errado**. Digite qualquer coisa: **inválido**.

---

## Autenticação: sessão opaca em Redis

O front recebe um **`session_id`**: 256 bits aleatórios, sem estrutura e sem significado. Ele ocupa
o lugar que um JWT ocuparia — é o que o cliente guarda e reenvia — mas as propriedades são
opostas. Todo o estado da sessão (quem é, qual papel) fica no Redis, sob `session:<id>`.

**Por que não JWT.** Um JWT é autocontido: quem tem o token tem os claims, e o servidor não
consegue invalidá-lo antes de expirar. Isso troca uma consulta por três problemas — logout que não
desloga, mudança de papel que só vale no próximo login, e claims legíveis por quem interceptar o
token. Com token opaco o servidor é a única fonte de verdade: `DEL session:<id>` encerra a sessão
naquele instante.

O custo é uma consulta ao Redis por request autenticado — que é `O(1)` em memória, e o preço de
poder revogar.

**O que deliberadamente não fazemos** é guardar um JWT *dentro* do Redis e devolver esse JWT ao
front. Isso anularia o ganho: o cliente voltaria a ter um token autocontido, decodificável e
não-revogável, e o Redis seria só um armário no caminho. Não existe JWT em nenhum ponto deste
fluxo.

**Transporte.** O `session_id` vai em cookie `httponly`, `samesite=lax` — invisível para
JavaScript, o que neutraliza roubo de sessão por XSS (vantagem que um JWT em `localStorage` não
tem). O header `Authorization: Bearer <session_id>` é aceito como alternativa, para `curl` e
testes.

**Duas janelas de expiração**, porque resolvem coisas diferentes:

| Janela | Padrão | Renovada? | Resolve |
| ------ | ------ | --------- | ------- |
| Inatividade (`SESSION_TTL_SECONDS`) | 8 h | sim, a cada request | quem parou de usar perde a sessão |
| Absoluta (`SESSION_ABSOLUTE_TTL_SECONDS`) | 7 dias | **nunca** | aba aberta para sempre = sessão eterna, e token roubado valendo sem prazo |

**Redis cair não perde dado de negócio.** Sessão é estado descartável: ninguém perde ingresso nem
reserva, as pessoas só precisam entrar de novo. É por isso que o hold de assento **não** mora aqui
— ele pertence à mesma transação que garante o assento, no Postgres. O `/health` reporta os dois
serviços separadamente justamente para essa distinção não virar adivinhação.

**Papéis.** Os três do PDF são disjuntos — organizador não compra, cliente não valida — então a
autorização é lista branca explícita por rota (`RequireOrganizer`, `RequireCustomer`,
`RequireGate`), não hierarquia de permissão. A portaria é vinculada a um evento
(`users.gate_event_id`), e é isso que permite responder **evento errado** em vez de aceitar
qualquer ingresso legítimo.

---

## Decisões de domínio

**Hold antes de pagar.** Escolher assento cria uma reserva `PENDING` com `expires_at`. Sem hold,
duas pessoas chegam ao checkout com o mesmo lugar e uma descobre no fim do processo que perdeu —
péssima experiência. Com hold, a disputa é resolvida no clique, não no pagamento. A expiração é
avaliada na leitura (`expires_at < now()` conta como livre), então não existe job de background
que precise estar rodando para o estoque ficar correto.

**Estados da validação na portaria.** O PDF pede quatro respostas distintas, e cada uma tem uma
causa diferente:

| Resposta          | Quando                                                        |
| ----------------- | ------------------------------------------------------------- |
| **válido**        | HMAC confere, ingresso `VALID`, evento é o da portaria         |
| **inválido**      | HMAC não confere, ou o código não existe                      |
| **já utilizado**  | Ingresso `USED` — a resposta mostra data/hora do primeiro uso |
| **evento errado** | Ingresso legítimo, mas de outro evento                        |

Marcar como usado é `UPDATE ... WHERE status = 'VALID'` com checagem de linhas afetadas: dois
scanners na mesma porta lendo o mesmo QR no mesmo instante, e só um vê **válido**. Se fosse
`ticket.status = USED` seguido de commit, os dois leriam `VALID` antes de qualquer escrita e ambos
passariam. Testado com 20 leituras simultâneas: exatamente uma entrada liberada.

**A ordem das checagens importa.** Autenticidade (HMAC) → existência → evento → estado. Checar o
estado antes do evento faria um ingresso de outro evento já utilizado responder *já utilizado*,
escondendo de quem está na porta o problema real: está na porta errada. E validar na porta errada
**não consome** o ingresso.

As três recusas respondem **200**, não 4xx: são resultado de negócio que a portaria precisa exibir.
Com 4xx o front cairia no tratamento de falha genérica em vez de mostrar o motivo.

**Preço em centavos, inteiro.** `price_cents` em vez de float. Ninguém quer descobrir `0.1 + 0.2`
num total de carrinho.

**Cancelamento devolve ao estoque.** Cliente cancela reserva paga → ingresso vira `CANCELLED`,
sai do índice de unicidade, assento reaparece no mapa.

**O que já foi vendido limita a edição.** Preço não muda com ingresso vendido (quem pagou pagou
outro valor, e mudar criaria duas verdades para o mesmo evento); capacidade não cai abaixo do que
já saiu; evento publicado não volta a rascunho — cancela-se. E a capacidade de evento com assentos
é **derivada** do mapa (`seat_rows × seats_per_row`), não um campo livre: dois campos independentes
divergiriam e o mapa deixaria de fechar com o total de ingressos.

---

## API

Documentação interativa (OpenAPI) em **http://localhost:8000/docs** com o servidor de pé.

```
POST   /auth/login                    → abre sessão (cookie httponly + session_id no corpo)
POST   /auth/logout                   → encerra a sessão no servidor
GET    /auth/me                       → usuário atual

GET    /catalog/search?q=&source=     → busca em TMDb e/ou Ticketmaster  [ORGANIZER]

GET    /events                        → vitrine: publicados e futuros, com busca e filtro
GET    /events/:id                    → detalhe + mapa de assentos com os ocupados

GET    /organizer/events              → todos os meus eventos    [ORGANIZER]
POST   /organizer/events              → cria (publish opcional)  [ORGANIZER]
PATCH  /organizer/events/:id          → edita / publica          [ORGANIZER]
DELETE /organizer/events/:id          → cancela                  [ORGANIZER]

POST   /reservations                  → cria hold (409 SEAT_TAKEN se perdeu)  [CUSTOMER]
DELETE /reservations/:id              → libera hold, devolve ao estoque       [CUSTOMER]

POST   /payments                      → cobrança simulada (aprova ou recusa)

GET    /tickets/me                    → meus ingressos [CUSTOMER]
GET    /tickets/:id/qr                → PNG do QR      [CUSTOMER]
POST   /tickets/:id/share             → gera link público
GET    /public/tickets/:token         → ingresso, somente leitura (sem auth)

POST   /gate/validate                 → valida código  [GATE]
```

Erros seguem um formato só: `{"error": {"code": "SEAT_TAKEN", "message": "..."}}`, para o front
poder reagir por código em vez de por texto.

---

## Testes

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

**182 testes passando.** Sessão, HMAC, catálogo e normalização dos provedores rodam com um Redis
em memória (`fakeredis`), sem precisar de infraestrutura. Os testes de concorrência exigem um Postgres real — e isso é proposital: o índice
parcial *é* a regra de negócio, então testá-lo contra um banco falso não provaria nada. Sem
`TEST_DATABASE_URL` eles são **pulados**, nunca aprovados em silêncio:

```bash
docker run -d --name palco-test-pg -e POSTGRES_USER=palco -e POSTGRES_PASSWORD=palco   -e POSTGRES_DB=palco -p 5432:5432 postgres:16-alpine

export TEST_DATABASE_URL=postgresql+psycopg://palco:palco@localhost:5432/palco
export DATABASE_URL=$TEST_DATABASE_URL
alembic upgrade head
pytest                            # agora inclui os testes de concorrência
```

Os testes de fluxo (`test_api_flow.py`) exercitam a API pelo HTTP, e não os serviços diretamente:
é o que garante que as guardas de papel e os códigos de erro estão de fato ligados nas rotas —
um serviço correto com uma rota sem guarda passaria num teste de unidade.

O teste que mais importa dispara **20 reservas simultâneas para o mesmo assento** e verifica que
exatamente uma vence. É o requisito mais fácil de parecer resolvido sem estar — e por isso o único
que faz questão de um banco de verdade. Ele também cobre o outro lado: cancelar ou expirar devolve
o assento ao estoque, e reservas de pista (`seat_label NULL`) não se bloqueiam entre si.

```bash
cd frontend && npm test           # componentes (ainda não implementado)
```

---

## Uso de IA

Usei **Claude Code (Opus)** como par ao longo do desafio. O que ficou com cada um:

**Meu, sem IA:**

- Todas as decisões de produto e de domínio da seção [Por que essas escolhas](#por-que-essas-escolhas):
  separar `Event` do item de catálogo, hold com expiração avaliada na leitura, HMAC no QR em vez
  de JWT, share token separado do código de validação.
- Modelagem do banco e a estratégia de unicidade por constraint parcial.
- Direção visual: layout das telas, hierarquia da vitrine, decisão de deixar o pôster mandar na
  composição, e a recusa deliberada da estética padrão de projeto gerado.
- Escolha da stack e do recorte do escopo.

**Com IA:**

- Boilerplate: configuração do FastAPI, modelos SQLAlchemy a partir do modelo que desenhei,
  migrations Alembic, setup do Vite.
- Clientes HTTP do TMDb e do Ticketmaster e o mapeamento para `CatalogItem`.
- Componente de mapa de assentos (a lógica de grid; o visual foi ajustado à mão).
- Casos de teste, e a redação deste README a partir das minhas decisões.

**Onde discordei da IA:** a primeira sugestão foi colocar um JWT dentro do QR e usar Redis para
os *holds* de assento. Recusei as duas: o QR ficava denso demais para câmera de celular, e o hold
é estado que não pode se perder — pertence à mesma transação que garante o assento, então mora no
Postgres, não num cache. Também descartei um schema com tabela de `seat_locks` separada: a
constraint parcial faz o mesmo trabalho sem uma tabela a mais para manter em sincronia.

O Redis entrou depois, para outra finalidade: guardar **sessão**, que é justamente estado
descartável. Ver [Autenticação](#autenticação-sessão-opaca-em-redis).

Os artefatos de contexto que produzi no caminho ficam versionados em [`docs/`](docs/).

---

## Status de implementação

Atualizado a cada commit. O PDF pede que o que não funciona esteja dito no README, então esta
seção é a fonte de verdade — o resto do documento descreve o desenho da solução, não uma garantia
de que já esteja pronto.

| Item                                           | Status          |
| ---------------------------------------------- | --------------- |
| README, decisões e desenho da arquitetura      | ✅ pronto       |
| Estrutura do repositório e commit inicial      | ✅ pronto       |
| Modelos e migration inicial                    | ✅ pronto       |
| Autenticação por sessão opaca + 3 papéis       | ✅ pronto       |
| Garantia de assento único (constraint + teste) | ✅ pronto       |
| Seed de dados de teste                         | ✅ pronto       |
| Catálogo TMDb + Ticketmaster (+ modo offline)   | ✅ pronto       |
| CRUD de eventos (organizador)                  | ✅ pronto       |
| Reserva com mapa de assentos + pista           | ✅ pronto       |
| Pagamento simulado (aprovação e recusa)        | ✅ pronto       |
| Emissão do ingresso, QR e link de compartilhar | ✅ pronto       |
| Validação na portaria (API, 4 resultados)      | ✅ pronto       |
| Front-end (todas as telas)                     | 🔜 pendente     |
| Leitura do QR pela câmera                      | 🔜 pendente     |
| Testes do back-end (182)                       | ✅ pronto       |
| Deploy público                                 | 🔜 pendente     |

**Limitações conhecidas / avisos:**

- A cobrança é simulada; não há provedor de pagamento real. Os números de cartão do roteiro são
  gatilhos de aprovação/recusa, não validam nada.
- A leitura do QR pela câmera exige HTTPS ou `localhost` — restrição do navegador, não da
  aplicação. Em outro host sem TLS, use a digitação manual do código.
- **Assento marcado tem garantia forte; pista não.** O índice único parcial resolve a disputa por
  um lugar específico, mas a capacidade da pista é uma soma (`SUM(quantity) <= capacity`), e isso
  não se expressa como constraint. A checagem é feita na aplicação e, portanto, sujeita a corrida:
  duas compras simultâneas de pista podem passar juntas e estourar a capacidade em alguns lugares.
  Aceitei o risco em vez de serializar toda compra com um lock por evento — em pista o overbooking
  pequeno é reconciliável na entrada, enquanto vender o mesmo assento numerado duas vezes não é.
  Se fosse necessário fechar isso, o caminho seria `SELECT ... FOR UPDATE` na linha do evento.
- O cache do catálogo fica no Redis (`CATALOG_CACHE_TTL_SECONDS`, 15 min por padrão): como o
  Redis já é dependência para sessão, usá-lo também aqui evita que cada instância tenha o seu
  próprio cache e queime o rate limit das APIs externas em duplicidade.
