# Building Bullet-Proof Applications — Guía del proyecto

> Guía de trabajo para **Building Bullet-Proof Applications** de 4Geeks Academy. Resume las instrucciones oficiales, incluyendo **«Qué debes hacer»** y **«Qué vamos a evaluar»**, y las adapta al monorepo y la API existentes. La tarea consiste en añadir pruebas unitarias de lógica de negocio a la API de autenticación; no reemplaza la entrega de **Gestión de Errores** ni pide crear otra aplicación.

## Fuente y estado de 4Geeks

- Cohorte: **Error handling, debugging and testing** (`error-handling-debugging-and-testing`).
- Actividad: **Error Handling: Building Bulletproof Applications**, tipo `EXERCISE`, ID `1003160`, slug `error-handling-building-bulletproof-application-en`; estado observado: `PENDING`.
- README oficial: [español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-building-bullet-proof-applications/README.es.md) · [inglés](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-building-bullet-proof-applications/README.md).
- Repositorio de trabajo: `https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis.git`.

## Reto y objetivo

La API de autenticación debe contar con pruebas que generen confianza contra regresiones. Cubrir la lógica de negocio en los endpoints de autenticación en condiciones normales, casos límite y escenarios de fallo. No escribir pruebas cuyo objetivo sea verificar serialización HTTP o detalles internos del framework: probar qué decide la lógica de la aplicación.

El ticket del README es **AUTH-088**, de prioridad alta. Los requisitos obligatorios incluyen cobertura de todos los endpoints de autenticación, al menos un camino feliz, un caso límite y un modo de fallo por endpoint, pytest para FastAPI y Jest para lógica de TypeScript cuando corresponda, ejecución limpia de las suites y al menos 70% de cobertura del módulo de autenticación. El entregable incluye el plan y las instrucciones en `TESTING.md`.

## Contexto del monorepo

Se inspeccionó la rama principal del repo y existen:

- API Python/FastAPI en `services/api/`.
- Rutas de autenticación en `services/api/routers/auth.py`:
  - `POST /auth/login`
  - `GET /auth/me`
  - `POST /auth/forgot-password`
  - `POST /auth/reset-password`
  - `POST /auth/change-password`
- Modelos y lógica auth en `services/api/auth_models.py`, `auth_dependencies.py`, `passwords.py`, `security.py`, `password_reset_service.py`, `user_service.py` y `email_service.py`.
- Suite existente bajo `services/api/tests/`, con `test_auth_api.py`, `test_auth_models.py`, `test_security.py`, `test_password_reset_api.py`, `test_password_reset_service.py` y otras suites. Se debe extender/ordenar este conjunto en lugar de duplicar ciegamente lo ya cubierto.
- Configuración Python en `services/api/pyproject.toml`. Los endpoints de autenticación de la API principal están en `/auth/*`; verificar si hay lógica de auth TypeScript reutilizable antes de decidir si aplica Jest.

El README solicita crear `tests/` en la raíz del proyecto FastAPI. En este monorepo la API vive en `services/api/` y ya mantiene sus pruebas en `services/api/tests/`; conservar esa organización del proyecto salvo que la configuración existente obligue a otra cosa. Documentar la ruta concreta en `TESTING.md`.

## Qué debes hacer

### 1. Plan de pruebas y `TESTING.md`

- [ ] Crear `TESTING.md` en la raíz del proyecto (raíz del monorepo).
- [ ] Documentar comandos para ejecutar cada suite y explicar brevemente qué cubre cada una y por qué.
- [ ] Antes de escribir o añadir pruebas, anotar por endpoint los caminos felices, casos límite y modos de fallo que se planean cubrir.
- [ ] Documentar resultados reales de cobertura obtenidos al ejecutar las pruebas; no inventar porcentajes.
- [ ] Explicar un caso de prueba identificado con ayuda de IA o un bug existente que la batería detectó, como evidencia del flujo de trabajo asistido por IA.

### 2. FastAPI — pytest (requisito principal)

- [ ] Mantener/crear la suite bajo `services/api/tests/` (la ubicación actual del proyecto).
- [ ] Asegurar módulo(s) de pruebas para **todos** los endpoints de autenticación: login, usuario actual, solicitar recuperación, restablecer contraseña y cambiar contraseña.
- [ ] Para **cada endpoint**, incluir como mínimo:
  - [ ] **Camino feliz:** entrada válida y decisión/resultado funcional esperado.
  - [ ] **Caso límite:** frontera significativa, por ejemplo campos vacíos, usuario duplicado, longitud límite, token en el límite de expiración o cuenta inactiva.
  - [ ] **Modo de fallo:** credenciales inválidas, token vencido/malformado, datos inválidos, fallo de persistencia o proveedor externo, según el endpoint.
- [ ] Probar lógica de negocio y efectos relevantes (p. ej. token aceptado/rechazado, cambio de contraseña, invalidez/reutilización de token); no limitarse a validar el formato de la respuesta HTTP.
- [ ] Ejecutar `uv run pytest` y asegurar que todas las pruebas pasan limpiamente desde la raíz del proyecto/API conforme a su configuración. Si el comando debe lanzarse desde `services/api`, documentarlo explícitamente.
- [ ] Ejecutar `uv run pytest --cov` y alcanzar al menos **70% de cobertura del módulo de autenticación**. Identificar en `TESTING.md` el módulo y el comando exactos usados para calcularla.
- [ ] Aislar datos y estado entre pruebas; emplear usuarios y credenciales sintéticos, almacenamiento temporal y dobles/mocks para servicios externos. No usar datos reales ni secretos.

### 3. Matriz inicial de cobertura

La siguiente matriz es un plan recomendado, no una afirmación de que una prueba específica falte: verificar primero la cobertura de la suite existente y completar vacíos.

| Endpoint | Camino feliz | Caso límite | Modo de fallo |
|---|---|---|---|
| `POST /auth/login` | credenciales válidas producen token utilizable | payload/campo ausente o formato de entrada admitido en el límite | contraseña incorrecta, usuario inexistente/inactivo o payload malformado |
| `GET /auth/me` | token válido identifica usuario y perfil correctos | usuario cambia de rol/estado o perfil no disponible, según contrato | token ausente, inválido, vencido o usuario eliminado |
| `POST /auth/forgot-password` | cuenta conocida procesa solicitud sin revelar si existe | email desconocido/inactivo conserva respuesta pública equivalente; email en límite válido | configuración, almacenamiento o envío externo falla sin filtrar secretos |
| `POST /auth/reset-password` | token vigente cambia contraseña y no permite reutilización | token en el límite temporal o contraseña en límite de validación | token expirado/manipulado/ausente o fallo al persistir |
| `POST /auth/change-password` | usuario autenticado con contraseña actual puede cambiarla | contraseña nueva en límites aceptados/rechazados | sin autenticación, contraseña actual incorrecta, cuenta inexistente o fallo de persistencia |

Ajustar estos casos al contrato y reglas reales del código; si un endpoint no tiene uno de estos escenarios, justificarlo en el plan.

### 4. TypeScript — Jest, si corresponde

- [ ] Primero identificar si existen funciones/utilidades TypeScript relacionadas con autenticación (generación/validación de tokens, hash de contraseñas, helpers auth). No añadir pruebas irrelevantes a código que no exista.
- [ ] Si aplica, configurar Jest (`jest.config.ts` o `.js`) en la raíz del proyecto TypeScript correspondiente.
- [ ] Cubrir cada utilidad auth con al menos camino feliz y modo de fallo.
- [ ] Asegurar que `jest --coverage` pasa y documentar el comando y alcance en `TESTING.md`.

### 5. Flujo asistido por IA

- [ ] Pedir al agente sugerencias de casos límite y revisar críticamente las propuestas antes de aceptarlas.
- [ ] Usar IA para ayudar con boilerplate solo después de decidir qué comportamiento se quiere verificar.
- [ ] Leer y entender cada test generado antes de incluirlo.
- [ ] Documentar en `TESTING.md` al menos un caso sugerido con IA o un bug real detectado por las pruebas y cómo se resolvió.

### 6. Alcance y exclusiones

- [ ] No probar serialización HTTP, tuberías internas ni comportamiento del framework como fin en sí mismo. Aunque algunas pruebas existentes usen `TestClient`, las afirmaciones deben validar decisiones de negocio.
- [ ] No expandir la entrega a características nuevas ajenas a autenticación/testing.
- [ ] No considerar obligatorias las actividades extra de backoffice/frontend para aprobar.

## Actividades extra opcionales

Estas actividades no son obligatorias para aprobar, pero pueden reconocerse si se implementan, ejecutan y documentan correctamente:

- [ ] **API-042 — Backoffice:** escoger al menos dos grupos de endpoints diferentes de autenticación; en cada grupo cubrir camino feliz, caso límite y modo de fallo, y apuntar a **60% de cobertura** en los módulos probados.
- [ ] **FE-019 — utilidades frontend:** identificar al menos tres funciones/helper en Next.js/TypeScript y escribir tests Jest de camino feliz y fallo para cada función.
- [ ] Actualizar `TESTING.md` con los comandos y resultados de cobertura de las suites opcionales.

No comenzar estas extras hasta tener completa y verde AUTH-088.

## Qué vamos a evaluar

- [ ] Existe `TESTING.md` con plan de pruebas, instrucciones de ejecución y resultados de cobertura.
- [ ] `uv run pytest` se ejecuta sin errores y pasan todas las pruebas.
- [ ] Cada endpoint de autenticación cuenta al menos con camino feliz, caso límite y modo de fallo.
- [ ] La cobertura del módulo de autenticación es **≥70%**, acreditada mediante `uv run pytest --cov`.
- [ ] Las pruebas verifican lógica de negocio, no serialización HTTP ni detalles del framework.
- [ ] Si existe lógica de utilidad de autenticación TypeScript, sus pruebas Jest están presentes y pasan.
- [ ] El proceso asistido por IA queda evidenciado en `TESTING.md` mediante caso sugerido o bug encontrado.
- [ ] Los tests tienen nombres claros, estructura consistente y comentarios breves para afirmaciones no obvias.
- [ ] Cobertura y resultados reportados coinciden con ejecuciones reales. El 100% no es requisito: el criterio de los casos importa más que perseguir porcentaje mecánicamente.

## Criterio de terminado

AUTH-088 está terminado cuando el plan precede a la implementación y está en `TESTING.md`, todos los endpoints auth tienen los tres tipos mínimos de caso, pytest pasa, la cobertura de auth alcanza 70% o más, las pruebas cubren lógica real, existe evidencia de revisión asistida por IA y la documentación refleja comandos/resultados reales.

## Entrega

Subir el repositorio actualizado a GitHub con la API existente, las pruebas nuevas y `TESTING.md`, y compartir el enlace según las instrucciones del instructor. Esta guía documenta el encargo; no es en sí el entregable de pruebas ni implica que la actividad ya esté aprobada en 4Geeks.
