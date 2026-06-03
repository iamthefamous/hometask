from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.repositories.person_repository import PersonRepository


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, length=None):
        return list(self.rows)


class _Collection:
    def __init__(self, rows):
        self.rows = rows
        self.indexes = []

    def aggregate(self, _pipeline):
        groups = {}
        for row in self.rows:
            if "normalized_name" in row:
                key = row.get("normalized_name")
            else:
                evidence = row.get("evidence", {})
                key = (
                    row.get("source_person_id"),
                    row.get("target_person_id"),
                    row.get("normalized_type"),
                    evidence.get("article_url"),
                    evidence.get("sentence"),
                )
            if not key:
                continue
            groups.setdefault(key, []).append(row["_id"])
        return _Cursor(
            [
                {"_id": key, "ids": ids, "count": len(ids)}
                for key, ids in groups.items()
                if len(ids) > 1
            ]
        )

    def find(self, query):
        ids = set(query["_id"]["$in"])
        return _Cursor([row for row in self.rows if row["_id"] in ids])

    async def update_one(self, query, update):
        for row in self.rows:
            if row["_id"] == query["_id"]:
                row.update(update.get("$set", {}))
                return

    async def update_many(self, query, update):
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                row.update(update.get("$set", {}))

    async def delete_many(self, query):
        ids = set(query["_id"]["$in"])
        self.rows[:] = [row for row in self.rows if row["_id"] not in ids]

    async def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))


class _Db:
    def __init__(self, people, relationships):
        self.collections = {
            "people": _Collection(people),
            "relationships": _Collection(relationships),
        }

    def __getitem__(self, name):
        return self.collections[name]


@pytest.mark.asyncio
async def test_ensure_indexes_merges_duplicate_people_before_unique_index():
    old_id = ObjectId()
    duplicate_id = ObjectId()
    people = [
        {
            "_id": old_id,
            "canonical_name": "Alyssa Stringer",
            "normalized_name": "alyssa stringer",
            "aliases": ["Alyssa"],
            "article_ids": ["a1"],
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        },
        {
            "_id": duplicate_id,
            "canonical_name": "Alyssa Stringer",
            "normalized_name": "alyssa stringer",
            "aliases": ["Stringer"],
            "article_ids": ["a2"],
            "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        },
    ]
    relationships = [
        {
            "_id": ObjectId(),
            "source_person_id": str(duplicate_id),
            "source_name": "Alyssa Stringer",
            "target_person_id": "p2",
            "target_name": "Sam Altman",
            "normalized_type": "interviewed",
            "evidence": {"article_url": "https://t.co/1", "sentence": "x"},
        }
    ]
    db = _Db(people, relationships)

    await PersonRepository(db).ensure_indexes()

    assert len(people) == 1
    assert people[0]["_id"] == old_id
    assert people[0]["aliases"] == ["Alyssa", "Stringer"]
    assert people[0]["article_ids"] == ["a1", "a2"]
    assert relationships[0]["source_person_id"] == str(old_id)
    assert db["people"].indexes[0][0] == ("normalized_name",)
