"""support_get_* skills: the only way the AI layer ever touches Tasseer data.

Every value used here (status codes, columns, the driver-assignment logic) is
grounded in a direct read of api.ksatasseerltdapi.com's actual PHP model code
(application/models/Request_model.php, Payment_model.php), not assumed from
the original ManyChat concept note. See TODO_INTEGRATION.md for the two
points still flagged as genuinely ambiguous in that source code itself
(items are called out inline below too).
"""

from __future__ import annotations

import datetime as dt

from app.core.db import fetch_one
from app.skills.context import SupportContext

# request_of_horses.status -> (english label, customer-facing explanation)
# Source: the app's own status_message CASE statement, Payment_model.php:744-815,
# cross-checked against every place `status` is written in Request_model.php.
STATUS_LABELS: dict[int | None, tuple[str, str]] = {
    None: (
        "Not yet accepted",
        "Your transport request hasn't been accepted by a driver yet. "
        "It's visible to eligible drivers and we'll notify you as soon as one accepts.",
    ),
    0: (
        "Pending (driver assigned)",
        "A driver has accepted your transport request. The trip hasn't started yet — "
        "we'll update you once the driver confirms pickup.",
    ),
    1: (
        "Completed",
        "Your transport request has been completed and payment has been settled. "
        "Thank you for using TASSEER!",
    ),
    2: (
        "Cancelled by you",
        "This request was cancelled by you.",
    ),
    3: (
        "Cancelled by driver",
        "The driver who had accepted this request cancelled after accepting. "
        "We're sorry for the inconvenience — you're welcome to submit a new request.",
    ),
    4: (
        "Delivered, payment pending",
        "The driver has completed the trip. We're just waiting on payment to be "
        "finalized before this request is marked complete.",
    ),
    5: (
        "In progress",
        "Your horse has been picked up (pickup was verified) and the trip is currently "
        "under way to the delivery location.",
    ),
}

# payments.payment_status, on the row where pay_to_id != 1 (i.e. the customer's
# payment for the ride, not the internal driver-commission row).
# Source: Hayperpay.php:107-131, Request_model.php:1550.
PAYMENT_STATUS_LABELS: dict[int, str] = {
    0: "pending",
    1: "paid",
    4: "declined",
}


def _get_active_request(customer_id: int):
    # "Active" mirrors the app's own get_my_request(): anything except
    # status 1 (completed) or 2 (customer-cancelled) counts as current.
    # NOTE: this deliberately also matches status=3 (driver-cancelled) -
    # that's the existing app's real behavior, not a bug we're introducing.
    return fetch_one(
        """
        SELECT r.id, r.request_ID, r.status, r.accepted_by, r.otp_is_verified,
               r.created_at, r.end_date,
               v.user_id AS driver_user_id,
               u.name AS driver_name
        FROM request_of_horses r
        LEFT JOIN vehicles v ON v.id = r.accepted_by
        LEFT JOIN users u ON u.id = v.user_id
        WHERE r.user_id = :customer_id
          AND r.status NOT IN (1, 2)
          AND r.is_active = 1
        ORDER BY r.created_at DESC
        LIMIT 1
        """,
        {"customer_id": customer_id},
    )


def _get_latest_request(customer_id: int):
    # Fallback for "what happened with my last order" once there's no active one.
    return fetch_one(
        """
        SELECT r.id, r.request_ID, r.status, r.accepted_by, r.otp_is_verified,
               r.created_at, r.end_date,
               v.user_id AS driver_user_id,
               u.name AS driver_name
        FROM request_of_horses r
        LEFT JOIN vehicles v ON v.id = r.accepted_by
        LEFT JOIN users u ON u.id = v.user_id
        WHERE r.user_id = :customer_id
        ORDER BY r.created_at DESC
        LIMIT 1
        """,
        {"customer_id": customer_id},
    )


def _get_payment_status_label(request_id: int) -> str | None:
    row = fetch_one(
        """
        SELECT payment_status FROM payments
        WHERE request_id = :request_id AND pay_to_id != 1
        ORDER BY id DESC LIMIT 1
        """,
        {"request_id": request_id},
    )
    if row is None:
        return None
    return PAYMENT_STATUS_LABELS.get(row.payment_status, "unknown")


def support_get_customer_context(customer_id: int) -> SupportContext:
    customer = fetch_one(
        "SELECT id, name, is_active FROM users WHERE id = :id", {"id": customer_id}
    )
    if customer is None:
        raise ValueError(f"No such customer_id={customer_id}")

    row = _get_active_request(customer_id) or _get_latest_request(customer_id)

    if row is None:
        return SupportContext(
            customer_id=customer.id,
            customer_name=customer.name,
            has_active_order=False,
        )

    label, explanation = STATUS_LABELS.get(
        row.status, ("Unknown", "We don't have a clear status for this request right now.")
    )

    # Driver assignment and acceptance are the SAME event in this system
    # (accept_request() sets accepted_by and status=0 together) - there is no
    # "assigned but not yet accepted" state to distinguish, unlike the
    # original concept note assumed. See TODO_INTEGRATION.md #2.
    driver_assigned = row.accepted_by is not None
    driver_accepted = True if driver_assigned else None

    last_update = row.end_date or row.created_at
    last_update_iso = last_update.isoformat() if isinstance(last_update, dt.datetime) else None

    return SupportContext(
        customer_id=customer.id,
        customer_name=customer.name,
        has_active_order=True,
        order_id=row.request_ID,
        service_type="horse_transport",
        status_code=row.status,
        status_label=label,
        status_explanation=explanation,
        driver_assigned=driver_assigned,
        driver_accepted=driver_accepted,
        driver_name=row.driver_name,
        pickup_confirmed=bool(row.otp_is_verified) if row.otp_is_verified is not None else None,
        delivered=row.status in (1, 4),
        payment_status_label=_get_payment_status_label(row.id),
        last_update_at=last_update_iso,
    )


def resolve_support_context(customer_id: int) -> SupportContext:
    return support_get_customer_context(customer_id)
