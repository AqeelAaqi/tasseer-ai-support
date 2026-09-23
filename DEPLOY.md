# Deploying tasseer-ai-support

Two ready-to-use paths. Pick one.

## Option A — Namecheap shared hosting (cPanel), same account as the main API

Since `api.ksatasseerltdapi.com` already lives on Namecheap/cPanel hosting, putting this
service on the **same account** is likely the easiest path for DB connectivity — the MySQL
server is probably only reachable from that same host/account, not from the public internet, so
a third-party host (Render, Fly, etc.) may not even be able to reach it without extra setup
(an SSH tunnel, or asking Namecheap support to allow-list a remote IP). Deploying alongside the
existing DB sidesteps that entirely.

Namecheap's shared/cPanel plans run Python apps through **cPanel's "Setup Python App"** (Phusion
Passenger under the hood), not a plain `uvicorn` process — see `passenger_wsgi.py` in this repo,
which adapts the FastAPI (ASGI) app to the WSGI interface Passenger expects.

Steps, in cPanel:

1. **Create a subdomain** for this service, e.g. `support.ksatasseerltdapi.com` (matches the
   placeholder already wired into the Android/iOS app's `SupportApiClient.BASE_URL` — use that
   exact subdomain, or update that constant to whatever you pick, then rebuild the app).
2. **Setup Python App** → create a new application:
   - Python version: 3.11+ if offered (3.9+ works, but match `.python-version` in this repo if
     possible)
   - Application root: wherever you upload this repo's files, e.g. `tasseer-ai-support`
   - Application URL: the subdomain from step 1
   - **Application startup file**: `passenger_wsgi.py`
   - **Application Entry point**: `application`
3. **Upload the code**: either `git clone` this repo into the application root via cPanel's Git
   Version Control feature (if available on your plan) or upload/extract a zip of it via File
   Manager. Either way, the folder needs every file in this repo, `passenger_wsgi.py` included.
4. Back in Setup Python App, open the app and use **"Run Pip Install"** (or its terminal) to
   install `requirements.txt` into the virtualenv cPanel created for you.
5. Set environment variables in the same Setup Python App screen (`TASSEER_DB_HOST`,
   `TASSEER_DB_USER`, `TASSEER_DB_PASSWORD` — a dedicated **read-only** DB user, see
   `TODO_INTEGRATION.md` — `TASSEER_DB_NAME`, `ANTHROPIC_API_KEY`, `TASSEER_API_BASE_URL=https://
   api.ksatasseerltdapi.com`, and the `WHATSAPP_*` ones once you have Meta credentials). If your
   cPanel version doesn't expose an env-var UI, fall back to a `.env` file in the application
   root (already gitignored, `python-dotenv` in requirements.txt loads it automatically).
6. **Restart** the app from the Setup Python App screen after any code or env change.
7. Verify: `https://support.ksatasseerltdapi.com/health` should return `{"status":"ok"}`.

Limitation worth knowing: Passenger/WSGI has no concept of async streaming, so this only works
for the plain request/response JSON endpoints this service actually has (`/api/support/chat`,
`/api/support/escalate`, `/health`) — which is all there is today. If a future endpoint needs
server-sent events or WebSockets, it won't work through this path and would need Option B (or a
real VPS) instead.

## Option B — Render.com (free tier, any provider)

`render.yaml` in this repo is a Render "Blueprint" — connect the GitHub repo on Render, it reads
that file and creates the service with the right build/start commands automatically. You'll be
prompted to fill in the `sync: false` env vars (DB credentials, `ANTHROPIC_API_KEY`, WhatsApp
credentials) in Render's dashboard.

Free-tier tradeoff: the service sleeps after 15 minutes idle, so the first support message after
a quiet period gets a ~30-60s cold-start delay before replying.

**This only works if your MySQL database accepts connections from outside Namecheap's network**
(check with your host/DB admin) — otherwise use Option A, or keep Render for everything except
the DB and have it connect over an SSH tunnel to the Namecheap box, which is more setup than is
worth documenting here unless you actually hit this wall.
