from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.core.auth import SupportIdentity, verify_handoff_token
from app.core.logging_store import log_message
from app.integrations.claude import generate_reply
from app.integrations.whatsapp import build_customer_deeplink, notify_support_team
from app.skills.queries import resolve_support_context

# resolve_support_context (sync MySQL query) and generate_reply (sync Anthropic
# call) both do blocking I/O - run them off the event loop so one slow chat
# doesn't stall every other request this instance is handling.

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    escalated: bool
    whatsapp_link: str | None = None


class EscalateRequest(BaseModel):
    reason: str = "Customer requested a human representative."


class EscalateResponse(BaseModel):
    whatsapp_link: str


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, identity: SupportIdentity = Depends(verify_handoff_token)) -> ChatResponse:
    ctx = await run_in_threadpool(resolve_support_context, identity.customer_id)

    log_message(identity.customer_id, ctx.order_id, "customer", body.message, ctx.model_dump())

    result = await run_in_threadpool(generate_reply, ctx, body.message)
    escalated = result["escalate"]

    whatsapp_link = None
    if escalated:
        whatsapp_link = build_customer_deeplink(ctx, reason="AI could not fully resolve the question")
        await notify_support_team(ctx, reason="AI-detected escalation", ai_explanation=result["reply"])

    log_message(identity.customer_id, ctx.order_id, "assistant", result["reply"], ctx.model_dump(), escalated)

    return ChatResponse(reply=result["reply"], escalated=escalated, whatsapp_link=whatsapp_link)


@router.post("/escalate", response_model=EscalateResponse)
async def escalate(
    body: EscalateRequest, identity: SupportIdentity = Depends(verify_handoff_token)
) -> EscalateResponse:
    ctx = await run_in_threadpool(resolve_support_context, identity.customer_id)
    link = build_customer_deeplink(ctx, reason=body.reason)
    await notify_support_team(ctx, reason=body.reason, ai_explanation="(direct customer request, no AI turn)")
    log_message(identity.customer_id, ctx.order_id, "customer", f"[escalate] {body.reason}", ctx.model_dump(), True)
    return EscalateResponse(whatsapp_link=link)
