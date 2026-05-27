from pydantic import BaseModel, Field, HttpUrl


class ArticleProcessRequest(BaseModel):
    url: HttpUrl


class ArticleData(BaseModel):
    url: HttpUrl
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    published_at: str | None = None
    text: str


class ArticleProcessResponse(BaseModel):
    url: HttpUrl
    status: str
    people_count: int
    relationships_count: int
