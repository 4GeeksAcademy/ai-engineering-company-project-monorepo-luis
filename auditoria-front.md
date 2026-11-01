# Auditoría de Rendimiento Frontend — Nexova

Guía de trabajo para el proyecto **Frontend Performance Audit / Auditoría de Rendimiento Frontend** de 4Geeks Academy, cohorte **Architecture optimization**. Consolida el README oficial, especialmente **«Qué debes hacer»** y **«Qué vamos a evaluar»**, con una revisión inicial del monorepo de Nexova.

> **Precedencia:** README oficial vigente de 4Geeks → estado real del código y configuración de este repositorio → esta guía. Esta guía no sustituye las instrucciones oficiales. Si cambian el README o el repo, actualiza las suposiciones antes de actuar. No inventes resultados Lighthouse ni des por corregido algo sin evidencia.

## Fuentes y tarea

- Cohorte: **Architecture optimization**, ID `1709`, slug `architecture-optimization`.
- Proyecto 4Geeks: **Frontend Performance Audit**, tarea `1008341`, slug `ai-eng-performance-web-vitals`, estado consultado: **PENDING**.
- README oficial en español: [Auditoría de Rendimiento Frontend](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-performance-web-vitals/README.es.md).
- README oficial en inglés: [Frontend Performance Audit](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-performance-web-vitals/README.md).
- Repositorio de trabajo: [ai-engineering-company-project-monorepo-luis](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo-luis).
- Aplicaciones incluidas: sitio público `uis/website/` y backoffice `uis/backoffice/`.

## Objetivo y alcance

Auditar y mejorar con cambios dirigidos los dos frontends existentes de Nexova: el sitio corporativo, cuyo rendimiento influye en experiencia y SEO, y el backoffice usado por el equipo. El ciclo exigido es **medir → analizar → corregir → volver a medir**. No rediseñar ni reescribir las aplicaciones, no cambiar su arquitectura para mejorar artificialmente las métricas y no sacrificar funcionalidad, accesibilidad o mantenibilidad por una puntuación.

El README oficial pide como entregables finales `AUDIT.md`, `REPORT.md` y capturas Lighthouse versionadas en `audit/before/` y `audit/after/`. Este archivo es la guía contextual del proyecto; **no sustituye** esos entregables.

## Auditoría inicial del checkout

Revisado en la rama `main` sincronizada al preparar esta guía. Revalidar antes de implementar, porque el repo puede avanzar.

### Stack y ejecución

- `uis/website/` y `uis/backoffice/` son frontends **estáticos HTML/CSS/JavaScript**, no aplicaciones Next.js ni proyectos Node independientes.
- Sitio público: `index.html`, `application.html`, estilos Tailwind compilados en `assets/css/styles.css`, `assets/js/validation.js` y el Web Component compartido `shared-components.js`.
- Backoffice: `index.html` y `inventory.html`, scripts de incidencias, proveedores, autenticación e inventario, y estilos CSS separados.
- Los READMEs indican `npx --yes serve uis/website -l 5500` y `npx --yes serve uis/backoffice -l 5502`. Para auditar, usar los servidores de producción/equivalentes de producción apropiados para estas apps estáticas; no cambiar a `next dev` ni presentar un servidor de desarrollo como producción.
- No hay `package.json` propio en ninguna de las dos carpetas. El `package.json` de la raíz es para el proyecto TypeScript general y no define un build o start de producción de estos frontends. Confirmar cómo generar el CSS final antes de medir; el README del sitio documenta Tailwind CLI 3.4.17 para compilar `styles.css`.
- El backoffice `inventory.html` presenta un rail de navegación de marcador/comentarios de implementación incompleta, mientras que `index.html` sí tiene navegación extensa. No se debe corregir esto como parte de la auditoría de rendimiento salvo que la revisión demuestre impacto directo y el cambio pueda mantenerse estrictamente dentro de alcance.

### Hallazgos observables para validar con mediciones

Estos son pistas de inspección estática, **no puntuaciones ni diagnósticos confirmados de Lighthouse**:

- `uis/website/assets/img/nexova_hero_image_1784574586596.png` ocupa aproximadamente 504 KiB en el checkout observado. Verificar formato, dimensiones, bytes transferidos y si es el LCP antes de decidir conversión/responsive/compression. Preservar calidad visual y atributos `width`/`height`.
- Las dos páginas públicas cargan Manrope desde Google Fonts mediante un stylesheet externo. Medir el coste/impacto y comprobar carga, renderizado y fallback antes de modificarlo; no quitar tipografía a ciegas.
- `uis/website/index.html` ya marca la imagen hero con `fetchpriority="high"`, `loading="eager"`, `decoding="async"` y dimensiones. No duplicar hints ni aplicar lazy loading al LCP.
- El backoffice contiene varias secciones, scripts y llamadas de red. Medir la página/ruta real más pesada (como mínimo el dashboard; incluir inventario u otra vista compleja si aporta cobertura). No desactivar funciones ni eliminar carga necesaria para maquillar una métrica.
- Hay potenciales repeticiones que se deben verificar durante el análisis: header/footer del sitio público se centralizan en `shared-components.js`; estructura del rail/topbar del backoffice se repite entre `index.html` e `inventory.html`; gestión de URL base y errores HTTP/red aparece tanto en `suppliers.js` como en `incidents.js`. Identificar y documentar **al menos dos casos concretos**, con ubicaciones y propuesta de extracción, en `AUDIT.md`. Confirmar solapamiento real y riesgo antes de refactorizar.
- En `inventory.html`, el comentario indica explícitamente que el rail se omitió como placeholder. Distinguir deuda funcional/consistencia de un hallazgo de rendimiento.

## Reglas de medición

- Toda ejecución de Lighthouse, antes y después, debe dirigirse a los frontends servidos en **modo producción**. Para estas aplicaciones estáticas, validar los archivos construidos/compilados que se sirven y evitar HMR/dev servers. Anotar el comando y configuración exactos.
- Fijar URLs, rutas, dispositivos, navegador, perfil de red/CPU y condiciones comparables para antes/después. Reducir ruido: realizar varias corridas comparables cuando sea posible y anotar variación; no comparar métricas de entornos diferentes.
- Auditar como mínimo el sitio corporativo en escritorio y móvil (home y páginas complejas pertinentes) y el backoffice en su vista principal o vista con más carga. Para backoffice, registrar los cuatro scores aunque SEO no sea relevante en una página noindex/privada; explicar la aplicabilidad en lugar de omitirlo en silencio.
- Registrar **Performance, Accessibility, Best Practices y SEO** para cada URL y modo. Capturar también métricas/diagnósticos pertinentes, como LCP, CLS, INP/TBT y TTFB, y las oportunidades/hallazgos vinculados a las causas raíz.
- Antes de cualquier corrección, guardar capturas legibles de los informes en `audit/before/`. Después, guardar capturas equivalentes en `audit/after/`. Incluir nombres de archivo que identifiquen aplicación, ruta y viewport; no incluir datos sensibles.
- No rellenar valores estimados. En `AUDIT.md` y `REPORT.md`, separar resultados medidos, observaciones de código e hipótesis por validar. Si una corrida falla, documentar la limitación, no fabricar captura ni puntuación.

## Skills de agente opcionales

El CTO permite, si hacen falta, instalar una o más de estas skills para guiar el trabajo:

- [core-web-vitals](https://www.skills.sh/addyosmani/web-quality-skills/core-web-vitals)
- [performance](https://www.skills.sh/addyosmani/web-quality-skills/performance)
- [web-perf (Cloudflare)](https://www.skills.sh/cloudflare/skills/web-perf)

Si se usan: inspeccionar fuente/alcance antes de instalar, ejecutar su orientación en ambos frontends y dejar evidencia concreta de qué recomendaciones identificó, cuáles se aceptaron/rechazaron y por qué. La instalación es opcional según la instrucción original; no afirmar uso si no se instaló/ejecutó. No introducir dependencias que cambien arquitectura o expongan datos del backoffice.

## Qué debes hacer

### 1. Preparar y medir antes de cambiar código

- [ ] Leer este archivo, `AGENTS.md`, `CONTEXT.md`, los README de `uis/`, `uis/website/` y `uis/backoffice/`, y ambos README oficiales del proyecto.
- [ ] Revisar rama, `git status`, diff y estado actual de las apps. Mantener trabajo aislado en una rama; no sobrescribir trabajo ajeno.
- [ ] Confirmar cómo construir/servir ambos frontends en modo producción. Para el sitio, verificar el build de Tailwind documentado; para las páginas estáticas del backoffice, servir los archivos del checkout sin servidor hot-reload. Anotar comandos y URLs.
- [ ] Ejecutar Lighthouse primero en el sitio público, al menos home en escritorio y móvil, y otra vista compleja si corresponde. Registrar las cuatro puntuaciones de cada corrida.
- [ ] Ejecutar Lighthouse en el backoffice, al menos la página principal y la vista compleja de mayor interés. Registrar las cuatro puntuaciones y métricas relevantes.
- [ ] Guardar las capturas originales en `audit/before/` y confirmar que abren y son legibles antes de cualquier cambio de código.

### 2. Analizar causas y refactorizaciones

- [ ] Revisar ambos frontends completos y conectar cada oportunidad a evidencia Lighthouse/experiencia real; no convertir todas las oportunidades automáticas en cambios.
- [ ] Documentar los problemas concretos, su ubicación, causa raíz, impacto probable y método de confirmación en `AUDIT.md`.
- [ ] Identificar **al menos dos** componentes o bloques de lógica duplicados y candidatos válidos a extracción. Registrar archivos/ubicaciones, duplicación observada, abstracción compartida propuesta y riesgos en `AUDIT.md`.
- [ ] Evitar duplicar una refactorización ya resuelta (por ejemplo, header/footer del website ya encapsulados como custom elements). Si el código ya está compartido, describirlo como estado existente, no como nuevo entregable.
- [ ] Revisar por separado rendimiento, accesibilidad, buenas prácticas y SEO. No reducir accesibilidad ni indexabilidad de páginas públicas para elevar Performance.

### 3. Aplicar correcciones dirigidas

- [ ] Priorizar TTFB, LCP, CLS, INP y score Performance con base en mediciones y usuarios afectados. El README ofrece como referencias de salud Performance ≥ 90, LCP < 2.5 s, CLS < 0.1 e INP < 200 ms; son objetivos orientativos, no permiso para manipular puntuaciones.
- [ ] Corregir causas confirmadas con el cambio mínimo: por ejemplo, optimización y entrega apropiada de imágenes; estabilidad de layout y dimensiones reservadas; fuentes/render-blocking; JavaScript/carga que afecte interacción; o problemas de hidratación solo si el stack realmente la usa (este checkout observado es estático y no usa Next.js).
- [ ] Hacer cambios incrementales, idealmente un problema por commit, y re-ejecutar Lighthouse en la misma URL y condiciones después de cada cambio relevante.
- [ ] Refactorizar e integrar al menos un componente reutilizable o Custom Hook durante el trabajo, conforme al README oficial. En un proyecto vanilla estático, una abstracción reutilizable equivalente (módulo/helper/componente compartido) solo es aceptable si queda explícitamente razonada y cumple la intención; no introducir React/Next o un framework solo para encajar el nombre “hook”.
- [ ] Conservar rutas, interacciones, accesibilidad, SEO, formularios, navegación y funciones del dashboard. Revisar errores de consola/red y realizar pruebas funcionales pertinentes.
- [ ] No reestructurar ni reescribir ninguno de los frontends. Si una recomendación requiere migración de stack, descartarla o pedir aprobación por separado.

### 4. Medir después y documentar

- [ ] Ejecutar Lighthouse de nuevo en ambos frontends y las mismas páginas/viewports con servidores/builds de producción y configuración comparable.
- [ ] Capturar informes finales en `audit/after/` con nombres equivalentes a los de `before/`.
- [ ] Crear `AUDIT.md` con puntuaciones iniciales, condiciones/URLs, problemas identificados y causa raíz, más el análisis de al menos dos candidatos de refactorización.
- [ ] Crear `REPORT.md` con cada corrección aplicada, evidencia/commit asociado, comparativa antes/después por score y métrica principal, impacto medido y evaluación de cuál cambio produjo el mayor efecto. Informar también de resultados neutros/negativos.
- [ ] Versionar `AUDIT.md`, `REPORT.md` y todas las capturas Lighthouse antes/después. No versionar secretos, perfiles del navegador, datos internos ni archivos temporales innecesarios.
- [ ] Ejecutar verificaciones funcionales/técnicas de los cambios y registrar los comandos/resultados relevantes en el reporte o PR.

## Qué vamos a evaluar

Usar esta matriz como criterio de aceptación; marcar como cumplido solo cuando exista evidencia:

- [ ] Lighthouse se ejecutó antes y después en **ambos** frontends usando producción, no modo dev, y existen capturas con commit en el repositorio.
- [ ] Las corridas cubren sitio corporativo en escritorio y móvil, además de las páginas/rutas complejas elegidas y el backoffice exigido; `AUDIT.md` registra ruta, viewport y las cuatro puntuaciones.
- [ ] `AUDIT.md` analiza problemas concretos con razonamiento de causa raíz; no es solo una lista copiada de Lighthouse.
- [ ] `AUDIT.md` identifica al menos dos casos reales de duplicación, sus ubicaciones y cómo se podrían refactorizar.
- [ ] Se extrajo e integró al menos un componente reutilizable o Custom Hook, sin romper funcionalidades ni degradar calidad de código.
- [ ] `REPORT.md` describe las correcciones y enseña la comparación medida antes/después; se demuestra una mejora en al menos una puntuación Lighthouse **por frontend**.
- [ ] Si se instalaron skills, hay evidencia de su uso en el proceso y del tratamiento de sus recomendaciones.
- [ ] Las correcciones abordan causas reales (por ejemplo, imágenes, layout shift o recursos de bloqueo) y no alteran métricas superficialmente.
- [ ] No hay regresiones funcionales, cambios fuera de alcance ni reestructuración de arquitectura.
- [ ] Hay evidencia verificable y comparable. No se exige una puntuación perfecta de 100; sí una mejora medida y un análisis profesional.

## Entrega

- [ ] Subir al monorepo de empresa `AUDIT.md`, `REPORT.md` y `audit/before/`, `audit/after/` con todas las capturas pertinentes.
- [ ] Crear commits descriptivos que permitan seguir cada corrección; incluir referencias a las mediciones.
- [ ] Publicar la rama/PR según el flujo de trabajo del repo y compartir el enlace de entrega con 4Geeks según las instrucciones del instructor.

## Registro de condiciones y resultados

Completar con evidencia real antes de finalizar:

- Fecha de medición inicial: _pendiente_
- URL(s) website / viewport(s): _pendiente_
- URL(s) backoffice / viewport(s): _pendiente_
- Comando/build/servidor de producción utilizado: _pendiente_
- Navegador y versión/perfil de Lighthouse: _pendiente_
- Ubicación de capturas antes/después: `audit/before/`, `audit/after/`
- Fecha de medición final: _pendiente_
