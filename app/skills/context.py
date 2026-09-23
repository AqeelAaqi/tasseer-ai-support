"""SupportContext: the ONLY shape of operational data the LLM ever sees.

Populated by the support_get_* functions in this package, each a thin,
read-only query over the live Tasseer MySQL DB (`request_of_horses`,
`vehicles`, `users`, `payments`). The AI integration layer (app/integrations
/claude.py) is handed this object, never a raw DB connection.
"""

from __future__ import annotations

from pydantic import BaseModel


class SupportContext(BaseModel):
    customer_id: int
    customer_name: str

    has_active_order: bool
    order_id: str | None = None
    service_type: str | None = None  # e.g. "horse_transport"

    # Raw + human-facing status. `status_code` is kept for audit/logging only -
    # it must never be shown to the customer or sent to the LLM verbatim
    # without `status_label` explaining it, per TODO_INTEGRATION.md #1.
    status_code: int | None = None
    status_label: str | None = None
    status_explanation: str | None = None  # pre-written, reviewed customer-facing sentence

    # Assignment and acceptance are the SAME event in Tasseer's current system
    # (a driver "accepting" a request assigns it in one step) - there is no
    # "assigned but pending driver acceptance" state to distinguish, unlike
    # the original ManyChat concept note assumed. driver_accepted is only
    # ever True (when a driver holds the job) or None (no driver yet).
    driver_assigned: bool = False
    driver_accepted: bool | None = None
    driver_name: str | None = None

    pickup_confirmed: bool | None = None
    delivered: bool | None = None

    payment_status_label: str | None = None

    last_update_at: str | None = None  # ISO 8601
