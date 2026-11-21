from pymongo import MongoClient
from pymongo.errors import PyMongoError
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URI") or "mongodb://localhost:27017"
DATABASE_NAME = os.getenv("DATABASE_NAME") or "DiviEat"

mdb_conn = MongoClient(
    MONGODB_URL,
    serverSelectionTimeoutMS=5000,
)
db = mdb_conn[DATABASE_NAME]


def test_database_connection(db) -> bool:
    try:
        db.command("ping")
        print(f"Database connection successful: {DATABASE_NAME}")
        return True
    except PyMongoError as error:
        print(f"Database connection error: {error}")
        return False


def close_database_connection() -> None:
    mdb_conn.close()
