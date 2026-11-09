import jwt as pyjwt
from flask import Blueprint, current_app, jsonify, request

from . import db
from .jwt_utils import emitir_token, verificar_token

bp = Blueprint("main", __name__)


# Paginas estaticas servidas de forma explicita (no dependemos de que el
# "/" generico del static folder resuelva a un index.html).
@bp.get("/")
def pagina_login():
    return current_app.send_static_file("login.html")


@bp.get("/productos")
def pagina_productos():
    return current_app.send_static_file("productos.html")


@bp.get("/alumno-devtools")
def pagina_devtools():
    return current_app.send_static_file("alumno-devtools.html")


def _token_desde_request():
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


def _requiere_auth():
    """Devuelve el payload decodificado o None si no hay token valido."""
    token = _token_desde_request()
    if not token:
        return None
    try:
        return verificar_token(token)
    except pyjwt.PyJWTError:
        return None


@bp.get("/health")
def health():
    return jsonify(status="ok")


@bp.post("/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "")
    password = body.get("password", "")

    user = db.check_password(username, password)
    if not user:
        return jsonify(error="credenciales invalidas"), 401

    token = emitir_token(user)
    return jsonify(token=token)


# VULNERABLE (CWE-602): el perfil se arma con lo que dice el token, no con lo
# que hay en la base. Si el token esta forjado, esto devuelve el dato falso.
@bp.get("/me")
def me():
    payload = _requiere_auth()
    if payload is None:
        return jsonify(error="falta o es invalido el token"), 401
    return jsonify(
        sub=payload.get("sub"),
        username=payload.get("username"),
        balance=payload.get("balance"),
        isVip=payload.get("isVip"),
    )


@bp.get("/tienda/catalogo")
def catalogo():
    return jsonify(db.catalogo())


# VULNERABLE (CWE-602): la autorizacion de la compra (saldo suficiente,
# descuento VIP) se decide con los claims del token, nunca con el saldo real
# que figura en la base. Alterar "balance"/"isVip" en el token forjado alcanza.
@bp.post("/tienda/comprar")
def comprar():
    payload = _requiere_auth()
    if payload is None:
        return jsonify(error="falta o es invalido el token"), 401

    body = request.get_json(silent=True) or {}
    producto = body.get("producto", "")
    precio = body.get("precio")
    if precio is None:
        item = db.producto_por_nombre(producto)
        if not item:
            return jsonify(error="producto desconocido"), 404
        precio = item["precio"]

    balance = payload.get("balance", 0)
    es_vip = bool(payload.get("isVip"))
    precio_final = precio * 0.8 if es_vip else precio

    if balance < precio_final:
        return jsonify(
            error="saldo insuficiente",
            balance=balance,
            precio_final=precio_final,
        ), 402

    return jsonify(
        ok=True,
        mensaje=f"compra de '{producto}' exitosa",
        precio_final=precio_final,
        descuento_vip_aplicado=es_vip,
        balance_usado_para_autorizar=balance,
    )
