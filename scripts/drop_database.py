import argparse
from pathlib import Path
import sys

from pymongo import MongoClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Drop MongoDB database used by this project."
    )
    parser.add_argument(
        "--db-name",
        default=settings.mongodb_db_name,
        help="Database name to drop. Defaults to configured MONGODB_DB_NAME.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually drop the database. Without this flag, script runs in dry-run mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"Mongo URI: {settings.mongodb_uri}")
    print(f"Target DB: {args.db_name}")

    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")

    existing = set(client.list_database_names())
    if args.db_name not in existing:
        print("Database does not exist. Nothing to drop.")
        client.close()
        return

    if not args.apply:
        print("Dry-run mode enabled; no changes made.")
        client.close()
        return

    client.drop_database(args.db_name)
    print(f"Dropped database: {args.db_name}")
    print(f"Remaining databases: {sorted(client.list_database_names())}")
    client.close()


if __name__ == "__main__":
    main()
