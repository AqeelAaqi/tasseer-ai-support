"""Human handoff via WhatsApp Cloud API directly (no ManyChat).

Two ways this gets used:
1. `build_customer_deeplink` - a wa.me link opened by the customer's app,
   prefilled with a support summary, landing in the support team's WhatsApp
   inbox. Zero API credentials needed; works from day one.
2. `notify_support_team` - proactively push the handoff summary into an
   internal WhatsApp group/number via the Cloud API, so the rep sees it
   before the customer's message even arrives. Requires WHATSAPP_* config.
"""

from __future__ import annotations

from urllib.parse import quote

import httpx

from app.core.config import settings
from app.skills.context import SupportContext


def build_customer_deeplink(ctx: SupportContext, reason: str) -> str:
    order_ref = ctx.order_id or "no active order"
    message = (
        f"Hello, I need assistance with {order_ref}. "
        f"I was transferred from TASSEER AI Support. Reason: {reason}"
    )
    phone = settings.whatsapp_support_phone_e164.lstrip("+")
    return f"https://wa.me/{phone}?text={quote(message)}"


async def notify_support_team(ctx: SupportContext, reason: str, ai_explanation: str) -> None:
    if not (settings.whatsapp_phone_number_id and settings.whatsapp_access_token
            and settings.whatsapp_support_phone_e164):
        return  # not configured yet - deeplink handoff still works without this

    summary = (
        f"*Support escalation*\n"
        f"Customer: {ctx.customer_name} ({ctx.customer_id})\n"
        f"Order: {ctx.order_id or 'none'}\n"
        f"Service: {ctx.service_type or 'n/a'}\n"
        f"Status: {ctx.status_label or 'unknown'}\n"
        f"Driver assigned: {ctx.driver_assigned}\n"
        f"Driver accepted: {ctx.driver_accepted}\n"
        f"Reason for escalation: {reason}\n"
        f"AI explanation given: {ai_explanation}"
    )

    url = f"https://graph.facebook.com/v20.0/{settings.whatsapp_phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": settings.whatsapp_support_phone_e164,
        "type": "text",
        "text": {"body": summary},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
