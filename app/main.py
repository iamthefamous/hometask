from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.articles import router as articles_router
from app.api.people import router as people_router
from app.api.rescan import router as rescan_router
from app.core.config import settings
from app.db.mongo import close_mongo_connection, connect_to_mongo, get_database
from app.repositories.article_repository import ArticleRepository
from app.repositories.person_repository import PersonRepository
from app.repositories.relationship_repository import RelationshipRepository


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_to_mongo()
    db = get_database()
    await ArticleRepository(db).ensure_indexes()
    await PersonRepository(db).ensure_indexes()
    await RelationshipRepository(db).ensure_indexes()
    yield
    await close_mongo_connection()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(articles_router)
app.include_router(rescan_router)
app.include_router(people_router)


@app.get("/health")
async def health_check():
    db = get_database()
    await db.command("ping")
    return {"status": "ok"}
