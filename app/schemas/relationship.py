from pydantic import BaseModel, ConfigDict, field_validator


class RelationshipExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    type: str
    explanation: str
    evidence: str

    @field_validator("source", "target", "type", "explanation", "evidence")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class RelationshipEvidence(BaseModel):
    article_id: str
    article_url: str
    sentence: str
