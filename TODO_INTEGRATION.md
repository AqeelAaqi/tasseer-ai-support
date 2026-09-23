# Integration notes

Everything below was confirmed by reading the actual `api.ksatasseerltdapi.com` PHP/CodeIgniter
code (`application/models/Request_model.php`, `Payment_model.php`, `application/controllers/api/
Users.php`, `application/libraries/Authorization_Token.php`) — not assumed from the original
ManyChat concept note, which described a cleaner status workflow than the real system has.

## Resolved

- **Status legend** (`request_of_horses.status`) — encoded in `app/skills/queries.py::STATUS_LABELS`,
  taken directly from the app's own `status_message` `CASE` statement
  (`Payment_model.php:744-815`), cross-checked against every place `status` is written in
  `Request_model.php`. Values: `NULL`=not accepted, `0`=driver assigned/pending start,
  `1`=completed+paid, `2`=cancelled by customer, `3`=cancelled by driver after accepting,
  `4`=ride ended, payment pending, `5`=in progress (pickup OTP verified).
- **Driver assignment == acceptance**, one event, not two (`accept_request()` sets `accepted_by`
  and `status=0` together). `SupportContext.driver_assigned` / `driver_accepted` reflect that —
  there's no "assigned but awaiting driver acceptance" state to show, unlike the original
  concept note assumed.
- **`request_status`** is not a real column — it's just a JSON response key that echoes
  `request_of_horses.status`. Ignored; we read `status` directly.
- **Pickup confirmation**: `otp_is_verified` (bool) flips to 1 only at pickup OTP verification.
  There is **no separate delivery OTP or "delivered_at" timestamp** — `end_date` (set in
  `end_ride()`) is the closest thing to a delivery timestamp, and there's no field
  distinguishing "loading the horse" from "en route" (`status=5` covers the whole span). If a
  customer asks specifically "has my horse been loaded yet", the schema genuinely can't answer
  that more precisely than "trip is in progress" — the AI is instructed to say so rather than
  guess (see `app/integrations/claude.py` system prompt).
- **Payment status**: `payments.payment_status` on the row where `pay_to_id != 1` — `0`=pending,
  `1`=paid, `4`=declined. Encoded in `app/skills/queries.py::PAYMENT_STATUS_LABELS`.
- **Customer auth**: no session/token table exists to read. `app/core/auth.py` passes the
  customer's existing bearer token straight through to the live `GET /api/user` endpoint
  (`Users.php::user_get`) to resolve identity — no new PHP endpoint needed, no shared JWT
  secret to distribute.

## Still open / needs a decision or DB check before production

1. **`request_ID` vs `request_Id`** — the PHP code references what may be one column aliased two
   ways, or two distinct columns; couldn't disambiguate from application code alone. Run
   `DESCRIBE request_of_horses;` against the real DB and fix `app/skills/queries.py` if the
   column name assumed there (`request_ID`) is wrong.
2. **Read-only DB user**: create a dedicated MySQL account with `SELECT`-only grants on
   `ksatntau_api` for `TASSEER_DB_USER`/`PASSWORD` in `.env` — do not reuse the main app's
   read/write credentials, even though this codebase only ever issues `SELECT`s. The guarantee
   should live at the DB grant level.
3. **Stale-session gap inherited from the existing auth system**: the PHP JWT has no
   revocation list and a ~360-day expiry, and `validateToken()` never re-checks `users.is_active`
   on every call — only login does. Calling `GET /api/user` (as this service does) closes that
   gap for support chat specifically, since it re-reads the live `users` row, but it's worth
   flagging to whoever owns the main API as a pre-existing issue beyond this project's scope.
4. **`status = 3` (driver-cancelled) app quirk**: the existing app's own "current request" query
   shows status=3 as still "active", but its "history" query excludes it — so a driver-cancelled
   ride is invisible in both the customer's current view and their history in the app today.
   `_get_active_request()` in `app/skills/queries.py` intentionally mirrors this real behavior;
   worth a product decision on whether to fix it (in the main app) rather than paper over it here.
5. **WhatsApp Cloud API credentials** (`WHATSAPP_*` in `.env.example`) — need a Meta Business
   account + phone number set up; until configured, human handoff still works via the `wa.me`
   deep link in `build_customer_deeplink`, just without the proactive push to the support team.
6. Extend `app/skills/queries.py` + `STATUS_LABELS`-style mappings to Boarding, Training, Horse
   Services, Experiences once Horse Transport is validated against real data — those services'
   tables weren't investigated yet.
