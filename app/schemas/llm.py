from pydantic import BaseModel, Field

from app.schemas.people import PersonExtraction
from app.schemas.relationship import RelationshipExtraction


class LLMGraphOutput(BaseModel):
    people: list[PersonExtraction] = Field(default_factory=list)
    relationships: list[RelationshipExtraction] = Field(default_factory=list)
