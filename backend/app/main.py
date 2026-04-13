from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.api import agents, awakening, execute, integrations, memory, oracle, standup
from app.ws import nerve_center, minds_eye

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize connections
    print("◎ Gnosis starting up...")
    yield
    # Shutdown: cleanup
    print("◎ Gnosis shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="The Knowledge That Works — AI Agent Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API routes
app.include_router(agents.router, prefix=f"{settings.api_prefix}/agents", tags=["agents"])
app.include_router(awakening.router, prefix=f"{settings.api_prefix}/awaken", tags=["awakening"])
app.include_router(execute.router, prefix=f"{settings.api_prefix}/execute", tags=["execute"])
app.include_router(integrations.router, prefix=f"{settings.api_prefix}/integrations", tags=["integrations"])
app.include_router(memory.router, prefix=f"{settings.api_prefix}/memory", tags=["memory"])
app.include_router(oracle.router, prefix=f"{settings.api_prefix}/oracle", tags=["oracle"])
app.include_router(standup.router, prefix=f"{settings.api_prefix}/standup", tags=["standup"])

# WebSocket routes
app.include_router(nerve_center.router, tags=["ws"])
app.include_router(minds_eye.router, tags=["ws"])


@app.get("/health")
async def health():
    return {"status": "alive", "service": "gnosis"}
