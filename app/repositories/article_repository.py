from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class ArticleRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["articles"]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("url", unique=True)
        await self.collection.create_index("published_at")

    async def upsert_article(self, article: dict) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "url": str(article["url"]),
            "title": article.get("title", ""),
            "authors": article.get("authors", []),
            "published_at": article.get("published_at"),
            "text": article["text"],
            "updated_at": now,
        }
        result = await self.collection.find_one_and_update(
            {"url": payload["url"]},
            {"$set": payload, "$setOnInsert": {"created_at": now}},
            upsert=True,
            return_document=True,
        )
        if result and "_id" in result:
            return str(result["_id"])

        created = await self.collection.find_one({"url": payload["url"]}, {"_id": 1})
        if not created:
            raise RuntimeError("Failed to persist article")
        return str(created["_id"])
