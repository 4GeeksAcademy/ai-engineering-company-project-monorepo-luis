# Nexova Operations API

Centralized FastAPI backend service for Nexova operations and incident analysis.

## Endpoints

### 1. `POST /api/incidents/analyze`

- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body**: File field `file` containing an incidents `.csv` file.
- **Response**: JSON summary with total, valid, invalid records, categories breakdown, status breakdown, and satisfaction score statistics without any customer PII.

### 2. `GET /api/incidents/results/export`

- **Method**: `GET`
- **Response**: `text/csv` attachment `results.csv` containing aggregated metrics for the latest completed analysis (one metric per row). Returns `404` if no analysis has been run yet.

### 3. `GET /health`

- **Method**: `GET`
- **Response**: `{"status": "ok", "service": "nexova-api"}`

## Running the API locally

```bash
uvicorn services.api.main:app --reload --port 8000
```

Interactive Swagger API documentation is available at `http://127.0.0.1:8000/docs`.

## Supplier storage and seed

The supplier directory uses TinyDB. Its default JSON database is created at
`services/api/data/suppliers.json`, which is local runtime data and is ignored by Git.
Set `NEXOVA_SUPPLIERS_DB_PATH` to use another database file, for example a temporary
path in tests. Keep this API and its commercial supplier data on the local/demo
environment; the current CORS configuration is not authentication.

Install and run the idempotent seed from this directory:

```bash
cd services/api
uv run seed
```

The command reports inserted and already-existing suppliers. It does not replace
records that match by supplier name and country.
