# SAST, secret detection y análisis de dependencias

> **Nota sobre la plataforma:** todavía no tengo acceso al GitLab de la cátedra, así que el repo está en **GitHub** y el pipeline corre en **GitHub Actions** (`.github/workflows/security.yml`), replicando los jobs de los templates de GitLab: SAST con Semgrep (el mismo motor que usa GitLab para Python) + Bandit, y secret detection con **la imagen oficial del analizador de GitLab** (`registry.gitlab.com/security-products/secrets:6`), que genera exactamente el mismo `gl-secret-detection-report.json`. El `.gitlab-ci.yml` con los `include` pedidos ya está en la raíz para cuando el repo se migre.

## Pipeline

| Job | Qué corre | Reporte (artifact) | ¿Corta el pipeline? |
|---|---|---|---|
| `test` | `pytest -q` (incluye el ataque completo) | — | Sí, si fallan los tests |
| `sast` | Semgrep (`p/security-audit`, `p/python`, `p/secrets`) + Bandit | `gl-sast-report.json`, `bandit-report.json` | No: igual que el SAST de GitLab, informa (el código es vulnerable a propósito) |
| `secret_detection` | Analizador de secretos de GitLab (Gitleaks + reglas de GitLab) sobre el árbol del commit | `gl-secret-detection-report.json` | **Sí**: si encuentra un secreto, el pipeline falla |
| `dependency_scanning` | `pip-audit -r server/requirements.txt` | `gl-dependency-scanning-report.json` | No |

![Pipeline en verde con los jobs sast y secret_detection](capturas/8-pipeline-verde.png)

Equivalente GitLab (`.gitlab-ci.yml`):

```yaml
include:
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Secret-Detection.gitlab-ci.yml
  - template: Jobs/Dependency-Scanning.gitlab-ci.yml
```

## Análisis local (antes de subir)

Todas las herramientas corren contra la copia local; solo bajan reglas / bases de vulnerabilidades. El código no se manda a ningún servicio (`semgrep --metrics=off`, sin login).

| Categoría | Comando |
|---|---|
| SAST | `bandit -r server -x server/.venv,server/tests` |
| SAST | `semgrep scan --metrics=off --config p/security-audit --config p/python --config p/secrets --exclude .venv server/` |
| Secretos | `gitleaks git . -v` (todo el historial) / `gitleaks git --staged .` (antes de commitear) / la imagen `registry.gitlab.com/security-products/secrets:6` en Docker (mismo analizador que el pipeline) |
| Dependencias (SCA) | `pip-audit -r server/requirements.txt` |

![SAST local](capturas/5-sast-local-bandit-semgrep.png)
![Secretos y dependencias en local](capturas/6-secretos-y-dependencias-local.png)

### Resultados y clasificación

| # | Herramienta | Archivo:línea | Regla | ¿Verdadero positivo? | Comentario |
|---|---|---|---|---|---|
| 1 | Semgrep | `server/app/jwt_utils.py:28` | `jwt-python-hardcoded-secret` (CWE-522) | **Sí** | Es exactamente la falla del desafío: el secreto que crackeamos |
| 2 | Bandit | `server/app/jwt_utils.py:9` | B105 hardcoded password | **Sí** | El mismo secreto, visto desde la asignación |
| 3 | Semgrep / Bandit | `server/wsgi.py:6` | `app.run(host="0.0.0.0")` / B104 | Sí, de bajo impacto | Expone el server de desarrollo en todas las interfaces; para el lab debería ser `127.0.0.1` |
| 4 | Bandit | `server/tools/crack_local.py:83` | B105 hardcoded password `'-'` | **No** (falso positivo) | Es el valor `-` que significa "leer de stdin"; Bandit lo marca porque se compara con una variable llamada `token` |
| — | Secret detection (Gitleaks) | — | — | Falso negativo | `secret123` no tiene la entropía ni el formato de ningún proveedor conocido: ni Gitleaks ni el analizador de GitLab lo ven. Por eso conviene combinar secret detection con SAST, que sí lo encontró por contexto (`jwt.encode(..., SECRET)`) |
| — | pip-audit | — | — | — | Sin CVEs conocidas en `flask`, `PyJWT`, `pytest` a la fecha |

**Lo que ninguna herramienta encontró** (revisión manual): la confianza en `balance`/`isVip` del token y en `precio` del body en `routes.py` (CWE-602). Son fallas de **lógica de negocio**: no hay una función peligrosa ni un patrón sintáctico que buscar, así que el SAST no las ve. Esa es la principal limitación del análisis estático.

## Prueba de secret detection con credencial falsa

**Primer hallazgo, un falso positivo:** al correr por primera vez el analizador de GitLab (en local, antes de subir) marcó `AWS access token` en `README.md`: es la clave de ejemplo de la documentación de AWS que trae el propio enunciado (`AKIAIOSFODNN7…EXAMPLE`). No es una credencial, así que excluí ese archivo con `SECRET_DETECTION_EXCLUDED_PATHS: "README.md"` (variable soportada por el template). Por la misma razón, en este documento la clave aparece cortada.

**Prueba** (rama `test/secret-detection`, nunca mergeada a `main`):

1. Agregué `server/app/config_prueba.py` con `AWS_SECRET_ACCESS_KEY = "<la clave de ejemplo de la consigna>"`.
2. **En local**: el `gitleaks` "pelado" **no** la reporta, porque tiene en su allowlist las claves de ejemplo de AWS (terminan en `EXAMPLE`). El analizador de GitLab **sí** la reporta: usa Gitleaks como motor, pero con el ruleset propio de GitLab, que no tiene esa excepción. Es una diferencia de configuración entre herramientas que vale la pena conocer.
3. **En el pipeline**: el job `secret_detection` la reportó (`AWS access token` en `server/app/config_prueba.py:1`) y falló.
4. La borré en otro commit y el job volvió a verde.

**Pero la credencial sigue en el historial.** El job analiza el árbol del último commit, así que después del borrado ya no la ve; sin embargo, `git log -p` la sigue mostrando y cualquiera que haya clonado la rama la tiene. Borrarla del código no la "des-filtra": si hubiese sido real, lo correcto es **revocarla/rotarla** en AWS primero y recién después limpiar el historial (`git filter-repo`) o, como hice acá, descartar la rama.

![Prueba local con la credencial falsa](capturas/7-prueba-credencial-falsa-local.png)
![Pipeline de la rama de prueba marcando la credencial](capturas/9-pipeline-secret-detection-rama-prueba.png)

## Herramientas elegidas

| Herramienta | Para qué sirve | Por qué la elegí |
|---|---|---|
| **Semgrep** | SAST multilenguaje por patrones/flujo: inyección, crypto débil, secretos de JWT, configuraciones de Flask | Es el analizador que usa el template SAST de GitLab para Python, así que lo que veo en local es comparable con el pipeline. Tiene una regla específica para secretos JWT hardcodeados, justo la falla del desafío. Con `--metrics=off` no manda nada afuera |
| **Bandit** | SAST específico de Python (AST): `eval`, `subprocess` con shell, hashes débiles, passwords hardcodeados, bind a `0.0.0.0` | Corre 100 % offline, sin configuración, muy rápido; complementa a Semgrep con reglas propias de Python |
| **Gitleaks** / **analizador de secretos de GitLab** | Detección de secretos (API keys, tokens, claves privadas) en archivos y en el historial de git | Gitleaks es binario único, sin red, y sirve como pre-commit (`--staged`); el analizador de GitLab es Gitleaks con las reglas de GitLab, y lo uso en el pipeline para tener el mismo reporte que daría GitLab |
| **pip-audit** | SCA: compara `requirements.txt` contra la base de vulnerabilidades de PyPI/OSV | Herramienta oficial de PyPA, solo necesita el `requirements.txt` y descarga la base de CVEs, no sube el código |
