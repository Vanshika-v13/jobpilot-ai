import json
import sys
import asyncio
import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from core.config import settings
from api.v1.router import api_router
from database.connection import connect_to_mongo, close_mongo_connection


class SafeJSONResponse(JSONResponse):
    """JSON response that escapes non-ASCII characters (e.g. ₹ → \\u20b9).

    Starlette's default JSONResponse uses ``ensure_ascii=False``, which sends
    multi-byte UTF-8 characters as raw bytes.  Some consumers (notably
    PowerShell's ``Invoke-RestMethod`` on Windows) decode those bytes using
    the system codepage (cp1252) instead of UTF-8, producing mojibake.

    Using ``ensure_ascii=True`` encodes every non-ASCII character as a
    ``\\uXXXX`` JSON escape sequence, which is universally safe.
    """

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=True,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(
    title="JobPilot AI API",
    description="AI-driven job application assistant API",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=SafeJSONResponse,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the primary API router under /api/v1
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to JobPilot AI API. Access /api/v1/health for health checks."}
