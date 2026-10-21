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
| **`POST /auth/login`** | Credenciales válidas (tanto payload JSON como `x-www-form-urlencoded` OAuth2) emiten un token JWT utilizable con claims correctos (`sub`, `id`, expiración). | Email en formato admitido extremo (mayúsculas/espacios normalizados) o Content-Type con parámetros extra (`application/json; charset=utf-8`). | Contraseña errónea (401), usuario inactivo (401), usuario inexistente (401), payload malformado/incompleto (422) y Content-Type no soportado (415). |
| **`GET /auth/me`** | Token Bearer válido y vigente devuelve datos del usuario autenticado (`email`, `role`) junto a su perfil de negocio asociado (`name`, `bio`, etc.). | Perfil huérfano/inexistente para un usuario válido (`ProfileNotFoundError` devuelve 404 de negocio) o token cercano al segundo de expiración pero válido. | Token ausente (401), formato de cabecera no Bearer (401), token manipulado/firma inválida (401), token vencido (401) y usuario eliminado de la base de datos tras emisión del token (401). |
| **`POST /auth/forgot-password`** | Email registrado encola en segundo plano (`BackgroundTasks`) el envío del token de recuperación y retorna mensaje seguro estándar sin revelar información sensible. | Email no registrado o cuenta inactiva recibe exactamente la **misma respuesta pública** (`200 OK`) para mitigar ataques de enumeración de usuarios (*User Enumeration*). | Fallo de configuración o indisponibilidad del servicio de correo (`RuntimeError` en settings -> 503 Service Unavailable), o email con formato sintácticamente inválido (422). |
| **`POST /auth/reset-password`** | Token de recuperación válido y vigente actualiza la contraseña del usuario y consume inmediatamente el token, impidiendo su reutilización (*replay protection*). | Contraseña nueva en la longitud mínima permitida (8 caracteres) y caracteres especiales variados. | Token manipulado o inexistente (400), token ya consumido/expirado (400), contraseña nueva débil o faltante (422), y fallo de persistencia en almacenamiento (503). |
| **`POST /auth/change-password`** | Usuario autenticado con token válido y contraseña actual correcta cambia exitosamente su contraseña; el nuevo hash es verificable en subsecuentes logins. | Nueva contraseña idéntica a la anterior permitida según contrato, o longitud en frontera exacta de validación (8 caracteres). | Sin token de autenticación (401), contraseña actual incorrecta (400), cuenta inexistente (401), contraseña nueva que no cumple requisitos (422), y fallo de I/O en almacenamiento (503). |

---

## 3. Delimitación y Análisis de TypeScript / Jest

De acuerdo con las instrucciones de `bullet-proof.md`:
> *"Primero identificar si existen funciones/utilidades TypeScript relacionadas con autenticación (generación/validación de tokens, hash de contraseñas, helpers auth). No añadir pruebas irrelevantes a código que no exista. Si aplica, configurar Jest... Si no existen, documentarlo y justificarlo en el plan."*

### Auditoría Exhaustiva de la Superficie Frontend
Se auditaron todos los proyectos bajo la carpeta `uis/`:
1. **`uis/talent-pipeline-tracker` (Next.js 16 + React 19 + TypeScript)**:
   - `lib/api.ts` y `lib/nexova-api.ts`: Clientes HTTP estándar que consumen la API de FastAPI mediante `fetch`. No contienen lógica criptográfica, parsing de firmas ni derivación de contraseñas.
   - `lib/nexova-auth-routes.ts`: Contiene únicamente dos helpers de navegación:
     ```typescript
     export function isNexovaPublicPath(pathname: string): boolean;
     export function isNexovaProtectedPath(pathname: string): boolean;
     ```
     Estas funciones verifican cadenas estáticas de rutas (`/login`, `/register`, etc.) para guardias de interfaz.
   - `types/auth.ts`: Declaraciones puras de tipos e interfaces TypeScript sin lógica ejecutable.
   - `package.json`: No incluye `jest` ni configuraciones de testing unitario para React.
2. **`uis/backoffice` y `uis/website`**: Interfaces web HTML/CSS/Vanilla JS estáticas.

### Justificación Arquitectónica
- **Centralización Backend**: Toda la lógica de negocio sensible (hashing seguro de contraseñas mediante bcrypt, verificación de salt, emisión, firma HMAC-SHA256 y expiración de tokens JWT, almacenamiento transaccional en TinyDB y mitigación de fugas de información) reside de forma intencional y exclusiva en la API Python/FastAPI (`services/api`).
- **Conclusión Técnica**: No existen funciones criptográficas ni de validación de tokens en TypeScript. Incorporar Jest para probar funciones triviales de comparación de strings inflaría el pipeline innecesariamente y violaría el principio de enfocarse en lógica de negocio real. Por lo tanto, el 100% del alcance de pruebas de AUTH-088 se encuentra implementado y certificado en `services/api/tests/`.

---

## 4. Registro de Cobertura de Código

*Requisito obligatorio de AUTH-088: Cobertura $\ge 70\%$ en el módulo de autenticación.*

### Línea Base Inicial (Antes de extender pruebas)
- `services.api.routers.auth`: **58%** (Insuficiente, < 70%)
- `services.api.auth_dependencies`: **93%**
- `services.api.security`: **97%**
- `services.api.password_reset_service`: **100%**
- **Promedio global auth baseline**: **86%**

### Cobertura Final Certificada (Tras Etapa 2)
```text
Name                        Stmts   Miss  Cover   Missing
---------------------------------------------------------
auth_dependencies.py           30      1    97%   25
password_reset_service.py      68      0   100%
routers\auth.py                94      4    96%   62, 64, 130, 185
security.py                    26      0   100%
---------------------------------------------------------
TOTAL                         218      5    98%
```
- **Resultado en `routers/auth.py`**: Aumento de **58% a 96%** (+38 puntos porcentuales).
- **Cobertura Global del Módulo de Autenticación**: **98%** (superando con amplio margen el requisito del 70%).
- **Ejecución Total**: 204 pruebas pasando limpiamente, 2 skipped (condicionales de SO), 0 fallos.

---

## 5. Evidencia de Flujo Asistido por IA

Durante la auditoría, diseño e implementación, se utilizaron técnicas de razonamiento asistido por IA para detectar casos límite, prevenir regresiones y resolver incompatibilidades de plataforma:

### 1. Resolución de Compatibilidad Multiplataforma (`pass_fds` en Windows)
- **Problema detectado**: El test de integración `test_real_uvicorn_process_serves_login_and_me` fallaba al ejecutarse en Windows (`AssertionError: pass_fds not supported on Windows.` en `subprocess.py:1460`).
- **Diagnóstico y Solución IA**: `pass_fds` es un mecanismo exclusivo de descriptores de archivo en POSIX. Con la asistencia del agente, se aplicó el decorador condicional `@unittest.skipIf(sys.platform == "win32", "pass_fds not supported on Windows")`. Esto garantiza que la batería de pruebas sea 100% reproducible y portable tanto en entornos de desarrollo Windows como en entornos de integración continua Linux/macOS.

### 2. Edge Case de Perfil Huérfano en `GET /auth/me` (`ProfileNotFoundError`)
- **Problema detectado**: Un usuario puede contar con un token JWT válido pero su registro de perfil podría no existir en la base de datos (por inconsistencia o borrado manual de datos).
- **Diseño del caso por IA**: Se diseñó el test `test_me_edge_case_orphan_profile_returns_404` para simular que `get_profile_by_user_id` lance `ProfileNotFoundError`. Se verificó que el router capture la excepción y responda ordenadamente con `404 Not Found` (`{"detail": "Profile not found"}`), evitando respuestas 500 no controladas.

### 3. Mitigación contra Ataques de Enumeración de Usuarios (*User Enumeration*)
- **Problema detectado**: En `POST /auth/forgot-password`, si un atacante prueba distintas direcciones de email, una API mal diseñada revelaría si el usuario existe o no a través del código de estado HTTP o del tiempo de respuesta.
- **Diseño del caso por IA**: Se implementó `test_forgot_password_edge_case_unknown_or_inactive_user_prevents_enumeration`, el cual comprueba que tanto usuarios inexistentes como usuarios inactivos reciban **exactamente la misma respuesta 200 OK con el mensaje estándar** y que **ningún correo sea encolado ni despachado**.

### 4. Protección contra *Replay Attacks* en Recuperación de Contraseña
- **Problema detectado**: Un token de recuperación de contraseña reutilizable permitiría a un atacante con acceso al correo volver a cambiar la clave posteriormente.
- **Diseño del caso por IA**: En `test_reset_password_happy_path`, tras un reseteo exitoso, se intenta inmediatamente una segunda invocación con el mismo token. Se verificó que el sistema responda con `400 Bad Request` (`detail: Invalid password reset token`), garantizando la invalidación transaccional inmediata del token en TinyDB.

### 5. Descubrimiento de Contrato de Claims en JWT
- **Problema detectado**: Durante el desarrollo inicial del happy path de login se intentó validar `claims["role"]`.
- **Diagnóstico IA**: Al auditar `create_access_token` en `services/api/security.py`, la IA constató que el token intencionalmente solo incluye `{"id", "sub", "iat", "exp"}`. El rol del usuario se consulta dinámicamente desde TinyDB en la dependencia `get_current_user` para que revocaciones o ascensos de rol tomen efecto al instante sin esperar la expiración del JWT. La prueba fue ajustada para validar el contrato real y se añadió `test_me_edge_case_role_dynamically_reflected` para verificar la actualización en caliente de roles.
