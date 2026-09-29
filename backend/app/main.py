from contextlib import asynccontextmanager

from core.config import settings
from core.database import SessionLocal, init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services import seed

from app.api.routes import auth, dashboard, explain, lender, products, scoring


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.seed_on_startup:
        with SessionLocal() as db:
            seed.seed(db)
    yield


app = FastAPI(title=settings.app_name, version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


for r in (
    auth.router,
    scoring.router,
    explain.router,
    dashboard.router,
    products.router,
    lender.router,
):
    app.include_router(r, prefix=settings.api_prefix)
