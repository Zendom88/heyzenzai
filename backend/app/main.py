"""
FastAPI application entrypoint.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.webhook import router as webhook_router
from app.routes.oauth import router as oauth_router
from app.routes.health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("HeyZenzai backend starting up...")
    yield
    logger.info("HeyZenzai backend shutting down.")


app = FastAPI(
    title="HeyZenzai API",
    description="WhatsApp AI Booking Agent for Singapore Beauty & Wellness SMEs",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if True else None,  # Disable in production via env check
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://heyzenzai.pages.dev", "https://heyzenzai.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Routers
app.include_router(webhook_router, tags=["WhatsApp Webhook"])
app.include_router(oauth_router, prefix="/oauth", tags=["Google OAuth"])
app.include_router(health_router, tags=["Health"])
