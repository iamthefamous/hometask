import argparse
import asyncio
from pathlib import Path
import sys

from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings

GRAPH_COLLECTIONS = ["articles", "people", "relationships"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Drop graph collections without deleting the database.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually drop collections. Without this flag, script runs in dry-run mode.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    existing = set(await db.list_collection_names())
    targets = [name for name in GRAPH_COLLECTIONS if name in existing]

    print(f"Mongo URI: {settings.mongodb_uri}")
    print(f"Target DB: {settings.mongodb_db_name}")
    print(f"Collections found: {sorted(existing)}")
    print(f"Graph collections to drop: {targets}")

    if not args.apply:
        print("Dry-run mode enabled; no changes made.")
        client.close()
        return

    for name in targets:
        await db[name].drop()
        print(f"Dropped collection: {name}")

    final_collections = await db.list_collection_names()
    print(f"Remaining collections: {sorted(final_collections)}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
