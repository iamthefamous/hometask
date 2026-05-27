from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.normalization import normalize_text


class RelationshipRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["relationships"]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("source_person_id")
        await self.collection.create_index("target_person_id")
        await self.collection.create_index("normalized_type")
        await self.collection.create_index(
            [
                ("source_person_id", 1),
                ("target_person_id", 1),
                ("normalized_type", 1),
                ("evidence.article_url", 1),
                ("evidence.sentence", 1),
            ],
            unique=True,
        )

    async def insert_relationship_if_not_exists(
        self,
        source_person_id: str,
        source_name: str,
        target_person_id: str,
        target_name: str,
        relationship_type: str,
        explanation: str,
        article_id: str,
        article_url: str,
        sentence: str,
    ) -> bool:
        normalized_type = normalize_text(relationship_type)
        query = {
            "source_person_id": source_person_id,
            "target_person_id": target_person_id,
            "normalized_type": normalized_type,
            "evidence.article_url": article_url,
            "evidence.sentence": sentence,
        }
        existing = await self.collection.find_one(query, {"_id": 1})
        if existing:
            return False

        doc = {
            "source_person_id": source_person_id,
            "source_name": source_name,
            "target_person_id": target_person_id,
            "target_name": target_name,
            "type": relationship_type,
            "normalized_type": normalized_type,
            "explanation": explanation,
            "evidence": {
                "article_id": article_id,
                "article_url": article_url,
                "sentence": sentence,
            },
            "created_at": datetime.now(timezone.utc),
        }
        await self.collection.insert_one(doc)
        return True

    async def get_person_relationships(self, person_id: str) -> dict:
        outgoing = await self.collection.find({"source_person_id": person_id}).to_list(length=1000)
        incoming = await self.collection.find({"target_person_id": person_id}).to_list(length=1000)

        def serialize(rows: list[dict]) -> list[dict]:
            return [
                {
                    "id": str(r["_id"]),
                    "source_person_id": r["source_person_id"],
                    "source_name": r["source_name"],
                    "target_person_id": r["target_person_id"],
                    "target_name": r["target_name"],
                    "type": r["type"],
                    "explanation": r["explanation"],
                    "evidence": r["evidence"],
                }
                for r in rows
            ]

        return {"outgoing": serialize(outgoing), "incoming": serialize(incoming)}
