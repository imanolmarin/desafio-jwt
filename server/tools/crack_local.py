#!/usr/bin/env python3
"""Fuerza bruta offline del secreto HS256 de un JWT. A COMPLETAR POR EL ALUMNO.

Este archivo esta vacio a proposito: es tu punto de partida para construir
(o adaptar) una herramienta que recupere el secreto de firma del token del
Paso 2 del desafio.

Reglas:
- Tiene que ejecutarse 100% en tu maquina (stdlib, una libreria que instales
  con pip, un binario que bajes e instales localmente, etc.).
- NO vale ningun servicio online (decodificadores/"JWT crackers" web,
  pegar el token en un sitio de terceros, APIs en la nube). Si la herramienta
  manda el token afuera de tu maquina, no cuenta.
- Podes escribir tu propio script (en Python, con "hmac"/"hashlib" de la
  libreria estandar, recalculando la firma contra una wordlist) o usar
  cualquier herramienta de terceros que corra en local, por ejemplo
  `jwt_tool` o `hashcat` (ver el README para ejemplos de invocacion).
- `tools/wordlist.txt` tiene un diccionario corto para probar.

Pista de forma (si vas a escribir tu propio script en Python):
    1. Separar el token en header_b64, payload_b64, sig_b64 (split por ".").
    2. Para cada palabra candidata, calcular HMAC-SHA256 de
       "{header_b64}.{payload_b64}" usando la palabra como clave.
    3. Comparar esa firma (en base64url) con sig_b64 usando una comparacion
       segura (`hmac.compare_digest`), no "==".
"""


def main():
    raise NotImplementedError("Completar: recuperar el secreto del JWT, 100% local.")


if __name__ == "__main__":
    main()
