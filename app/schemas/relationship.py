from pydantic import BaseModel


class RelationshipExtraction(BaseModel):
    source: str
    target: str
    type: str
    explanation: str
    evidence: str


class RelationshipEvidence(BaseModel):
    article_id: str
    article_url: str
    sentence: str
