from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.db.mongo import close_mongo_connection, connect_to_mongo, get_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "message": "News People Knowledge Graph API",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    db = get_database()
    await db.command("ping")

    return {
        "status": "ok",
        "database": "connected",
        "environment": settings.app_env,
    }