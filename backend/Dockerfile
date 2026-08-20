# Back-end FastAPI.
#
# Serve para o Compose local e para o deploy no Render — mesma imagem, mesma
# forma de rodar, então "funciona na minha máquina" e "funciona em produção"
# param de ser perguntas diferentes.

FROM python:3.12-slim

# Sem .pyc e sem buffer no stdout: o log aparece na hora nos dois ambientes.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Requirements antes do código: a camada de dependências só reconstrói quando
# elas mudam, e não a cada edição de arquivo.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Normaliza a quebra de linha e dá permissão de execução. O repositório é
# editado no Windows, e um shell script com CRLF falha no Linux com "no such
# file or directory" — erro que aponta para o lugar errado.
RUN tr -d '\r' < entrypoint.sh > /tmp/e.sh \
    && mv /tmp/e.sh entrypoint.sh \
    && chmod +x entrypoint.sh \
    # Usuário sem privilégio: nada aqui precisa de root.
    && useradd --create-home --shell /bin/bash palco \
    && chown -R palco:palco /app
USER palco

EXPOSE 8000

# O entrypoint aplica as migrations antes de subir — ver entrypoint.sh.
CMD ["./entrypoint.sh"]
