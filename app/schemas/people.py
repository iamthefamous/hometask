from pydantic import BaseModel, ConfigDict, Field, field_validator


class PersonExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    aliases: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("aliases")
    @classmethod
    def aliases_must_be_non_blank(cls, value: list[str]) -> list[str]:
        cleaned_aliases: list[str] = []
        for alias in value:
            cleaned = alias.strip()
            if not cleaned:
                continue
            if cleaned not in cleaned_aliases:
                cleaned_aliases.append(cleaned)
        return cleaned_aliases


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
