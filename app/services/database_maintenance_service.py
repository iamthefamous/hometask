from motor.motor_asyncio import AsyncIOMotorDatabase


class DatabaseMaintenanceService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def clear_graph_collections(self) -> dict[str, int]:
        deleted: dict[str, int] = {}
        for collection_name in ("articles", "people", "relationships"):
            result = await self.db[collection_name].delete_many({})
            deleted[collection_name] = result.deleted_count
        return deleted
