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
