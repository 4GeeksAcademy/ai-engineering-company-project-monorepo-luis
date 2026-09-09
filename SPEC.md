# Talent Pipeline Tracker — Especificación del Proyecto

## 🏢 Empresa: Nexova

Consultora de recursos humanos y adquisición de talento.
- Fundada en 2011, sede en Valencia + oficina en Miami
- 120 empleados, $8M facturación anual
- Líneas de negocio: headhunting ejecutivo, outsourcing atención al cliente, formación corporativa
- Clientes: empresas medianas de tecnología, retail, servicios financieros
- Stakeholder: **Carmen Ruiz**, Head of Marketing

> La UI debe reflejar el contexto de Nexova: lenguaje de RH, terminología de talento, no nombres técnicos de API.

## 📦 Repositorio

```
Monorepo: https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis.git
Proyecto nuevo en: /uis/talent-pipeline-tracker/
```

## 🛠 Stack

- Next.js App Router + TypeScript
- Tailwind CSS v4
- shadcn/ui
- Solo React hooks (NO Redux, Zustand, Jotai, etc.)

## 🌐 API

Base URL: `https://playground.4geeks.com/tracker/api/v1`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /records | Listar candidatos |
| GET | /records/:id | Detalle candidato |
| PATCH | /records/:id | Actualizar status/stage |
| POST | /records | Crear candidato |
| PUT | /records/:id | Editar candidato |
| GET | /records/:id/notes | Listar notas |
| POST | /records/:id/notes | Añadir nota |
| DELETE | /records/:id/notes/:note_id | Borrar nota |

Env var: `NEXT_PUBLIC_API_URL=https://playground.4geeks.com/tracker/api/v1`

## ✅ Checklist de requisitos (evaluación 4Geeks)

### Vistas y routing
- [ ] Lista de candidatos en `/` con datos de `GET /records`
- [ ] Detalle de candidato en `/candidates/[id]` con `GET /records/:id`
- [ ] Navegación con Next.js App Router (sin recargas completas)

### Lista de candidatos
- [ ] Mostrar: nombre completo, posición, status actual, stage actual
- [ ] Filtro por status y stage con `useSearchParams` (query params)
- [ ] Búsqueda por nombre o email sin recargar página
- [ ] Estados: loading, error, success

### Detalle de candidato
- [ ] Mostrar todos los campos: nombre, email, teléfono, posición, LinkedIn, CV, años experiencia, status, stage, fecha aplicación
- [ ] Control para actualizar status (PATCH /records/:id)
- [ ] Control para actualizar stage (PATCH /records/:id)
- [ ] Lista de notas (GET /records/:id/notes)
- [ ] Añadir nota (POST /records/:id/notes)
- [ ] Borrar nota (DELETE /records/:id/notes/:note_id)

### Gestión de candidatos
- [ ] Formulario para registrar nuevo candidato (POST /records)
- [ ] Formulario para editar candidato (PUT /records/:id)
- [ ] Validación de campos requeridos antes de enviar
- [ ] Feedback de éxito y error después de cada envío

### Estados y async
- [ ] Todas las llamadas API con async/await
- [ ] Cada operación con 3 estados: loading, success, error
- [ ] Después de PATCH/PUT/POST, actualizar UI sin recargar página

### Estructura del código
- [ ] Carpetas: `/components`, `/types`, `/lib` o `/services`
- [ ] Tipos TypeScript para todas las estructuras de datos de la API

---

## 📋 Pasos de implementación

### Paso 1 — Setup inicial

Clonar monorepo, crear proyecto Next.js en `uis/talent-pipeline-tracker/`, instalar shadcn/ui, crear estructura de carpetas, `.env.local` y `.env.example`. Commit: `feat(talent-pipeline-tracker): scaffold Next.js project with shadcn/ui`

### Paso 2 — Tipos TypeScript y API service layer

Crear `types/index.ts` con interfaces para Candidate, Note, Stage, Status. Crear `lib/api.ts` con funciones fetch tipadas para cada endpoint. Commit: `feat(talent-pipeline-tracker): add types and API service layer`

### Paso 3 — Página de lista de candidatos

Implementar `app/page.tsx` con lista de candidatos desde `GET /records`. Incluir filtros por status/stage via `useSearchParams`, búsqueda por nombre/email, estados loading/error. Commit: `feat(talent-pipeline-tracker): candidate list page with filters and search`

### Paso 4 — Página de detalle de candidato

Implementar `app/candidates/[id]/page.tsx`. Mostrar todos los campos del candidato. Controles PATCH para status y stage. Sección de notas (listar, añadir, borrar). Commit: `feat(talent-pipeline-tracker): candidate detail page with status, stage and notes`

### Paso 5 — Formularios: registrar y editar candidato

Formulario de registro (POST /records) en página o modal. Formulario de edición (PUT /records/:id) en detalle. Validación de campos, feedback success/error. Commit: `feat(talent-pipeline-tracker): add candidate register and edit forms`

### Paso 6 — Pulido final y verificación

Verificar que npm run build pasa. Verificar todos los estados async. Verificar que la UI refleja contexto Nexova. Commit final y push. Commit: `chore(talent-pipeline-tracker): final polish and verification`