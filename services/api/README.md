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

## AUTH-01: authentication delivery plan

### Stage 1 status and sources

Stage 1 prepares dependencies and documents the implementation contract. **No
authentication endpoints or route restrictions are implemented yet.** The existing
API and backoffice continue to behave as before this stage.

The local requirements are in [autenticacion.md](../../autenticacion.md). On
2026-10-13, they were checked against the complete
[official Spanish assignment](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-user-authentication-api/README.es.md):
no substantive requirement discrepancies were found. The official assignment takes
precedence if it changes or a discrepancy appears. `ingenieria-ia.md` was retired
intentionally, as recorded in the memory bank; do not recreate it for this milestone.

All work extends this service on `feature/auth-api`, based on `main` at `12ef190`.
Each stage includes tests, documentation, one commit and a push; the final delivery
is a pull request to `main`. Pre-existing README formatting changes are not part of
the stage 1 commit.

### Dependencies and reproducible checks

The required packages were added with `uv`, not `pip` or `pipenv`:

```bash
# From the monorepo root; equivalent to uv add from services/api.
uv add --project services/api "python-jose[cryptography]" "libpass[bcrypt]"

# Existing backend suite, using the committed lockfile.
uv run --locked --project services/api python -m unittest discover -s services/api/tests -v

# Local API, from the monorepo root.
uv run --locked --project services/api uvicorn services.api.main:app --reload --port 8000
```

`pyproject.toml` defines dependencies; `uv.lock` fixes their resolved versions.
Keep the compatibility manifest `requirements.txt` consistent with the project
dependencies. `libpass` provides the Python import `from passlib.hash import bcrypt`.
Stage 1 resolved `libpass==1.9.3`, `bcrypt==5.0.0` and `python-jose==3.5.0`.

Stage 1 checks on 2026-10-13: all 24 existing tests passed before and after the
dependency change. A runtime smoke check passed bcrypt hashing, verification of
correct/incorrect passwords and HS256 JWT encode/decode with an expiration claim.
It used disposable in-memory values and printed no passwords, hashes, keys or tokens.
This validates the packages, not a completed authentication implementation.

The suite emits an existing Starlette warning about `httpx` test-client support;
tests still pass. `uv` also reported a cross-filesystem hardlink fallback to copying,
which did not prevent installation. Neither warning is an authentication change.
No Python lint/typecheck/build commands are currently declared for this service.

### Agreed security contract (not yet implemented)

- Public registration always creates `role=user`. Allowed roles are `admin`,
  `manager`, `user`; invalid roles are rejected and registration cannot elevate
  privileges. Only an admin can change roles or account activation state.
- The first admin is provisioned by a safe, explicit, idempotent local command,
  not by a public privileged endpoint or a seeded password. Its packaging must be
  added alongside the existing `seed` entry point when implemented.
- User credentials and profiles remain exclusively in TinyDB, including after
  any future Supabase integration. Contact data belongs only in `Profile`.
- Registration creates the linked profile even when its optional fields are
  absent; deleting a user also deletes its profile. Coordinate failures and test
  compensation, without claiming that TinyDB offers database transactions.
- The TinyDB user `doc_id` is an integer, exposed as `id`; `Profile.user_id` and
  the JWT `id` claim use that same identity. Any future `user_uuid` reference uses
  its decimal string representation, not a new UUID. Prevent ID reuse from
  granting an old token access to a newly created account.
- Separate input/output schemas; reject client-managed fields and never expose
  password hashes. Normalize emails consistently and reject duplicates. Hash
  passwords on creation and update; do not silently truncate bcrypt input.
- Login accepts JSON `email`/`password` and OAuth2 form data with `username=email`
  and `password`, using the same credential verification. Swagger `Authorize`
  must work with `OAuth2PasswordBearer` pointing to `/auth/login`.
- JWT authentication is stateless: no cookies, sessions or refresh-token workflow.
  Decode only the configured algorithm (HS256) and check expiration; retrieve the
  current user, active state and permissions from TinyDB on every protected request.
- Missing, malformed, expired or invalid credentials return `401` with a Bearer
  challenge; a valid user without authorization receives `403`. Invalid payloads
  return `422`, duplicate emails `409`, and authorized missing resources `404`.
- Suppliers and the latest incident result remain shared operational resources
  for authenticated users. The incident result is currently global and in memory;
  this milestone does not introduce per-user ownership or durable result storage.
- This remains a local/demo service. TinyDB concurrency/transaction limitations
  must be documented; multi-worker production deployment is outside this scope.

### Planned environment configuration

These names are reserved for stages 2 and 3; **stage 1 does not read them**.

| Variable | Planned purpose |
| --- | --- |
| `NEXOVA_AUTH_DB_PATH` | Optional separate TinyDB path; default `services/api/data/auth.json`. Tests use temporary databases. |
| `JWT_SECRET_KEY` | Required signing key from the runtime environment; no hardcoded or repository-stored default. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Required positive finite access-token lifetime from the runtime environment. |

The existing `.gitignore` excludes `/services/api/data/`, including the planned
authentication database. Any custom path must remain outside tracked source files.
Do not commit secrets, tokens, credential databases or real personal data. No
existing `.env` file was read or modified for this stage; file-based secret setup
requires explicit approval under the repository rules.

### Planned endpoint access matrix

The first nine operations below are new and will be implemented in stages 3 and 4.
The following eight already exist and remain unauthenticated until stage 5.

| Method | Route | Target access |
| --- | --- | --- |
| POST | `/users` | Public registration; role `user` only. |
| GET | `/users` | Admin only; never return hashes. |
| GET | `/users/{id}` | Owner or admin. |
| PUT | `/users/{id}` | Owner or admin; role/activation changes admin only. |
| DELETE | `/users/{id}` | Owner or admin; delete the linked profile. |
| POST | `/auth/login` | Public credential verification. |
| GET | `/auth/me` | Current authenticated user's email, role and profile. |
| GET | `/profiles/me` | Current authenticated user's profile. |
| PUT | `/profiles/me` | Current authenticated user's profile only. |
| POST | `/api/suppliers` | Authenticated user. |
| GET | `/api/suppliers` | Authenticated user. |
| GET | `/api/suppliers/{id}` | Authenticated user. |
| PATCH | `/api/suppliers/{id}/rate` | Authenticated user. |
| PATCH | `/api/suppliers/{id}/status` | Authenticated user. |
| DELETE | `/api/suppliers/{id}` | Authenticated user. |
| POST | `/api/incidents/analyze` | Authenticated user. |
| GET | `/api/incidents/results/export` | Authenticated user. |

`/health`, `/docs` and `/openapi.json` stay public for local verification. The
`manager` role does not inherit admin permissions. No additional operational
role matrix or private-resource model is introduced.

### Staged implementation and acceptance

| Stage | Deliverable | Acceptance before commit/push |
| --- | --- | --- |
| 1 | Audit, dependencies, access matrix and persistent plan. | Official requirements checked; package smoke check and existing backend suite pass. |
| 2 | TinyDB user/profile models and services, bcrypt, uniqueness and coordinated lifecycle. No new HTTP endpoints yet. | Isolated service/model tests: allowed/default roles, hashes, profile relation, duplicates, update/delete and failure compensation. |
| 3 | Environment configuration, JWT, `get_current_user`, `/auth/login`, `/auth/me` and local admin provisioning. | JSON/form login, valid/invalid/expired tokens, missing/invalid configuration, inactive/deleted users and safe admin provisioning tests. |
| 4 | `/users` CRUD and `/profiles/me`, protected as soon as registered. | Real-token HTTP tests for owner/admin/manager, `401` vs `403`, privilege escalation rejection, credential updates and profile cascade. |
| 5 | Protect the eight existing operational endpoints; adapt regression fixtures to real login/Bearer tokens. | Each operation rejects missing/invalid tokens and retains its original functional behavior with a valid token. |
| 6 | Full acceptance, manual Swagger flow, redacted evidence and PR to `main`. | Complete suite and requirement-to-test matrix; manual registration/login/Authorize/protected-route flow; secret/data review. |

Before every commit, run focused checks for the touched behavior and the complete
backend suite. Update this README and `memory-bank/progress.md`; update
`memory-bank/techContext.md` when configuration or architecture changes. Record
actual commands/results, limitations and the next stage, not presumed successes.
Review the diff and stage only authorized files/hunks; never include unrelated
work. Publish one descriptive commit per stage without force-pushing and report
its hash and validation results. Do not advance after a failed check or push.

Stage 5 will intentionally make current backoffice requests without a Bearer token
fail. Frontend authentication integration is a separate follow-up, as allowed by
the assignment. This milestone does not change the tracker, add Supabase, deploy
the service, use real candidate data or introduce MFA/password recovery.
