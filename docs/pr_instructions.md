# Pull Request y cierre del proyecto

## Pasos finales

1. **Abrir un Pull Request**
   - Desde la rama `docs/docker-contenedores` abre un PR hacia `main` en GitHub.
   - En la descripción incluye:
     - Enlace a la rama de trabajo.
     - Resumen de los commits realizados (etapas 1‑4, opcional 5).
     - Captura de `docker compose ps` local (si la tienes) o confirma que la fase 5 es opcional.
     - Enlace al archivo `docs/evidencia-vps.md` (aunque sea vacío o con una nota de que es opcional).

2. **Solicitar revisión**
   - Menciona al tech‑lead/revisor (`@tech‑lead` o el usuario correspondiente) para que apruebe.

3. **Después de la aprobación**
   - Haz merge del PR a `main`.
   - Elimina la rama `docs/docker-contenedores` si ya no es necesaria.

4. **Actualiza el README** (opcional) indicando que el proyecto ya está contenedorizado y que los comandos de desarrollo son:
   ```bash
   docker compose up --build   # Levanta UI y backend
   docker compose down         # Detiene los contenedores
   ```

5. **Cierre del ticket**
   - Marca la tarea como completada en el sistema de gestión de proyecto (Jira, Trello, etc.).

---

## Notas sobre la Etapa 5 (despliegue en VPS)
- La entrega indica que el despliegue al VPS es **opcional**. Si decides no hacerlo, simplemente indica en la descripción del PR que la fase 5 no se completó por ser opcional, pero que el stack funciona localmente.

---

*Este documento está listo para ser versionado y usado como guía para cerrar el proyecto.*

