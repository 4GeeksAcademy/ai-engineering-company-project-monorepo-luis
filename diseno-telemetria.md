# Diseño del plan de telemetría de Nexova

> Instrucciones del proyecto de 4Geeks Academy para el monorepo de la compañía. Este documento reúne el reto, las instrucciones completas de trabajo, las métricas obligatorias específicas de Nexova, los criterios de evaluación y la entrega.
>
> **Proyecto oficial:** [Diseño del plan de telemetría de tu compañía — README en español](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-telemetry-plan/README.es.md)
> **Briefing obligatorio de Nexova:** [nexova-BRIEFING.es.md](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/contexts/06-telemetry-data-pipelines/telemetry/nexova-BRIEFING.es.md)
>
> **Antes de diseñar:** leer completo el briefing de Nexova. Sus métricas, entidades, identificadores y restricciones son fuente obligatoria; no deben sustituirse por ejemplos genéricos.

---

## 🎯 Reto

Nexova es una consultora de RRHH con tres líneas de negocio: headhunting, outsourcing de soporte al cliente y formación corporativa. El sistema de inventario gestiona material de formación y certificación, así como kits de incorporación (laptops, credenciales y manuales) para nuevas contrataciones y agentes outsourced.

El sistema existente usa un backend FastAPI con autenticación y un modelo relacional en Supabase. **El stock nunca se modifica directamente:** toda variación debe proceder de una orden de entrada o salida trazable a un usuario.

Operaciones y gestión necesitan información accionable sobre el sistema, no solo métricas de inventario: también autenticación, rendimiento, errores y navegación del backoffice. El entregable es un diseño exhaustivo y preciso que otro desarrollador pueda instrumentar sin aclaraciones. **En esta tarea no se escribe código de instrumentación.**

Cada evento debe tener una razón. Usa la regla:

> “Capturamos `[event_type]` porque necesitamos saber `[hipótesis]`, lo que nos permite tomar la decisión `[decisión concreta]`.”

Si no puedes completar esa frase con una hipótesis y una decisión útil, no incluyas el evento.

### Conceptos requeridos

- **Batch vs. stream:** stream cuando la decisión o respuesta operativa necesita datos en segundos; batch cuando es suficiente procesarlos periódicamente. Justifica por urgencia de negocio u operación.
- **Event Envelope:** estructura común para todos los eventos: `eventId` único, `timestamp` ISO 8601, `sessionId`, `userId`, `event_type` con taxonomía `entidad_acción`, `schemaVersion`, `requestId` de correlación frontend–backend–logs y `properties` con el payload específico.

---

## 🏢 Contexto obligatorio de Nexova

### Entidades del inventario

| Entidad / campo | Significado |
|---|---|
| `Product` | Material formativo o de incorporación, por ejemplo kit de certificación en ventas B2B, manual de onboarding de soporte, credencial o laptop temporal. Categorías: `training_kit`, `certification`, `onboarding_equipment`. Cada producto pertenece a un programa o área. |
| `InboundOrder` | Entrada de un lote de material desde un proveedor (imprenta, plataforma de e-learning o proveedor de hardware). |
| `OutboundOrder` | Entrega de un kit o certificado a un cliente, candidato, consultor o agente de soporte. |
| `office` | `valencia` o `miami`. |
| `programme` | Programa al que pertenece el material, por ejemplo `ventas-b2b` o `liderazgo-basico`. |

### Métricas/eventos obligatorios del briefing

Estos cinco eventos son el **mínimo obligatorio**, no el alcance total. Incluye todos en el plan y en `event-schemas.json`:

| `event_type` | Emisión | Hipótesis | Decisión habilitada |
|---|---|---|---|
| `inbound_order_created` | Llega un lote nuevo de material de formación o incorporación desde un proveedor. | Saber cuánto material se produce/compra, para qué programa y con qué costo. | Planificar producción de material según demanda esperada de matrículas (Elena, L&D). |
| `outbound_order_created` | Se entrega un kit o certificado a un cliente, candidato, consultor o agente. | Saber qué programas consumen más material y a qué ritmo. | Anticipar reposición antes de una ola de matrículas (Elena, L&D). |
| `stock_threshold_triggered` | El stock de un ítem cae por debajo del mínimo configurado. | Saber con qué frecuencia un programa se queda sin material disponible. | Ajustar el mínimo o acelerar la reimpresión/reproducción. |
| `direct_stock_edit_rejected` | El sistema rechaza un intento de cambiar stock directamente, fuera de una orden. | Saber si el personal intenta saltarse la trazabilidad. | Reforzar capacitación o permisos en la oficina con más intentos (Patricia, RRHH). |
| `kit_cost_variance_detected` | El costo unitario de una orden de entrada supera el umbral de variación respecto al histórico del mismo material/proveedor (ejemplo de umbral: 10%). | Detectar aumentos de precio anómalos de proveedores. | Alertar a Elena y Laura para renegociar o buscar alternativa. |

Para eventos de inventario, el briefing establece como propiedades mínimas —además del envelope— `office` (`valencia`/`miami`), `product_id`, `product_category` (`training_kit`/`certification`/`onboarding_equipment`), `programme_id`, `quantity` y `currency` (`EUR`/`USD`). Define claramente cuáles aplican a cada evento y documenta cualquier campo condicional, sin romper la consistencia del esquema.

**Privacidad y reglas financieras:** no incluyas nombres de candidatos, clientes ni consultores en `properties`; usa identificadores de programa o kit, nunca datos personales. Registra importes en la moneda de la oficina (`EUR` en Valencia y `USD` en Miami); no conviertas monedas dentro de la capa de telemetría. No mezcles idioma de interfaz con oficina: son dimensiones independientes.

---

## 🌱 Cómo iniciar

1. Trabaja en esta copia del monorepo de la compañía asignada; no crees ni forkees otro repositorio.
2. Lee completamente el briefing de Nexova y localiza sus métricas obligatorias, entidades y restricciones.
3. Crea `docs/telemetry/` en el monorepo.
4. Coloca en esa carpeta los dos entregables: `telemetry-plan.md` y `event-schemas.json`.
5. No levantes un servidor nuevo ni escribas código de instrumentación para este proyecto: hoy se diseña la documentación que el equipo implementará después.

---

## 💻 Qué debes hacer

### Fase 1 — Catálogo exhaustivo de oportunidades de datos

- [ ] Revisa el briefing y enumera las métricas obligatorias de Nexova; incorpóralas todas al plan como piso, no como techo.
- [ ] Mapea el flujo de gestión de inventario desde el acceso de un usuario autenticado hasta completar una orden de entrada o salida. Identifica **al menos cinco puntos de instrumentación** a lo largo del flujo. Deben incluir intentos de modificación directa del stock (rechazados), validaciones fallidas y activaciones del umbral mínimo.
- [ ] Explora otras secciones del backoffice sin limitarte a un mínimo: autenticación (intentos fallidos, sesiones expiradas, credenciales incorrectas), rendimiento (latencia de API y carga), errores de frontend no capturados y navegación (secciones visitadas y flujos abandonados), además de cualquier oportunidad de negocio/técnica relevante.
- [ ] Para cada oportunidad, documenta la hipótesis y la decisión concreta con la frase: “Capturamos `[event_type]` porque necesitamos saber `[hipótesis]`, lo que nos permite tomar la decisión `[decisión]`.” Descarta los puntos que no puedas justificar.
- [ ] Clasifica cada evento como **obligatorio (BRIEFING)** o **oportunidad identificada**.
- [ ] El catálogo adicional debe ser amplio y fundamentado; no basta con cumplir el mínimo de eventos.

### Fase 2 — Diseño del Event Envelope y esquemas

- [ ] Define el envelope estándar e incluye en **todos** los eventos: `eventId`, `timestamp` en ISO 8601, `sessionId`, `userId`, `event_type`, `schemaVersion`, `requestId` y `properties`.
- [ ] Diseña los esquemas de todas las métricas obligatorias del briefing **más al menos ocho eventos adicionales** de tu catálogo, cubriendo por lo menos **tres categorías** (p. ej., negocio/inventario, autenticación, rendimiento, errores y navegación).
- [ ] Usa la taxonomía `entidad_acción` para cada `event_type`, con verbos consistentes. Ejemplos: `inbound_order_created`, `stock_threshold_triggered`, `direct_stock_edit_rejected`, `session_expired`, `api_latency_recorded`.
- [ ] Para cada evento, especifica el tipo, descripción y sus propiedades con nombre, tipo de dato, obligatoriedad (requerida/opcional) y descripción.
- [ ] Define un **allowlist explícito de propiedades por evento**. No se permite ninguna propiedad fuera de la lista aprobada.
- [ ] Identifica datos sensibles o PII. Si un evento los necesita, documenta cómo se anonimiza o sanitiza antes de emitirlo; evita capturar PII innecesaria y cumple la prohibición de nombres del briefing.
- [ ] Exporta los esquemas a `docs/telemetry/event-schemas.json` en un formato validable (JSON Schema draft-07 o estructura personalizada cuya forma quede documentada). Debe ser JSON válido y coincidir con el plan Markdown.

### Fase 3 — Estrategia de entrega

- [ ] Decide para cada evento si se procesa en **stream** o **batch**.
- [ ] Justifica cada elección por la urgencia de la decisión que alimenta o por la necesidad de detección operativa rápida; no la justifiques por preferencia técnica.
- [ ] Documenta estrategia de throttle/debounce para cualquier evento de alta frecuencia, indicando ventana, criterio de agregación/limitación y cómo se evita perder señales relevantes.
- [ ] Incluye una sección de **riesgos y exclusiones**: eventos considerados y descartados con sus razones, y datos que no se capturarán por privacidad o costo.
- [ ] Asegura que el diseño permita agregar métricas por oficina y programa sin exponer identidades personales.

---

## ✅ Qué vamos a evaluar

- [ ] Están presentes todas las métricas obligatorias del `empresa-BRIEFING.md` de Nexova, correctamente identificadas como obligatorias.
- [ ] El plan cubre de forma amplia oportunidades tanto **técnicas** (errores, rendimiento, autenticación, navegación) como **de negocio**; no se limita a un mínimo cumplido por trámite.
- [ ] Cada evento tiene una hipótesis y una decisión de negocio u operación que lo justifican; no hay eventos “por si acaso”.
- [ ] El Event Envelope es consistente en todos los eventos e incluye al menos `eventId`, `timestamp` (ISO 8601), `sessionId`, `userId`, `event_type` en formato `entidad_acción`, `schemaVersion`, `requestId` y `properties`.
- [ ] Cada evento tiene un allowlist de propiedades documentado; solo se permiten claves explícitamente listadas.
- [ ] `event-schemas.json` es válido y consistente con `telemetry-plan.md`.
- [ ] Las decisiones stream/batch están justificadas por la urgencia del negocio u operación, no por preferencia técnica.
- [ ] Los datos sensibles o PII están identificados y cuentan con estrategia de anonimización/sanitización; se respeta la prohibición de datos personales del briefing.
- [ ] La sección de riesgos y exclusiones demuestra pensamiento crítico y justifica las decisiones de no capturar datos.
- [ ] El plan es suficientemente preciso para que otro desarrollador lo instrumente sin aclaraciones.

---

## 📦 Entrega del proyecto

1. Deben existir `docs/telemetry/telemetry-plan.md` y `docs/telemetry/event-schemas.json` en esta copia del monorepo.
2. Crea un Pull Request contra la rama principal del monorepo con el título exacto: **`docs: telemetry design plan`**.
3. En la descripción del PR indica:
   - Número total de eventos diseñados y cuántos son obligatorios del briefing frente a oportunidades identificadas.
   - Categorías cubiertas (negocio, autenticación, rendimiento, errores, navegación, etc.).
   - Una oración que explique la decisión de diseño más difícil.
4. Si el PR se aprueba, intégralo en `main`; si no se aprueba, la funcionalidad no se despliega y conviene resolverlo antes de iniciar el siguiente proyecto para evitar conflictos.

> Este documento de instrucciones se guarda como `diseno-telemetria.md` en la raíz por solicitud del usuario. No sustituye los dos entregables finales ni el Pull Request.
