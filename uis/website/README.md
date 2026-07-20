# Website — Nexova

Landing page y formulario de aplicación del sitio público de Nexova.

## Compilar estilos Tailwind (build local)

Desde la raíz del repositorio ejecuta:

```bash
npx --yes tailwindcss@3.4.17 -c uis/website/tailwind.config.cjs -i uis/website/assets/css/input.css -o uis/website/assets/css/styles.css --minify
```

Esto genera el archivo estático:

- `uis/website/assets/css/styles.css`

## Ejecutar localmente en Codespaces

Desde la raíz del repositorio ejecuta:

```bash
npx --yes serve uis/website -l 5500 -s
```

Luego abre en el navegador:

- http://localhost:5500

Si el puerto 5500 está ocupado, usa otro puerto:

```bash
npx --yes serve uis/website -l 5501 -s
```

## Verificación rápida

- La landing carga en `/index.html`.
- El formulario carga en `/application.html`.
- El enlace de la landing hacia la aplicación funciona correctamente.
