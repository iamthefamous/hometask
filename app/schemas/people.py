from pydantic import BaseModel, Field


class PersonExtraction(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)


class PersonListItem(BaseModel):
    id: str
    canonical_name: str
    aliases: list[str]


class PeopleListResponse(BaseModel):
    page: int
    limit: int
    total: int
    people: list[PersonListItem]


class PersonRelationships(BaseModel):
    outgoing: list[dict] = Field(default_factory=list)
    incoming: list[dict] = Field(default_factory=list)


class PersonDetailResponse(BaseModel):
    id: str
    canonical_name: str
    aliases: list[str]
    relationships: PersonRelationships
