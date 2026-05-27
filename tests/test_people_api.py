import pytest
from fastapi import HTTPException

from app.api.people import get_person, list_people


class _PersonRepo:
    async def list_people(self, page, limit):
        return (
            [{"_id": "665f", "canonical_name": "Sam Altman", "aliases": ["Altman", "OpenAI CEO"]}],
            1,
        )

    async def get_person(self, person_id):
        if person_id == "missing":
            return None
        return {"_id": "665f", "canonical_name": "Sam Altman", "aliases": ["Altman", "OpenAI CEO"]}


class _RelationshipRepo:
    async def get_person_relationships(self, person_id):
        return {"outgoing": [], "incoming": []}


@pytest.mark.asyncio
async def test_people_list_endpoint():
    response = await list_people(page=1, limit=20, person_repo=_PersonRepo())
    assert response.total == 1
    assert response.people[0].canonical_name == "Sam Altman"


@pytest.mark.asyncio
async def test_person_detail_endpoint():
    response = await get_person(
        person_id="665f",
        person_repo=_PersonRepo(),
        relationship_repo=_RelationshipRepo(),
    )
    assert response.canonical_name == "Sam Altman"


@pytest.mark.asyncio
async def test_person_detail_404():
    with pytest.raises(HTTPException) as exc:
        await get_person(
            person_id="missing",
            person_repo=_PersonRepo(),
            relationship_repo=_RelationshipRepo(),
        )
    assert exc.value.status_code == 404
