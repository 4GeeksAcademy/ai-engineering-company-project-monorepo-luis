# Evidencia de despliegue en el VPS

> **Estado: OPCIONAL** — El profesor confirmó que el despliegue al VPS no es obligatorio para esta entrega. Este archivo queda como referencia si se decide completar en el futuro.

> **Instrucciones**: Si decides completar el despliegue, ejecuta los siguientes comandos en el VPS y copia/pega la salida en los bloques de código correspondientes.

## Estado de los contenedores
```
# Ejecuta en el VPS
docker compose ps
```

## Logs recientes de los contenedores
```
# Ejecuta en el VPS
docker compose logs --tail=100
```

## Health‑check del backend
```
# Ejecuta en el VPS (cambia <IP> por la IP pública del VPS)
curl --fail http://<IP>:8000/health
```

## Acceso a las UI
- Website: `http://<IP>:3000`
- Backoffice: `http://<IP>:3001`

**Nota**: elimina cualquier credencial o dato sensible antes de commitear.

