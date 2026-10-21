# TESTING.md — Plan de Pruebas y Estrategia de Calidad (AUTH-088)

> **Ticket:** AUTH-088 — Building Bullet-Proof Applications  
> **Prioridad:** Alta  
> **Módulo:** Autenticación y Gestión de Sesiones (`services/api/routers/auth.py`)  
> **Objetivo:** Garantizar la fiabilidad y robustez de la lógica de negocio en todos los endpoints de autenticación, cubriendo caminos felices, casos límite y modos de fallo con un umbral mínimo de cobertura $\ge 70\%$.

---

## 1. Guía de Ejecución de Pruebas

La API principal está desarrollada en FastAPI y reside en `services/api/`. El entorno soporta tanto la herramienta moderna `uv` como `pytest` estándar.

### Comandos de Ejecución

1. **Ejecución estándar con `uv` (Recomendado):**
   ```bash
   cd services/api
   uv run pytest
   ```

2. **Ejecución selectiva de la suite de autenticación:**
   ```bash
   cd services/api
   uv run pytest tests/test_auth_api.py -v
   ```

3. **Ejecución con reporte de cobertura de autenticación:**
   ```bash
   cd services/api
   uv run pytest tests/test_auth_api.py tests/test_password_reset_api.py tests/test_security.py tests/test_password_reset_service.py \
     --cov=services.api.routers.auth \
     --cov=services.api.security \
     --cov=services.api.password_reset_service \
     --cov=services.api.auth_dependencies \
     --cov-report=term-missing
   ```

4. **Ejecución alternativa desde la raíz del monorepo con `python -m pytest`:**
   ```bash
   # En Windows PowerShell:
   $env:PYTHONPATH="."
   python -m pytest services/api/tests/test_auth_api.py -v
   ```

---

## 2. Plan de Pruebas por Endpoint (AUTH-088)

A continuación se detalla la matriz de diseño de pruebas unitarias y de negocio planificada **antes** de la implementación, garantizando que cada endpoint cuente con al menos un camino feliz, un caso límite significativo y un modo de fallo real.

### Matriz de Casos de Negocio

| Endpoint | Camino Feliz (Happy Path) | Caso Límite (Edge Case) | Modo de Fallo (Failure Mode) |
|---|---|---|---|
| **`POST /auth/login`** | Credenciales válidas (tanto payload JSON como `x-www-form-urlencoded` OAuth2) emiten un token JWT utilizable con claims correctos (`sub`, `role`, expiración). | Email en formato admitido extremo (mayúsculas/espacios normalizados) o Content-Type con parámetros extra (`application/json; charset=utf-8`). | Contraseña errónea (401), usuario inactivo (401), usuario inexistente (401), payload malformado/incompleto (422) y Content-Type no soportado (415). |
| **`GET /auth/me`** | Token Bearer válido y vigente devuelve datos del usuario autenticado (`email`, `role`) junto a su perfil de negocio asociado (`name`, `bio`, etc.). | Perfil huérfano/inexistente para un usuario válido (`ProfileNotFoundError` devuelve 404 de negocio) o token cercano al segundo de expiración pero válido. | Token ausente (401), formato de cabecera no Bearer (401), token manipulado/firma inválida (401), token vencido (401) y usuario eliminado de la base de datos tras emisión del token (401). |
| **`POST /auth/forgot-password`** | Email registrado encola en segundo plano (`BackgroundTasks`) el envío del token de recuperación y retorna mensaje seguro estándar sin revelar información sensible. | Email no registrado o cuenta inactiva recibe exactamente la **misma respuesta pública** (`200 OK`) para mitigar ataques de enumeración de usuarios (*User Enumeration*). | Fallo de configuración o indisponibilidad del servicio de correo (`RuntimeError` en settings -> 503 Service Unavailable), o email con formato sintácticamente inválido (422). |
| **`POST /auth/reset-password`** | Token de recuperación válido y vigente actualiza la contraseña del usuario y consume inmediatamente el token, impidiendo su reutilización (*replay protection*). | Contraseña nueva en la longitud mínima permitida (8 caracteres) y caracteres especiales variados. | Token manipulado o inexistente (400), token ya consumido/expirado (400), contraseña nueva débil o faltante (422), y fallo de persistencia en almacenamiento (503). |
| **`POST /auth/change-password`** | Usuario autenticado con token válido y contraseña actual correcta cambia exitosamente su contraseña; el nuevo hash es verificable en subsecuentes logins. | Nueva contraseña idéntica a la anterior permitida según contrato, o longitud en frontera exacta de validación. | Sin token de autenticación (401), contraseña actual incorrecta (400), cuenta inexistente (401), contraseña nueva que no cumple requisitos (422), y fallo de I/O en almacenamiento (503). |

---

## 3. Delimitación y Análisis de TypeScript / Jest

Se realizó una auditoría del frontend en `uis/` (`uis/talent-pipeline-tracker`, `uis/backoffice` y `uis/website`):

1. **Arquitectura de Autenticación**: Toda la lógica criptográfica (hashing de contraseñas con bcrypt/argon2, generación y firma de JWTs con HMAC-SHA256, expiración y verificación de tokens) reside exclusivamente en el backend FastAPI (`services/api`).
2. **Helpers en Frontend**: En `uis/talent-pipeline-tracker/lib/nexova-auth-routes.ts` se encuentran exclusivamente funciones auxiliares de comprobación de rutas públicas vs. protegidas (`isNexovaPublicPath`, `isNexovaProtectedPath`). No existen utilidades cliente de hashing ni parsing criptográfico de tokens en TypeScript.
3. **Decisión Técnica**: La suite Jest no aplica para módulos criptográficos inexistentes en el cliente. La totalidad de la validación de negocio de autenticación se concentra en `services/api/tests/`, cumpliendo con las directrices de alcance de AUTH-088.

---

## 4. Registro de Cobertura de Código

*Requisito obligatorio de AUTH-088: Cobertura $\ge 70\%$ en el módulo de autenticación.*

### Línea Base Inicial (Antes de extender pruebas)
- `services.api.routers.auth`: **58%** (Insuficiente, < 70%)
- `services.api.auth_dependencies`: **93%**
- `services.api.security`: **97%**
- `services.api.password_reset_service`: **100%**
- **Promedio global auth baseline**: **86%**

*(Los resultados finales tras la implementación de la Etapa 2 se registrarán al concluir las ejecuciones de verificación).*

---

## 5. Evidencia de Flujo Asistido por IA

Durante la auditoría inicial se identificaron con asistencia de IA las siguientes consideraciones críticas:

1. **Compatibilidad Multiplataforma (Windows Subprocess `pass_fds`)**:
   - Se detectó que el test `test_real_uvicorn_process_serves_login_and_me` fallaba en Windows debido al parámetro `pass_fds` en `subprocess.Popen`, propio de plataformas POSIX. Se implementó `@unittest.skipIf(sys.platform == "win32", ...)` para garantizar suites reproducibles sin sacrificar cobertura en entornos Unix/CI.
2. **Caso Límite de Perfil Huérfano en `/auth/me`**:
   - La IA identificó la rama donde un usuario posee un token JWT válido pero su registro de perfil fue borrado o no existe en la base de datos (`ProfileNotFoundError` -> `404 Not Found`), escenario límite crucial para la resiliencia de la API.
3. **Mitigación de Enumeración de Usuarios en `/auth/forgot-password`**:
   - Se confirmó que la respuesta ante emails inexistentes debe ser idéntica a la de emails válidos para evitar fugas de información (*timing & status code user enumeration*).
