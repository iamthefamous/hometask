import pytest

from app.api.cleardb import clear_db
from app.schemas.cleardb import ClearDBResponse
from app.services.database_maintenance_service import DatabaseMaintenanceService


class _DeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


class _FakeCollection:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count
        self.deleted_queries = []

    async def delete_many(self, query: dict):
        self.deleted_queries.append(query)
        return _DeleteResult(self.deleted_count)


class _FakeDB:
    def __init__(self):
        self.collections = {
            "articles": _FakeCollection(2),
            "people": _FakeCollection(3),
            "relationships": _FakeCollection(4),
        }

    def __getitem__(self, name: str):
        return self.collections[name]


@pytest.mark.asyncio
async def test_database_maintenance_service_clears_graph_collections():
    db = _FakeDB()
    service = DatabaseMaintenanceService(db)

    deleted = await service.clear_graph_collections()

    assert deleted == {"articles": 2, "people": 3, "relationships": 4}
    assert db["articles"].deleted_queries == [{}]
    assert db["people"].deleted_queries == [{}]
    assert db["relationships"].deleted_queries == [{}]


@pytest.mark.asyncio
async def test_cleardb_endpoint_function():
    response = await clear_db(maintenance=DatabaseMaintenanceService(_FakeDB()))

    assert response == ClearDBResponse(
        status="cleared",
        deleted={"articles": 2, "people": 3, "relationships": 4},
    )
