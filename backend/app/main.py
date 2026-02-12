from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import API_PREFIX, CORS_ORIGINS
from app.db.session import Base, engine
from app.mcp.server import router as mcp_router


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Infra Change Risk Engine",
    version="0.2.0",
    description=(
        "AI-augmented pre-deploy gate: deterministic policy engine + "
        "LLM fix-generation agent + MCP tool server."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=API_PREFIX)
app.include_router(mcp_router, prefix="/mcp", tags=["MCP"])

