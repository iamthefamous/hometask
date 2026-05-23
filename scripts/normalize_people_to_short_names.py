import argparse
import asyncio
from collections import defaultdict
from pathlib import Path
import sys

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.utils.normalization import extract_canonical_person_name, normalize_text


async def normalize_people(apply_changes: bool) -> None:
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    people_col = db["people"]
    rel_col = db["relationships"]

    people = await people_col.find({}).to_list(length=200000)
    groups: dict[str, list[dict]] = defaultdict(list)

    for person in people:
        raw_name = person.get("canonical_name", "")
        canonical = extract_canonical_person_name(raw_name)
        if not canonical:
            continue
        groups[normalize_text(canonical)].append(person)

    merge_groups = [rows for rows in groups.values() if len(rows) > 1 or any(extract_canonical_person_name(r["canonical_name"]) != r["canonical_name"] for r in rows)]
    print(f"Groups needing normalization: {len(merge_groups)}")

    updates = 0
    deletes = 0
    rel_updates = 0

    for rows in merge_groups:
        rows_sorted = sorted(rows, key=lambda r: str(r["_id"]))
        primary = rows_sorted[0]
        primary_id = str(primary["_id"])
        short_name = extract_canonical_person_name(primary["canonical_name"]) or primary["canonical_name"]

        alias_set = set(primary.get("aliases", []))
        article_ids = set(primary.get("article_ids", []))

        for row in rows_sorted:
            original_name = row.get("canonical_name", "")
            if original_name != short_name:
                alias_set.add(original_name)
            for alias in row.get("aliases", []):
                if alias != short_name:
                    alias_set.add(alias)
            for aid in row.get("article_ids", []):
                article_ids.add(aid)

        alias_values = sorted(a for a in alias_set if a and a != short_name)
        article_values = sorted(article_ids)

        for row in rows_sorted[1:]:
            old_id = str(row["_id"])
            if apply_changes:
                src = await rel_col.update_many(
                    {"source_person_id": old_id},
                    {"$set": {"source_person_id": primary_id, "source_name": short_name}},
                )
                tgt = await rel_col.update_many(
                    {"target_person_id": old_id},
                    {"$set": {"target_person_id": primary_id, "target_name": short_name}},
                )
                rel_updates += src.modified_count + tgt.modified_count
                await people_col.delete_one({"_id": row["_id"]})
            deletes += 1

        if apply_changes:
            await people_col.update_one(
                {"_id": primary["_id"]},
                {
                    "$set": {
                        "canonical_name": short_name,
                        "normalized_name": normalize_text(short_name),
                        "aliases": alias_values,
                        "article_ids": article_values,
                    }
                },
            )
        updates += 1

    print(f"People to update: {updates}")
    print(f"People to delete (merged duplicates): {deletes}")
    print(f"Relationships to repoint (modified): {rel_updates if apply_changes else 'dry-run'}")
    print("Applied" if apply_changes else "Dry-run only")

    client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize person records to short canonical names.")
    parser.add_argument("--apply", action="store_true", help="Persist changes to MongoDB")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(normalize_people(args.apply))
