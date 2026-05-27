from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings


class MongoDB:
    client: AsyncIOMotorClient | None = None
    database: AsyncIOMotorDatabase | None = None


mongo = MongoDB()


async def connect_to_mongo() -> None:
    mongo.client = AsyncIOMotorClient(settings.mongodb_uri)
    mongo.database = mongo.client[settings.mongodb_db_name]
    await mongo.client.admin.command("ping")


async def close_mongo_connection() -> None:
    if mongo.client is not None:
        mongo.client.close()


def get_database() -> AsyncIOMotorDatabase:
    if mongo.database is None:
        raise RuntimeError("MongoDB database is not initialized")
    return mongo.database
