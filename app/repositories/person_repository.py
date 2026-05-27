from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.utils.normalization import normalize_text


class PersonRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["people"]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("normalized_name", unique=True)
        await self.collection.create_index("aliases")

    async def find_person_for_name(self, name: str):
        normalized = normalize_text(name)
        person = await self.collection.find_one({"normalized_name": normalized})
        if person:
            return person
        return await self.collection.find_one({"aliases": name})

    async def upsert_person(self, canonical_name: str, aliases: list[str], article_id: str) -> str:
        normalized = normalize_text(canonical_name)
        now = datetime.now(timezone.utc)
        alias_values = [a for a in aliases if a and a != canonical_name]
        person = await self.find_person_for_name(canonical_name)
        if person:
            updates = {
                "$addToSet": {
                    "aliases": {"$each": alias_values},
                    "article_ids": article_id,
                },
                "$set": {"updated_at": now},
            }
            await self.collection.update_one({"_id": person["_id"]}, updates)
            return str(person["_id"])

        doc = {
            "canonical_name": canonical_name,
            "normalized_name": normalized,
            "aliases": alias_values,
            "article_ids": [article_id],
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self.collection.insert_one(doc)
            return str(result.inserted_id)
        except DuplicateKeyError:
            # Another concurrent task created this person first. Merge and continue.
            person = await self.collection.find_one({"normalized_name": normalized})
            if not person:
                raise
            updates = {
                "$addToSet": {
                    "aliases": {"$each": alias_values},
                    "article_ids": article_id,
                },
                "$set": {"updated_at": now},
            }
            await self.collection.update_one({"_id": person["_id"]}, updates)
            return str(person["_id"])

    async def list_people(self, page: int, limit: int) -> tuple[list[dict], int]:
        total = await self.collection.count_documents({})
        cursor = self.collection.find({}).sort("canonical_name", 1).skip((page - 1) * limit).limit(limit)
        rows = await cursor.to_list(length=limit)
        return rows, total

    async def get_person(self, person_id: str):
        return await self.collection.find_one({"_id": ObjectId(person_id)})
