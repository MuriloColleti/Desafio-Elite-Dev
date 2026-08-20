#!/bin/sh
# Boot da API.
#
# As migrations rodam aqui, e não à mão, porque o plano gratuito do Render não
# dá shell no contêiner: sem isto a API subiria contra um banco sem tabelas e
# todo request falharia.
#
# `alembic upgrade head` é idempotente — em deploy sem migration nova ele não
# faz nada.

set -e

echo "→ aplicando migrations…"
alembic upgrade head

# O seed só roda quando pedido explicitamente (SEED_ON_BOOT=true) e só popula
# banco vazio: `app.seed` sem --reset recusa se já houver dados. Assim um
# redeploy não apaga o que o avaliador fez durante o teste.
if [ "${SEED_ON_BOOT}" = "true" ]; then
  echo "→ semeando dados de teste (se o banco estiver vazio)…"
  python -m app.seed || echo "  banco já populado, seguindo."
fi

echo "→ subindo a API na porta ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
