import time

import jwt

# VULNERABLE (CWE-798 Uso de credenciales hardcodeadas / CWE-326 Fuerza
# criptografica insuficiente): secreto corto, hardcodeado y presente en
# cualquier wordlist basica. Con un diccionario corto y la firma del token
# (HMAC-SHA256 de "header.payload") se puede recuperar offline en segundos.
SECRET = "secret123"
ALGORITHM = "HS256"


def emitir_token(usuario):
    """Firma un JWT HS256 a partir de un registro de usuario.

    VULNERABLE (CWE-602 Client-Side Enforcement of Server-Side Security):
    "balance" e "is_vip" son datos de negocio que el servidor deberia volver
    a calcular/consultar en cada request. Acá se calculan una sola vez, en
    el login, y de ahi en adelante el servidor "cree" lo que diga el token.
    """
    payload = {
        "sub": str(usuario["id"]),
        "username": usuario["username"],
        "balance": usuario["balance"],
        "isVip": usuario["is_vip"],
        "iat": int(time.time()),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def verificar_token(token):
    """Verifica la firma y devuelve el payload. Lanza jwt.PyJWTError si no es valido."""
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
