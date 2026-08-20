"""Testes das primitivas de segurança."""

from app.core.security import (
    hash_password,
    new_session_id,
    sign_ticket_code,
    verify_password,
    verify_ticket_code,
)


# --- Senha ---


def test_senha_correta_valida():
    assert verify_password("senha123", hash_password("senha123"))


def test_senha_errada_falha():
    assert not verify_password("outra", hash_password("senha123"))


def test_hash_nao_contem_a_senha():
    assert "senha123" not in hash_password("senha123")


def test_mesmo_texto_gera_hashes_diferentes():
    """Salt por hash: dois usuários com a mesma senha têm hashes distintos."""
    assert hash_password("igual") != hash_password("igual")


def test_hash_invalido_nao_explode():
    """Hash corrompido no banco deve virar 'senha inválida', não erro 500."""
    assert not verify_password("qualquer", "isto-nao-e-um-hash")


# --- Código do ingresso (o requisito "QR que não pode ser forjado") ---


def test_codigo_legitimo_valida():
    tid = "abc-123"
    assert verify_ticket_code(sign_ticket_code(tid)) == tid


def test_mac_forjado_e_rejeitado():
    """Sem o segredo, não se produz um código válido."""
    assert verify_ticket_code("abc-123.0000000000000000") is None


def test_id_trocado_invalida_o_codigo():
    """Trocar o id mantendo o MAC não funciona — é o ataque óbvio."""
    mac = sign_ticket_code("ingresso-1").rpartition(".")[2]
    assert verify_ticket_code(f"ingresso-2.{mac}") is None


def test_codigo_malformado_e_rejeitado():
    for ruim in ["", "sem-ponto", ".", "abc.", ".xyz"]:
        assert verify_ticket_code(ruim) is None, f"deveria rejeitar: {ruim!r}"


def test_codigo_e_curto_para_caber_num_qr_legivel():
    """Motivo de ter recusado JWT no QR: densidade.

    Um QR com ~70 caracteres fica em versão baixa, com módulos grandes — o que
    permite ler com câmera de celular em porta de cinema. Um JWT passaria de
    200 e exigiria aproximar muito o aparelho.
    """
    code = sign_ticket_code("550e8400-e29b-41d4-a716-446655440000")
    assert len(code) < 100, f"código longo demais para QR legível: {len(code)}"


# --- session_id ---


def test_session_id_url_safe():
    """Vai em cookie e header: não pode ter caractere que precise de escape."""
    import string

    permitido = set(string.ascii_letters + string.digits + "-_")
    for _ in range(20):
        assert set(new_session_id()) <= permitido
