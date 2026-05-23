from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_person_repository, get_relationship_repository
from app.repositories.person_repository import PersonRepository
from app.repositories.relationship_repository import RelationshipRepository
from app.schemas.people import PeopleListResponse, PersonDetailResponse, PersonListItem, PersonRelationships

router = APIRouter(prefix="/people", tags=["people"])


@router.get("", response_model=PeopleListResponse)
async def list_people(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    person_repo: PersonRepository = Depends(get_person_repository),
):
    rows, total = await person_repo.list_people(page=page, limit=limit)
    return PeopleListResponse(
        page=page,
        limit=limit,
        total=total,
        people=[
            PersonListItem(
                id=str(row["_id"]),
                canonical_name=row["canonical_name"],
                aliases=row.get("aliases", []),
            )
            for row in rows
        ],
    )


@router.get("/{person_id}", response_model=PersonDetailResponse)
async def get_person(
    person_id: str,
    person_repo: PersonRepository = Depends(get_person_repository),
    relationship_repo: RelationshipRepository = Depends(get_relationship_repository),
):
    person = await person_repo.get_person(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    relationships = await relationship_repo.get_person_relationships(person_id)

    return PersonDetailResponse(
        id=str(person["_id"]),
        canonical_name=person["canonical_name"],
        aliases=person.get("aliases", []),
        relationships=PersonRelationships(**relationships),
    )
