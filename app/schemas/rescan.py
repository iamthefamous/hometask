from pydantic import BaseModel, Field


class RescanRequest(BaseModel):
    pages: int = Field(default=1, ge=1, le=20)


class RescanError(BaseModel):
    url: str
    error: str


class RescanResponse(BaseModel):
    pages_scanned: int
    urls_found: int
    processed: int
    failed: int
    errors: list[RescanError]
