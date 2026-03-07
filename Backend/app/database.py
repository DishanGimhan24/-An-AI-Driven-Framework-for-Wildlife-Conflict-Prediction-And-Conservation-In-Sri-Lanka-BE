import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "wildlife_system")

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_config = Database()

def get_db():
    return db_config.db

async def connect_to_mongo():
    try:
        db_config.client = AsyncIOMotorClient(MONGO_URI)
        db_config.db = db_config.client[DATABASE_NAME]
        print(f"Connected to MongoDB at {MONGO_URI}, Database: {DATABASE_NAME}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")

async def close_mongo_connection():
    if db_config.client:
        db_config.client.close()
        print("Closed MongoDB connection")
