from pydantic import BaseModel, ConfigDict, Field

from app.schemas.people import PersonExtraction
from app.schemas.relationship import RelationshipExtraction


class LLMGraphOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    people: list[PersonExtraction] = Field(default_factory=list)
    relationships: list[RelationshipExtraction] = Field(default_factory=list)
