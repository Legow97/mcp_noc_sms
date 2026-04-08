from fastapi import FastAPI

from app.api.routes.conversation import router as conversation_router
from app.api.routes.health import router as health_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.retrieval import router as retrieval_router
from app.core.config import settings


app = FastAPI(title=settings.app.name)

app.include_router(health_router)
app.include_router(conversation_router)
app.include_router(incidents_router)
app.include_router(retrieval_router)


@app.get("/")
def read_root() -> dict[str, str | bool]:
    return {
        "service": settings.app.name,
        "environment": settings.app.environment,
        "debug": settings.app.debug,
    }
