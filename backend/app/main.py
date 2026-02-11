from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import API_PREFIX, CORS_ORIGINS
from app.db.session import Base, engine
from app.mcp.server import router as mcp_router


Base.metadata.create_all(bind=engine)

