# Nexova Backoffice

Panel interno de referencia para el contexto de negocio y las etapas del proceso de talento. Se mantiene separado del sitio público y del tracker de candidatos.

## Alcance de datos

- Las cifras aproximadas de plantilla y facturación y las líneas de negocio se transcriben de `CONTEXT.md`.
- Los nombres de las etapas se toman de `SPEC.md`.
- No consulta la API del tracker, no muestra recuentos operativos y no contiene datos personales de candidatos.
- El aviso visible en el panel indica que es contexto del proyecto, no una vista en tiempo real.

## Ejecutar localmente

Desde la raíz del monorepo:

```bash
npx --yes serve uis/backoffice -l 5502
```

Abrir http://localhost:5502. No usar el modo SPA; la app estática debe servir `index.html` en `/`.

## Validación

- Abrir `/` y comprobar la carga del panel.
- Revisar navegación interna, enlace al sitio público y enlace al tracker.
- Comprobar el layout en viewport amplio y móvil, foco visible y contenido con zoom.
- Confirmar que el panel no renderiza nombres, correos, teléfonos ni otros datos personales.

No hay scripts propios de test, lint, typecheck o build porque esta app es estática y no añade un toolchain independiente.
