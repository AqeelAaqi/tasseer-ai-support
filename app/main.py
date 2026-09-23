from fastapi import FastAPI

from app.api.chat import router as chat_router

app = FastAPI(title="TASSEER AI Support", version="0.1.0")
app.include_router(chat_router, prefix="/api/support", tags=["support"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
