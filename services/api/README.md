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

## AUTH-01 stage 2: internal users and profiles

Stage 2 implements the internal TinyDB service only. Login, JWT, HTTP user/profile
routes, admin provisioning and authorization are still pending. Nothing in
`main.py` or the existing routers changed; the backoffice is unaffected so far.

### Modules and internal operations

- `auth_models.py`: `UserRole`, `UserCreate`, `UserUpdate`, `UserResponse`,
  `UserRecord`, `ProfileUpdate` and `ProfileResponse`. Server-managed fields are
  forbidden on input; credential updates reject explicit nulls. Contact fields
  belong only to the profile, and contact updates can clear fields with null.
- `passwords.py`: `hash_password` and `verify_password`, using libpass bcrypt.
  New passwords require at least 8 characters and at most 72 UTF-8 bytes, without
  null bytes. Overlong inputs are rejected, never silently truncated.
- `auth_storage.py`: `get_auth_database_path` and `open_auth_database`, using
  `NEXOVA_AUTH_DB_PATH` or the ignored local `services/api/data/auth.json`.
- `user_service.py`: `create_user`, `get_user_by_id`, `get_user_by_email`,
  `list_users`, `update_user`, `delete_user`, `get_profile_by_user_id` and
  `update_profile`. Registration creates a `user` account and exactly one profile,
  including when contact fields are absent. Deletion removes both together.

Emails are validated, trimmed and lowercased consistently before registration,
lookup and update. Role validation accepts only `admin`, `manager` and `user`;
the registration service separately rejects the two privileged roles. UTC
timestamps and the active state are generated by the service, not registration.

Password inputs and stored hashes use `SecretStr`, are hidden from representations
and excluded from model serialization. A `UserRecord` exposes its hash only through
the internal attribute needed for password verification; response data and the
serialization schema omit it. The persisted users table contains only email,
hash, active state, role and timestamp; TinyDB's document key is the user ID.

Domain exceptions are `DuplicateEmailError`, `UserNotFoundError`,
`ProfileNotFoundError` and `RegistrationRoleError`. Missing email lookup returns
`None`. They do not contain passwords/hashes or implement HTTP responses yet.
HTTP mapping and owner/admin checks will be added in later stages. In particular,
`update_user` is an internal privileged operation: callers must enforce permission
checks before exposing role or active-state changes over HTTP.

### Coordinated storage and limitations

Every operation loads the TinyDB snapshot into `MemoryStorage` under a shared
in-process lock. Changes are committed only after the whole operation succeeds,
through a flushed temporary file and `os.replace` in the same directory. Exceptions
before replacement leave the persisted snapshot unchanged; temporary files are
removed on ordinary failure. Reads and empty updates do not rewrite existing data.
Successful commits use a temporary file with owner-only permissions.

This coordinates user/profile creation, deletion, duplicate checks and IDs within
one process. `auth_metadata` is a third TinyDB table containing only persistent ID
high-water counters; it prevents ID reuse after deletion and reopening the database.
It contains no extra user/contact data and does not move identity to another store.

This is not a multi-process transaction system: use one API worker, and do not
mutate the same database concurrently through an external admin/seed process.
File replacement does not guarantee recovery from all operating-system failures
or power loss; a killed process may leave an unused temporary file. Restoring or
resetting the database can invalidate the ID history and must be accompanied by
invalidating old signing keys/tokens once JWT is introduced. Production deployment
and cross-process locking remain outside this local/demo milestone.

### Stage 2 verification

Run from the monorepo root:

```bash
uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_auth_models.py -v
uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_user_service.py -v
uv run --locked --project services/api python -m unittest discover -s services/api/tests -v
```

On 2026-10-13, all 10 model/password tests, 17 service/storage tests and 51 total
backend tests passed. Coverage includes role/default validation, forbidden fields,
UTF-8 password limits, hidden hashes, profile linkage, normalized duplicate emails,
credential updates, cascade deletion, non-reused IDs, concurrent duplicate creation,
missing records and injected profile/file-commit failures. All credential data is
synthetic and databases are temporary; no real auth database or `.env` was used.

Next: stage 3 introduces environment-based JWT configuration, login in both formats,
`get_current_user`, `/auth/me` and the safe local admin command.

## AUTH-01 stage 3: JWT, login and offline admin provisioning

### Current behavior

- `POST /auth/login` verifies credentials and returns `access_token` and
  `token_type=bearer`. It accepts JSON `email`/`password` or
  `application/x-www-form-urlencoded` with `username=email` and `password`.
  The optional OAuth2 `grant_type`, if supplied, must be `password`.
- `GET /auth/me` requires a valid Bearer token and returns the current user's
  email, role and linked profile. It never returns a password or hash.
- `get_current_user` is reusable by the next stages. It validates HS256 signature,
  required expiration and a positive integer TinyDB `id`; an optional `sub` must
  match that ID. It then reads the existing active user and current role from
  TinyDB. Roles/passwords/contact data are not copied into issued tokens.
- Invalid/missing credentials, token failures and deleted/inactive accounts return
  generic `401` errors with `WWW-Authenticate: Bearer`. Invalid login payloads
  return a generic `422` without echoing input; unsupported content types return
  `415`. Unknown-user login still performs a dummy bcrypt verification.
- OAuth2 password flow and both request formats are documented in OpenAPI;
  Swagger `Authorize` uses the same `/auth/login` endpoint, with email as username.

The routes for registration, user CRUD and `/profiles/me` are **not implemented
yet**. Stage 3 tests create synthetic accounts through the internal service.
Do not mistake login alone for complete API protection: suppliers and incidents
remain public until stage 5. Their existing behavior and the frontend are unchanged,
provided the backend is started with its new required configuration.

### Required runtime configuration

The FastAPI lifespan validates configuration before startup succeeds:

| Variable | Stage 3 validation |
| --- | --- |
| `JWT_SECRET_KEY` | Required, nonblank, at least 32 UTF-8 bytes. Supply a high-entropy signing key, not a memorable password. No secret default. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Required positive integer; must yield a representable finite expiration. |
| `NEXOVA_AUTH_DB_PATH` | Optional; same separate TinyDB path introduced in stage 2. |

HS256 is fixed in code; a token header cannot choose the verification algorithm.
Settings are loaded once at startup and changes require restarting the API. Startup
errors name the invalid variable without printing its value. Tests calling auth
must run `TestClient` as a context manager so the lifespan initializes settings.

For a disposable local/demo session, from the repository root and with shell
tracing disabled, generate the key into the environment without displaying it:

```bash
export JWT_SECRET_KEY="$(uv run --locked --project services/api python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export ACCESS_TOKEN_EXPIRE_MINUTES=15
uv run --locked --project services/api uvicorn services.api.main:app --reload --port 8000
```

These commands do not write a `.env` file or version a secret. Regenerating the key
invalidates previously signed tokens. Keep the same environment when restarting if
tokens must remain valid until expiration. No real secret/configuration file was
read, created or modified during this stage; all verification used temporary values.

This is JWT stateless authentication, without cookies, sessions or refresh tokens.
Password changes alone do not revoke previously issued tokens immediately; account
deactivation/deletion is checked on each request and expiration remains mandatory.

### First admin: explicit offline promotion

The installed `promote-admin` command promotes an **existing active user** to
admin. It never registers a user, accepts a password, seeds privileged credentials
or exposes an HTTP bootstrap endpoint. Stop the API before running it: TinyDB's
in-process lock cannot coordinate simultaneous writes by this separate process.

From the repository root, use an existing authorized database and replace the
example ID with the actual TinyDB ID of the intended user:

```bash
uv run --locked --project services/api promote-admin --database services/api/data/auth.json --user-id 1 --confirm
```

Both database path and positive user ID are mandatory; `--confirm` is required.
The explicit path overrides `NEXOVA_AUTH_DB_PATH` only for the command and then
restores it. Missing databases/users, inactive users and I/O failures exit nonzero;
missing arguments exit with usage code 2. Promotion is idempotent and preserves
the password hash and linked profile. Output contains no email, password or hash.
Permission to execute this command comes from authorized local filesystem access,
not from an unauthenticated API request. Real-data mutations require separate
authorization under the repository rules; stage 3 ran it only against test data.

`pyproject.toml` registers `promote-admin = "bootstrap_admin:main"` and packages
the local command module alongside `seed`. Tests verify that the installed command
also runs outside the repository working directory in this editable monorepo setup.
This does not package the entire monorepo as a standalone production distribution.

### Stage 3 verification and next step

Run from the repository root:

```bash
uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_security.py
uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_auth_api.py
uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_bootstrap_admin.py
uv run --locked --project services/api python -m unittest discover -s services/api/tests
uv lock --check --project services/api
```

On 2026-10-13: 9 security tests, 13 HTTP/startup tests, 7 admin-command tests and
all 80 backend tests passed. The 51 previous tests remain green. Checks cover
missing/invalid configuration, expiration, wrong signature/algorithm, malformed
claims, active/deleted users, current role changes, both login formats, generic
errors, safe response/OpenAPI schemas, installed CLI and idempotent promotion.
Password verification also safely rejects unencodable Unicode input.

One HTTP test starts a real Uvicorn subprocess on an ephemeral local port, checks
`/health`, `/docs`, unauthenticated `/auth/me`, JSON login and authenticated
`/auth/me`, then stops the process. All databases/keys/accounts are temporary and
synthetic; neither credentials nor tokens are printed. Manual browser verification
of the complete registration/Swagger flow was scheduled for stage 6 after the
registration endpoints existed; that acceptance is recorded below. No persistent
development server was left running.

Lockfile verification and diagnostics passed; there are no new dependencies or
changes to `uv.lock`. The existing Starlette/httpx warning and uv hardlink fallback
remain nonblocking. Pre-existing README formatting edits stay outside this commit.

Stage 4 subsequently published `/users` and `/profiles/me` with owner/admin
authorization and privilege checks before invoking the internal services.

## AUTH-01 stage 4: protected user and profile endpoints

### Endpoint behavior

- `POST /users` is public and creates a default `user` plus its linked profile.
  Optional `name`, `phone` and `address` initialize `Profile`. The public
  registration schema does not accept `role`, `id`, `is_active`,
  `hashed_password`, `created_at` or `user_id`; invalid/extra fields return a
  generic `422` without echoing credentials. Duplicate normalized emails return
  `409`.
- `GET /users` requires an active admin. It returns credential-safe user
  responses and never includes hashes.
- `GET /users/{user_id}`, `PUT /users/{user_id}` and
  `DELETE /users/{user_id}` require an active owner or admin. A non-admin
  accessing another ID gets `403` before existence is checked, preventing ID
  enumeration; an authorized missing target gets `404`.
- Owners can update their own email/password. Only admins can include `role` or
  `is_active` in `PUT`, including setting the same value. The `manager` role
  receives no admin privileges. Duplicate email updates return `409`; missing
  authorized users return `404`. Passwords are re-hashed by the internal service.
- `GET /profiles/me` and `PUT /profiles/me` require authentication and always use
  the current token's user ID. There is no profile-by-ID route, even for admins.
  The request accepts only `name`, `phone` and `address`; explicit null clears a
  field, omitted fields remain unchanged, and contact details never enter `User`.
- User deletion removes the linked profile. `/auth/me` continues to include that
  user's linked profile. All user/profile routes return `401` with a Bearer
  challenge for absent or invalid tokens; valid authentication without permission
  returns `403`.

All reads of users/profiles use `UserResponse`/`ProfileResponse`; the internal
`UserRecord` hash is excluded by the response schemas. The app sanitizes request
validation responses on `/users` so Pydantic errors cannot echo submitted
passwords. Other existing API validation behavior is unchanged.

### OpenAPI and local verification

`/docs` exposes public registration and login separately from Bearer-protected
user/profile operations. A disposable local API requires the stage 3 environment
variables and can be run from the repository root as follows:

```bash
uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_users_api.py -v
uv run --locked --project services/api python -m unittest discover -s services/api/tests
```

The test fixture registers synthetic accounts through the real HTTP endpoint,
obtains tokens through the real JSON login, and promotes synthetic manager/admin
accounts only through the internal service. It covers missing-token `401`, owner
and manager `403`, authorized admin behavior, `404`/`409`/sanitized `422`, public
role-escalation rejection, owner email/password changes, admin-only activation and
role changes, self-profile isolation, cascade deletion, OpenAPI and absence of
hashes/passwords in responses. No real credentials, personal data or auth database
were used.

On 2026-10-14, all 16 focused user/profile HTTP tests and all 96 backend tests
passed, including the 80 tests from stages 1–3 and the unchanged incident/supplier
regression tests. The existing Starlette `httpx` deprecation warning remains
non-blocking. Changes to README formatting that predated this stage were preserved
outside the commit.

### Current boundary and next stage

Stages 1–5 implement authentication for `/users`, `/auth`, `/profiles` and the
eight pre-existing operational routes. Frontend token integration and the manual
end-to-end Swagger acceptance flow remain for stage 6.

## AUTH-01 stage 5: protect operational endpoints

All six supplier operations and both incident operations require a valid Bearer
token through router-level `get_current_user` dependencies:

| Method | Route | Access |
| --- | --- | --- |
| POST | `/api/suppliers` | Active authenticated user. |
| GET | `/api/suppliers` | Active authenticated user. |
| GET | `/api/suppliers/{supplier_id}` | Active authenticated user. |
| PATCH | `/api/suppliers/{supplier_id}/rate` | Active authenticated user. |
| PATCH | `/api/suppliers/{supplier_id}/status` | Active authenticated user. |
| DELETE | `/api/suppliers/{supplier_id}` | Active authenticated user. |
| POST | `/api/incidents/analyze` | Active authenticated user. |
| GET | `/api/incidents/results/export` | Active authenticated user. |

The dependency runs before the existing operation. Missing, malformed, expired,
invalidly signed, deleted-user or inactive-user credentials return `401` with a
`WWW-Authenticate: Bearer` challenge. No new owner or role matrix is applied:
the supplier directory and the latest incident analysis remain shared among
authenticated users. The analysis result is still global and in memory. `/health`,
`/docs` and `/openapi.json` remain public.

Valid-token requests retain the existing contracts: supplier create remains `201`,
filters still combine with AND, missing suppliers still return `404`, updates retain
their timestamp behavior, and incident CSV validation, aggregation and export are
unchanged. No response, storage schema, or frontend behavior changed beyond the
required authentication header.

### Stage 5 regression checks

Run from the repository root:

```bash
uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_suppliers_api.py
uv run --locked --project services/api python -m unittest discover -s services/api/tests -p test_api.py
uv run --locked --project services/api python -m unittest discover -s services/api/tests
```

The existing supplier and incident HTTP tests now register synthetic users and
obtain tokens through `/auth/login` before exercising each original behavior. Added
route matrices check that all six supplier operations and both incident operations
reject absent and malformed tokens with `401`; OpenAPI also marks each operation as
Bearer-protected. Public health behavior is asserted unchanged. Tests use temporary
TinyDB files and disposable environment keys; no real credentials or candidate data
were introduced.

On 2026-10-14, the supplier slice passed 11 tests, the incident slice passed 8
tests, and the full backend suite passed 100 tests. A nested `TestClient` test setup
initially exposed that the app lifespan deleted shared `jwt_settings` twice; the
lifespan now restores the prior app state on exit. The focused suites pass after
that correction. Existing supplier response/filter/timestamp behavior and incident
CSV behavior remain covered by valid-token requests.

The test editor may report unresolved FastAPI imports if it selects the global
Python interpreter. The service dependencies are installed in `services/api/.venv`;
run the documented `uv` commands or select that interpreter for editor diagnostics.

Stage 6 completed the final `/docs` acceptance flow, requirement matrix and PR
description. Frontend token integration remains a separate follow-up.

## AUTH-01 stage 6: acceptance and delivery

### Final acceptance

The final live HTTP flow was exercised against a real Uvicorn subprocess on an
ephemeral local port. The signing key, access-token lifetime, auth/supplier TinyDB
paths, account and request data were generated for this run only and removed when
the process exited. No `.env` file, production service or real candidate data was
used.

The flow verified:

- `/docs`, `/openapi.json` and `/health` respond; OpenAPI marks all six supplier
  and both incident operations as Bearer-protected.
- Public `POST /users` creates the default `user` and linked profile without
  returning a hash/password; attempting public `role=admin` returns sanitized
  `422`.
- JSON login and OAuth2 form login work. `/auth/me` and `/profiles/me` return the
  authenticated user's account/profile; invalid or expired token returns `401`,
  and a non-admin cannot list users (`403`).
- Missing-token calls to protected supplier create/list and incident analysis/export
  return `401`. With a valid Bearer token, supplier create/list/read/rate/status/
  delete preserve their existing HTTP contracts and incident analysis/export
  succeed on one fully synthetic CSV row.
- The exported analysis contains no synthetic email. The auth database contains a
  bcrypt hash and not the submitted password; API responses contain neither hash
  nor password.

The complete automated acceptance/regression suite remains:

```bash
uv run --locked --project services/api python -m unittest discover -s services/api/tests
uv lock --check --project services/api
git diff --check
```

On 2026-10-14, all 100 backend tests passed, including the six supplier operations,
two incident operations, ownership/role checks, JWT failure cases, and existing
functional regressions. The live Uvicorn flow above also passed. `uv lock --check`
and `git diff --check` passed. Pylance diagnostics may still show unresolved FastAPI
imports because the editor's selected global interpreter is `/usr/local/python/3.12.1`;
the service `.venv` has FastAPI/Uvicorn and all `uv run` checks pass. No global editor
setting was changed. The existing Starlette/httpx deprecation warning is non-blocking.

### Protected-route matrix

| Area           | Public                               | Protected                                                                                          |
| -------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Users          | `POST /users` registration only.     | `GET /users` admin; `GET/PUT/DELETE /users/{user_id}` owner/admin; role/status changes admin only. |
| Authentication | `POST /auth/login`.                  | `GET /auth/me`.                                                                                    |
| Profiles       | None.                                | `GET/PUT /profiles/me`, current owner only.                                                        |
| Suppliers      | None.                                | All six operations under `/api/suppliers`.                                                         |
| Incidents      | None.                                | `POST /api/incidents/analyze` and `GET /api/incidents/results/export`.                             |
| Health/docs    | `/health`, `/docs`, `/openapi.json`. | None.                                                                                              |

### Pull request

The feature is delivered from `feature/auth-api` to `main`. The PR description
summarizes the protected routes, user/profile ownership rules, TinyDB-only identity
storage, environment-based JWT configuration, and the automated/live verification
above. The backoffice has not been updated to send Bearer tokens; that frontend
integration remains a separate follow-up. Its requests to the now-protected
operational routes will receive `401` until integrated.

## AUTH-03: password recovery plan

Stage 1, 2026-10-18, documents the contract only. Password recovery endpoints,
reset tokens and email delivery are **not implemented or configured yet**.
The [requirements and seven-stage board](../../restablecimiento-contrasena.md#plan-de-trabajo-por-etapas)
track evidence, review, commit and push separately. Work continues on the existing
`feature/password-reset`; every commit and push requires the user's approval.

### Integration and planned endpoints

AUTH-02 already integrates Nexova login, registration and profiles in
`uis/talent-pipeline-tracker`. Extend its `lib/nexova-api.ts` client and
`NEXT_PUBLIC_NEXOVA_API_URL`; do not send authentication requests to the external
candidate API configured by `NEXT_PUBLIC_API_URL`. The public website and the
static backoffice are outside this milestone.

| Method | Route | Planned access and behavior |
| --- | --- | --- |
| POST | `/auth/forgot-password` | Public; `{ email }`; identical `200` body for valid existing/unknown emails when accepted. No account-existence disclosure. |
| POST | `/auth/reset-password` | Public; `{ token, new_password }`; invalid, missing, expired or consumed token returns generic `400`. |
| POST | `/auth/change-password` | Bearer required; `{ current_password, new_password }`; wrong current password returns `400`, missing/invalid session `401`. No caller-supplied user ID. |

Malformed email or password-policy failures use sanitized validation errors,
without echoing input. Preserve bcrypt's minimum 8 characters, maximum 72 UTF-8
bytes, and rejection of null bytes. New auth payloads must not leak credentials
through FastAPI/Pydantic validation responses, logs or exception details.

### Planned reset-token storage

Use an opaque token generated with `secrets.token_urlsafe(32)` and persist only
its SHA-256 digest, user association and minimal expiration/consumption state.
Use secure comparison and a 30-minute default lifetime, bounded to 15-60 minutes.
Reset tokens cannot authorize protected routes; access JWTs cannot reset passwords.

Issuing another token invalidates previous links for that user. Validate and
consume the token, update the password hash and invalidate pending resets within
one `open_auth_database` snapshot, not separate service commits. Concurrent use
must yield exactly one success; persistence failure must leave the password and
token unchanged. Invalidate outstanding resets on existing password/email changes,
deactivation and deletion too. Clean up expired records without unbounded growth.
Reuse the existing single-process lock; multi-worker guarantees remain out of scope.
Previously issued access JWTs retain their existing expiration behavior: this work
does not introduce server-side session revocation or refresh tokens.

### Planned Resend configuration

These names are the implementation contract, **not settings currently read by the
application**. No credential or `.env` file is needed for stage 1. Existing required
`JWT_SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_MINUTES` remain unchanged.

| Variable | Planned purpose |
| --- | --- |
| `RESEND_API_KEY` | Backend-only secret API key. Never expose through `NEXT_PUBLIC_*`, responses, logs or committed files. |
| `RESEND_FROM_EMAIL` | Sender authorized by Resend. Verify the account's current onboarding/domain and recipient restrictions before a real test. |
| `NEXOVA_FRONTEND_URL` | Trusted frontend origin used to construct `/reset-password?token=...`; never derive it from a caller-controlled Host header. Local HTTP is for development only. |
| `PASSWORD_RESET_EXPIRE_MINUTES` | Optional integer, default `30`, constrained to `15` through `60`. |

Use runtime environment variables. Reading or modifying `.env*`, configuring real
credentials and connecting Resend require separate authorization. Check Git ignore
coverage before any approved file-based setup. Stage 1 neither creates nor reads an
environment file. Real email acceptance requires an authorized sender and test
inbox; no real candidate data may be used.

Stage 1 added root Git ignore rules for `.env` and `.env.*`, allowing
`.env.example` templates. `git check-ignore --no-index --verbose` verified the
API environment paths and its template exception without opening or creating them.
Nested application rules can be stricter; verify the exact path before any approved
template or credential setup.

### Accepted local/demo delivery policy

Perform account lookup, token issuance and Resend delivery in a background task,
outside the public response path. An identical `200` means the request was accepted,
not that email delivery succeeded. Do not hold the TinyDB lock across a network call.
Use bounded provider timeouts and sanitized operational failures; never log a reset
URL, token, API key, password, provider payload or recipient address.

Check local configuration and task acceptance consistently regardless of the email.
A failure before acceptance is a generic operational error, not a false success;
malformed email remains a generic validation error. A later provider failure must
not become an account-existence signal. The UI must distinguish a network or
acceptance error from a successfully accepted request without claiming delivery.
This agreed scope has no durable queue or guaranteed retries: a restart can lose
pending work and require another request. Real email receipt remains mandatory for
final acceptance; mocked delivery cannot satisfy it.

### Stage checks

From the monorepo root, establish the backend baseline:

```bash
uv run --locked --project services/api python -m unittest discover -s services/api/tests
git diff --check
```

From `uis/talent-pipeline-tracker`, establish the frontend baseline:

```bash
npm run lint
npm run build
```

Future backend tests use temporary databases, synthetic users, controlled clocks
and injected email transports. Cover expiration, one-time/concurrent consumption,
persistence failures, indistinguishable public responses, provider failures,
cross-use of JWT/reset tokens, validation secrecy and existing endpoint regressions.
Run focused tests before the full suite; check the uv lockfile if dependencies change.
No Python lint/typecheck/build or frontend test script is currently declared.
Final acceptance additionally requires a browser flow and real Resend receipt,
with sanitized evidence and no tokens in URLs captured by logs, screenshots or traces.

Stage 1 baseline on 2026-10-18: all **100 backend tests**, tracker lint and
production build passed. The existing Starlette/httpx deprecation and Next.js
multiple-lockfile/root-inference warnings remain nonblocking. The build loaded its
existing local environment automatically; no environment file content was inspected,
changed or printed. Document diff formatting passed; new local link destinations
exist. An older AUTH-01 link to the deleted `autenticacion.md` remains historical
and outside this change. These checks establish the starting point, not AUTH-03
acceptance. Stage 1 is ready for review; no commit or push has been made.
