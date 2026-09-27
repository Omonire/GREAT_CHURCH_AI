from fastapi import FastAPI
from church_ai_api.api.ws import router as websocket_router

app = FastAPI(
    title="Great Church AI",
    version="0.1.0",
    description="Realtime AI media assistant API",
)

app.include_router(websocket_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
