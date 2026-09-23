# TASSEER AI Support

A context-aware customer support agent for TASSEER, embedded directly in the TASSEER app —
**no ManyChat**. It already knows the authenticated customer, their active transport request,
driver assignment, and latest status before they type a word, and only ever states operational
facts it actually read from TASSEER's live database.

```
TASSEER App (in-app chat)
        │  customer_id (via short-lived support token) + message
        ▼
TASSEER Support API (this repo, FastAPI)
        │
        ├── reads ──► Tasseer MySQL DB (read-only)   ← Source of Truth
        │
        └── calls ──► Claude (language understanding + reply generation)
        │
        ▼
   reply to customer            (or, on escalation)
                                        │
                                        ▼
                              WhatsApp (human handoff, direct Cloud API)
```

## Why no ManyChat

The channel is the TASSEER app itself — a native chat screen calling this API directly — instead
of a third-party chat platform. Escalation to a human still goes out over WhatsApp, but via
Meta's Cloud API directly (`app/integrations/whatsapp.py`), not through ManyChat as an
intermediary.

## Status

Working MVP against the real Tasseer schema. The status/payment/driver-assignment logic in
`app/skills/queries.py` was grounded by reading the actual `api.ksatasseerltdapi.com`
PHP/CodeIgniter model code (not guessed) — see [`TODO_INTEGRATION.md`](TODO_INTEGRATION.md) for
what's confirmed vs. the handful of items that still need a live-DB check or a product decision
before this touches production traffic.

## Layout

```
app/
  core/           config, DB connection (read-only), auth, conversation logging
  integrations/   Claude (LLM), WhatsApp Cloud API (human handoff)
  skills/         controlled read functions over the Tasseer DB (support_get_*)
  api/            FastAPI routes (/api/support/chat, /api/support/escalate)
```

The AI never gets raw DB access — it only ever sees the structured `SupportContext` the
`skills` layer resolved, matching the "controlled skills, not unrestricted DB access" design in
the original concept note.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DB (read-only user!), Anthropic key, WhatsApp config
uvicorn app.main:app --reload
```

## Endpoints

- `POST /api/support/chat` — `{"message": "..."}`, `Authorization: Bearer <the app's existing
  session token>` → `{"reply": "...", "escalated": false, "whatsapp_link": null}`
- `POST /api/support/escalate` — force a human handoff regardless of what the AI decided,
  returns a WhatsApp deep link prefilled with the order context.

## Roadmap

1. Horse Transport support (this repo's initial focus)
2. Extend the same `skills` pattern to Boarding, Training, Horse Services, Experiences
