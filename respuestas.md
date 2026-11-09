# Respuestas — Preguntas para pensar con criterio

## 1. ¿Por qué `balance` e `isVip` no deberían viajar como claims de confianza?

Porque un JWT es un documento que **guarda el cliente**: cualquiera lo lee (es Base64) y, si la firma se rompe o el secreto se filtra, cualquiera lo reescribe. Aun con un secreto fuerte, el token es una **foto del momento del login**: si alice gasta su saldo o le sacan el VIP, el token viejo sigue diciendo lo contrario hasta que vence, y el servidor autoriza con datos desactualizados (se puede "gastar" el mismo saldo varias veces mientras el token viva).

Si el servidor los recalculara desde la base en cada request:

- el token pasa a ser solo una credencial de **identidad** (`sub`), no de estado;
- forjar un token solo serviría para hacerse pasar por un usuario existente (lo que el secreto fuerte evita), pero nunca para inventarse saldo;
- un `sub` que no existe en la base se rechaza (hoy `sub=999` compra igual);
- el saldo se descuenta en la base dentro de una transacción, que es lo que corresponde a una compra real;
- el costo es una consulta por request, que es trivial frente al riesgo.

## 2. Gestión del secreto de firma

- **Longitud y origen:** al menos 256 bits (32 bytes) de un CSPRNG: `secrets.token_bytes(32)` o `openssl rand -base64 48`. Nunca una palabra: `secret123` cayó en 8 intentos.
- **Dónde se guarda:** fuera del código y del repo; variable de entorno inyectada por el orquestador o, mejor, un secret manager (Vault, AWS Secrets Manager, GitLab CI variables *masked/protected*). La app no arranca si la variable no está (fallar cerrado), en vez de usar un valor por defecto.
- **Rotación:** usar `kid` en el header y mantener dos claves activas (la nueva firma, la vieja solo verifica) durante una ventana igual al `exp`; después se retira la vieja. Si se sospecha filtración, rotación inmediata.
- **Alternativa:** pasar a una firma asimétrica (RS256/EdDSA). La clave privada queda solo en el servicio que emite tokens y los demás verifican con la pública: si un servicio verificador se compromete, no puede emitir tokens.

## 3. ¿Qué mejoras priorizaría?

En orden:

1. **Sacar `balance`/`isVip` del token y consultar la base** (y no aceptar `precio` del cliente). Es la causa raíz: aun con todas las demás mejoras, si el servidor confía en el claim, cualquier fuga del secreto es fraude directo.
2. **Secreto fuerte, fuera del código y con rotación.** Sin esto la firma no vale nada: se crackea offline, sin tocar el servidor y sin dejar rastro en sus logs.
3. **`exp` corto** (5–15 min) con refresh token. Acota la ventana de un token robado.
4. **Allowlist de algoritmo** (`algorithms=["HS256"]`, ya presente): evita `alg=none` y la confusión RS/HS. Es barata y ya está, pero hay que mantenerla.
5. **Revocación por `jti`** (lista negra en Redis hasta el `exp`): necesaria para logout y para cortar una sesión comprometida; con `exp` corto la lista es chica.
6. **HTTPS** (obligatorio en cualquier despliegue real, el token es un bearer) y **no guardar el token en `localStorage`**: una cookie `HttpOnly; Secure; SameSite=Strict` evita que un XSS lo robe (con protección CSRF si hace falta).

Prioricé por impacto en *este* caso: 1 y 2 son los que hicieron posible el ataque; 3 a 6 reducen el daño de un robo de token, que acá no fue el vector.

## 4. ¿Qué dato sería razonable incluir en el JWT?

Datos que **no otorgan nada por sí mismos** y que no son secretos si alguien los lee: el identificador del usuario (`sub`, idealmente opaco/UUID), `iat`, `exp`, `jti`, `iss`/`aud`, y a lo sumo algo de presentación (nombre a mostrar, idioma). Lo que los distingue de `balance` es que:

- **no son autoridad**: el servidor los usa para *buscar* la verdad en la base, no como la verdad misma;
- **no cambian** durante la vida del token (un saldo cambia en cada compra);
- **no exponen información sensible** (un saldo es dato financiero/personal y queda legible para cualquiera que vea el token: logs, proxies, el `localStorage`).

Si alguien forja un token con otro `sub`, el problema es la firma (se resuelve con el secreto fuerte); si alguien lee el `sub`, no gana nada.
