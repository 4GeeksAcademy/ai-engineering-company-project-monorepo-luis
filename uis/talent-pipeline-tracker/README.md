This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Nexova Authentication

The tracker and Nexova authentication use separate API origins:

| Variable | Purpose | Typical local value |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Candidate records from the external Tracker API | `https://playground.4geeks.com/tracker/api/v1` |
| `NEXT_PUBLIC_NEXOVA_API_URL` | Nexova users, authentication, and profiles | `http://127.0.0.1:8000` |

From this directory, start Next.js with the Nexova API origin:

```bash
NEXT_PUBLIC_NEXOVA_API_URL=http://127.0.0.1:8000 npm run dev
```

The Nexova API must be running with valid `JWT_SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_MINUTES` settings; see `services/api/README.md`. `NEXT_PUBLIC_*` values are bundled at build time, so set them before `npm run build`. Never put secrets in a `NEXT_PUBLIC_*` variable or commit `.env*` files.

## Authentication Routes

| Route | Access |
|---|---|
| `/login`, `/register` | Public |
| `/`, `/candidates/[id]`, `/account/profile` | Client-side Nexova session guard |
| `/forgot-password`, `/reset-password` | Public recovery pages added in stage 5 |
| `/account/change-password` | Protected policy prepared in stage 4; page is added in stage 6 |

Protected Nexova requests send `Authorization: Bearer <token>`. Only a protected `401` expires the session; `403`, network errors, and `5xx` responses do not. The guard protects the tracker UI, not candidate data returned by the external Tracker API, which does not validate Nexova JWTs. The public website in `uis/website/` is separate and has no auth guard.

`lib/nexova-auth-routes.ts` provides the shared public/protected path policy for
the guard and session-expiry navigation. Expiry events on login, registration or
recovery do not redirect away from the public view. Protected views retain the
existing login redirection. Public recovery errors never clear a previous session;
an authenticated change with a rejected Bearer retains the existing expiry flow.

## AUTH-03 Client Integration

Stage 4 extends the existing Nexova client, not `lib/api.ts` or the external
candidate API. The backend endpoints are implemented; this stage does not create
password forms or certify real email delivery. See the
[requirements and stage board](../../restablecimiento-contrasena.md#plan-de-trabajo-por-etapas)
and [API configuration](../../services/api/README.md#resend-configuration).

| Client function | Input type | Endpoint | Session |
|---|---|---|---|
| `requestNexovaPasswordReset` | `NexovaForgotPasswordInput` (`email`) | `POST /auth/forgot-password` | Public, no Bearer |
| `resetNexovaPassword` | `NexovaResetPasswordInput` (`token`, `new_password`) | `POST /auth/reset-password` | Public, no Bearer |
| `changeNexovaPassword` | `NexovaChangePasswordInput` (`current_password`, `new_password`) | `POST /auth/change-password` | Required Bearer |

All return `Promise<NexovaAuthActionResponse>` containing `message`, use
`NEXT_PUBLIC_NEXOVA_API_URL` and reuse the existing request/error handling.
Failures reject rather than becoming successful responses. Passwords/reset tokens
are only JSON request data, not URLs, localStorage or logs. Only the access token
uses the existing session store; public reset does not mutate that session itself.
The reset screen will handle post-success navigation and prior local-session cleanup
in stage 5. No Resend key belongs in this frontend or a `NEXT_PUBLIC_*` variable.

Stage 4 verification on 2026-10-18:

- Full `npm run lint` and `npm run build` passed, including build-time TypeScript;
	diagnostics for five touched TypeScript/TSX files were clear. The known Next.js
	multiple-lockfile warning remains. Build/dev automatically load the existing
	local environment; no file contents were inspected, changed or printed.
- In-memory checks compiled the real client with the project's ES2017 target.
	They verified URL/payload/Bearer, public `400/401/403/503` without session loss,
	protected `401` expiration, preserved session on other errors/network failure,
	and no protected fetch without a token. Simulated hooks checked eight public/
	private paths, expiry-event navigation and listener cleanup; this is not a
	mounted browser/React interaction test or a newly declared frontend test suite.
- The real SDK called an ephemeral Uvicorn API with temporary synthetic accounts,
	configuration and injected email sender: equal forgot feedback, reset, login,
	`/auth/me`, wrong-current-password rejection, authenticated change, old-password
	rejection and token reuse rejection passed. Tokens passed through process stdin,
	not command arguments or logs; the server and temporary data were cleaned up.
- Local Next HTTP smoke returned `200` for login/register forms and the profile's
	unauthenticated loader. No new password pages exist in the build yet; browser
	acceptance and real email receipt remain for later stages. Next dev is available
	on port 3000 for this session; the ephemeral API used above has been stopped.

## Stage 5 Public Recovery Screens

Stage 5 implements the public password recovery flow:

- `/login` ([`components/auth-form.tsx`](components/auth-form.tsx)):
  - Added visible "¿Olvidaste tu contraseña?" link targeting `/forgot-password`.
  - Added accessible confirmation alert on success redirection (`?reset=success`).
- `/forgot-password` ([`app/forgot-password/page.tsx`](app/forgot-password/page.tsx), [`components/forgot-password-form.tsx`](components/forgot-password-form.tsx)):
  - Accessible form requesting `email`.
  - Calls `requestNexovaPasswordReset({ email })`.
  - Generic non-enumerating confirmation: *"Si esa dirección está registrada, recibirás un enlace en breve."*
  - Form and submit button are disabled post-submission to prevent duplicate requests.
  - Accessible error feedback for network/service failures (503, connection loss).
- `/reset-password` ([`app/reset-password/page.tsx`](app/reset-password/page.tsx), [`components/reset-password-form.tsx`](components/reset-password-form.tsx)):
  - Reads `token` query parameter from the URL.
  - Sanitizes the URL immediately using `window.history.replaceState` so the token is not leaked into history, logs, or referrers.
  - Declares `referrer: "no-referrer"` metadata.
  - Client-side validation: minimum 8 characters and confirmation match before calling `resetNexovaPassword`.
  - Cleans up residual local session with `clearNexovaSession()` upon successful reset, then redirects to `/login?reset=success`.
  - Invalid/expired tokens (HTTP 400) display a clear alert and a link to request a new link at `/forgot-password`.

## Validation

Run the available checks from this directory:

```bash
npm run lint
npm run build
```

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
