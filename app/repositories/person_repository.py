from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.utils.normalization import normalize_text


class PersonRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["people"]
        self.relationship_collection = db["relationships"]

    async def ensure_indexes(self) -> None:
        await self.merge_duplicate_people()
        await self.collection.create_index("normalized_name", unique=True)
        await self.collection.create_index("aliases")

    async def merge_duplicate_people(self) -> None:
        groups = await self.collection.aggregate(
            [
                {
                    "$match": {
                        "normalized_name": {
                            "$exists": True,
                            "$type": "string",
                            "$ne": "",
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$normalized_name",
                        "ids": {"$push": "$_id"},
                        "count": {"$sum": 1},
                    }
                },
                {"$match": {"count": {"$gt": 1}}},
            ]
        ).to_list(length=None)

        for group in groups:
            docs = await self.collection.find({"_id": {"$in": group["ids"]}}).to_list(
                length=None
            )
            if len(docs) < 2:
                continue

            docs.sort(key=self._person_sort_key)
            primary = docs[0]
            duplicates = docs[1:]
            primary_id = primary["_id"]
            primary_id_str = str(primary_id)
            primary_name = primary.get("canonical_name") or ""

            aliases = self._merged_values(primary.get("aliases", []))
            article_ids = self._merged_values(primary.get("article_ids", []))

            for duplicate in duplicates:
                aliases = self._merged_values(aliases, duplicate.get("aliases", []))
                article_ids = self._merged_values(
                    article_ids, duplicate.get("article_ids", [])
                )
                duplicate_name = duplicate.get("canonical_name")
                if duplicate_name and duplicate_name != primary_name:
                    aliases = self._merged_values(aliases, [duplicate_name])

            await self.collection.update_one(
                {"_id": primary_id},
                {
                    "$set": {
                        "aliases": aliases,
                        "article_ids": article_ids,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )

            duplicate_ids = [doc["_id"] for doc in duplicates]
            for duplicate_id in duplicate_ids:
                duplicate_id_str = str(duplicate_id)
                await self.relationship_collection.update_many(
                    {"source_person_id": duplicate_id_str},
                    {
                        "$set": {
                            "source_person_id": primary_id_str,
                            "source_name": primary_name,
                        }
                    },
                )
                await self.relationship_collection.update_many(
                    {"target_person_id": duplicate_id_str},
                    {
                        "$set": {
                            "target_person_id": primary_id_str,
                            "target_name": primary_name,
                        }
                    },
                )

            await self.collection.delete_many({"_id": {"$in": duplicate_ids}})
            await self._remove_duplicate_relationships()

    def _person_sort_key(self, doc: dict) -> tuple[datetime, str]:
        created_at = doc.get("created_at")
        if not isinstance(created_at, datetime):
            object_id = doc.get("_id")
            created_at = getattr(object_id, "generation_time", datetime.max)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return created_at, str(doc.get("_id", ""))

    def _merged_values(self, *value_lists: list) -> list:
        merged = []
        seen = set()
        for values in value_lists:
            if not isinstance(values, list):
                continue
            for value in values:
                if value in seen:
                    continue
                merged.append(value)
                seen.add(value)
        return merged

    async def _remove_duplicate_relationships(self) -> None:
        groups = await self.relationship_collection.aggregate(
            [
                {
                    "$group": {
                        "_id": {
                            "source_person_id": "$source_person_id",
                            "target_person_id": "$target_person_id",
                            "normalized_type": "$normalized_type",
                            "article_url": "$evidence.article_url",
                            "sentence": "$evidence.sentence",
                        },
                        "ids": {"$push": "$_id"},
                        "count": {"$sum": 1},
                    }
                },
                {"$match": {"count": {"$gt": 1}}},
            ]
        ).to_list(length=None)

        for group in groups:
            ids = group["ids"]
            await self.relationship_collection.delete_many({"_id": {"$in": ids[1:]}})

    async def find_person_for_name(self, name: str):
        normalized = normalize_text(name)
        person = await self.collection.find_one({"normalized_name": normalized})
        if person:
            return person
        return await self.collection.find_one({"aliases": name})

    async def upsert_person(
        self, canonical_name: str, aliases: list[str], article_id: str
    ) -> str:
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
        cursor = (
            self.collection.find({})
            .sort("canonical_name", 1)
            .skip((page - 1) * limit)
            .limit(limit)
        )
        rows = await cursor.to_list(length=limit)
        return rows, total

    async def get_person(self, person_id: str):
        try:
            object_id = ObjectId(person_id)
        except InvalidId:
            return None
        return await self.collection.find_one({"_id": object_id})
