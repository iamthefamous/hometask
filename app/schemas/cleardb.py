from pydantic import BaseModel


class ClearDBResponse(BaseModel):
    status: str
    deleted: dict[str, int]
