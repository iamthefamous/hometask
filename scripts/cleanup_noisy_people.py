import argparse
import asyncio
from pathlib import Path
import sys
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.utils.normalization import is_probable_person_name


async def cleanup(dry_run: bool) -> None:
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    people = db["people"]
    relationships = db["relationships"]

    cursor = people.find({}, {"_id": 1, "canonical_name": 1})
    noisy_ids: list[ObjectId] = []
    noisy_names: list[str] = []

    async for row in cursor:
        canonical_name = row.get("canonical_name", "")
        if not is_probable_person_name(canonical_name):
            noisy_ids.append(row["_id"])
            noisy_names.append(canonical_name)

    print(f"Detected noisy people: {len(noisy_ids)}")
    for name in noisy_names[:25]:
        print(f"- {name}")
    if len(noisy_names) > 25:
        print(f"... and {len(noisy_names) - 25} more")

    if dry_run or not noisy_ids:
        print("Dry-run mode enabled; no data deleted.")
        client.close()
        return

    people_result = await people.delete_many({"_id": {"$in": noisy_ids}})
    rel_result = await relationships.delete_many(
        {
            "$or": [
                {"source_person_id": {"$in": [str(i) for i in noisy_ids]}},
                {"target_person_id": {"$in": [str(i) for i in noisy_ids]}},
            ]
        }
    )

    print(f"Deleted people: {people_result.deleted_count}")
    print(f"Deleted relationships: {rel_result.deleted_count}")

    client.close()


def parse_args() -> Any:
    parser = argparse.ArgumentParser(description="Remove noisy person records from MongoDB.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply deletions. Without this flag, script runs in dry-run mode.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(cleanup(dry_run=not args.apply))
