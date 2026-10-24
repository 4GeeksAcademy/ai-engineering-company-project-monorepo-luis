# Auditoría Inicial – Monorepo Contenedorización

## Estado del repositorio
- **Rama actual:** `docs/docker-contenedores` (tracking `origin/docs/docker-contenedores`).
- **Cambios locales sin commitear:** varios archivos modificados en `uis/backoffice/` y varios archivos nuevos sin seguir (`??`).

## Estructura encontrada vs. requerimientos
| Ruta | Observado | Requerido por README oficial |
|------|-----------|------------------------------|
| `uis/website/` | Web estática (HTML, assets). No hay `package.json`, no es Next.js. | Se indica que debe ser una aplicación Next.js (puertos 3000 & 3001). |
| `uis/backoffice/` | HTML/CSS/JS estáticos. No hay `package.json`, no es Next.js. | Igual que arriba, se espera Next.js. |
| `uis/talent-pipeline-tracker/` | Aplicación Next.js completa con `package.json` y scripts (`dev`, `build`, `start`). | No está mencionada en los requisitos, pero es la única app Next.js real. |
| `services/api/` | FastAPI (`main.py`, `requirements.txt`, `uv.lock`). | Backend FastAPI esperado, ubicación correcta. |
| `.gitignore` (raíz) | Ignora `.env`, `.env.*`, artefactos Python/Node. | Coincide con buenas prácticas. |

## Diferencias críticas
1. **Frontend esperado vs. real** – El README de la tarea menciona dos aplicaciones Next.js (`website` y `backoffice`). En el checkout actual esas carpetas son solo estáticas. Solo hay una app Next.js (`talent-pipeline-tracker`). Necesitamos confirmar con el tech‑lead si:
   - Adaptamos los UI estáticos a contenedores simples (ej.: servir con `http-server`/`nginx`).
   - O bien creamos wrappers/convertimos esas carpetas a Next.js, o usamos la app existente como referencia.
2. **Ubicación de dependencias del backend** – El Dockerfile deberá apuntar a `services/api/requirements.txt`, no a `services/requirements.txt` como sugiere la guía.

## Decisiones pendientes
- **¿Servir UI estática o migrar a Next.js?**
- **Confirmar variables de entorno necesarias** (por ejemplo, puertos, base de datos). 

> **Acción:** Documentar estas preguntas en el issue interno y obtener respuesta antes de continuar con los Dockerfiles.

---

*Este informe será versionado en `docs/auditoria-inicial.md` y sirve como base para las siguientes etapas.*
