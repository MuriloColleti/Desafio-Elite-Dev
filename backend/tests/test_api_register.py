"""Registro de conta.

O ponto sensível é o papel: quem se cadastra pela tela pública não pode virar
portaria, porque validaria ingressos de eventos alheios.
"""

import pytest

pytestmark = pytest.mark.usefixtures("app_semeado")


def _registrar(cliente, **campos):
    corpo = {
        "name": "Pessoa Nova",
        "email": "nova@palco.dev",
        "password": "senha-longa-o-bastante",
        **campos,
    }
    return cliente.post("/auth/register", json=corpo)


# --- Caminho normal ---


def test_registro_cria_conta_e_abre_sessao(app_semeado):
    """Pedir login depois de definir a senha é um passo sem propósito."""
    clientes, _ = app_semeado
    c = clientes["anon"]

    r = _registrar(c)

    assert r.status_code == 201
    assert r.json()["role"] == "CUSTOMER"
    # A sessão já vale: /auth/me responde sem novo login.
    assert c.get("/auth/me").json()["email"] == "nova@palco.dev"


def test_cookie_do_registro_e_httponly(app_semeado):
    clientes, _ = app_semeado
    r = _registrar(clientes["anon"])

    assert "httponly" in r.headers.get("set-cookie", "").lower()


def test_cliente_e_o_papel_padrao(app_semeado):
    clientes, _ = app_semeado
    r = clientes["anon"].post(
        "/auth/register",
        json={"name": "Sem Papel", "email": "sp@palco.dev", "password": "senha-longa"},
    )

    assert r.json()["role"] == "CUSTOMER"


def test_registro_como_organizador_da_acesso_ao_painel(app_semeado):
    clientes, _ = app_semeado
    c = clientes["anon"]

    _registrar(c, email="org-novo@palco.dev", role="ORGANIZER")

    assert c.get("/organizer/events").status_code == 200


def test_da_para_entrar_depois_de_registrar(app_semeado):
    """A senha gravada tem de conferir no login — senão a conta nasce inútil."""
    clientes, _ = app_semeado
    _registrar(clientes["anon"], email="volta@palco.dev", password="minha-senha-123")

    r = clientes["anon"].post(
        "/auth/login", json={"email": "volta@palco.dev", "password": "minha-senha-123"}
    )
    assert r.status_code == 200


# --- Papel proibido ---


def test_nao_registra_como_portaria(app_semeado):
    """Portaria é conta operacional da casa, não algo de tela pública."""
    clientes, _ = app_semeado
    r = _registrar(clientes["anon"], role="GATE")

    assert r.status_code == 422


def test_nao_registra_com_papel_inventado(app_semeado):
    clientes, _ = app_semeado
    assert _registrar(clientes["anon"], role="ADMIN").status_code == 422


# --- E-mail duplicado ---


def test_recusa_email_ja_cadastrado(app_semeado):
    clientes, _ = app_semeado
    r = _registrar(clientes["anon"], email="ana@palco.dev")

    assert r.status_code == 409
    assert r.json()["error"]["code"] == "EMAIL_IN_USE"


def test_duplicado_ignora_caixa_e_espaco(app_semeado):
    """"Ana@X.com" e "ana@x.com" são a mesma conta.

    O UNIQUE do banco é sensível a caixa, então sem normalizar aqui as duas
    entrariam e o login ficaria ambíguo.
    """
    clientes, _ = app_semeado

    assert _registrar(clientes["anon"], email="ANA@PALCO.DEV").status_code == 409
    assert _registrar(clientes["anon"], email="  ana@palco.dev  ").status_code == 409


def test_email_e_gravado_em_minusculas(app_semeado):
    clientes, _ = app_semeado
    c = clientes["anon"]

    _registrar(c, email="MAIUSCULA@palco.dev")

    assert c.get("/auth/me").json()["email"] == "maiuscula@palco.dev"


# --- Validação ---


@pytest.mark.parametrize(
    ("campos", "motivo"),
    [
        ({"password": "curta"}, "senha com menos de 8"),
        ({"email": "não-é-email"}, "e-mail malformado"),
        ({"name": "A"}, "nome de um caractere"),
        ({"name": ""}, "nome vazio"),
    ],
)
def test_rejeita_dados_invalidos(app_semeado, campos, motivo):
    clientes, _ = app_semeado
    assert _registrar(clientes["anon"], **campos).status_code == 422, motivo


def test_nome_e_gravado_sem_espaco_nas_pontas(app_semeado):
    clientes, _ = app_semeado
    c = clientes["anon"]

    _registrar(c, name="  Maria Silva  ")

    assert c.get("/auth/me").json()["name"] == "Maria Silva"


# --- Login com caixa diferente ---


def test_login_aceita_email_em_maiusculas(app_semeado):
    """Quem cadastrou minúsculo e digitou maiúsculo deve entrar."""
    clientes, _ = app_semeado
    r = clientes["anon"].post(
        "/auth/login", json={"email": "ANA@PALCO.DEV", "password": "senha123"}
    )

    assert r.status_code == 200
