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

### 4. Supplier directory (`/api/suppliers`)

- `POST /api/suppliers`: create a supplier; returns `201` with the TinyDB ID and
	server-generated `updated_at`.
- `GET /api/suppliers`: list suppliers; optional `country` and `category` filters
	can be combined and are applied together (AND).
- `GET /api/suppliers/{id}`: retrieve a supplier; returns `404` when it does not
	exist.
- `PATCH /api/suppliers/{id}/rate`: update a positive `monthly_rate` and refresh
	`updated_at`; returns `404` for an unknown ID.
- `PATCH /api/suppliers/{id}/status`: set `active` or `suspended`; returns `404`
	for an unknown ID.
- `DELETE /api/suppliers/{id}`: remove a supplier; returns `200`, or `404` if it
	does not exist.

Pydantic rejects invalid payloads and filter values with `422`. The client cannot
set the TinyDB ID or `updated_at`; changing status does not change the rate
timestamp.

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
