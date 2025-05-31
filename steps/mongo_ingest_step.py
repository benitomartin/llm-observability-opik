from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from zenml import step

# Load environment variables and config
load_dotenv()

# MONGODB_URI = os.getenv("MONGODB_URI")

MONGODB_URI = "mongodb://root:root@localhost:27017/"


@step
def mongo_ingest_step(documents: list[dict[str, Any]]) -> None:
    mongodb_uri = MONGODB_URI
    if not mongodb_uri:
        raise ValueError("MONGODB_URI environment variable not set")

    client: MongoClient = MongoClient(mongodb_uri)
    db = client["football"]
    collection = db["teams"]

    for doc in documents:
        existing = collection.find_one({"team": doc["team"], "source_url": doc["source_url"]})

        if existing:
            if existing.get("content") != doc["content"]:
                collection.replace_one({"team": doc["team"], "source_url": doc["source_url"]}, doc)
                print(f"✅ Updated document for team: {doc['team']}")
            else:
                print(f"⏭️ No change for team: {doc['team']}, skipping update.")
        else:
            collection.insert_one(doc)
            print(f"🆕 Inserted new document for team: {doc['team']}")
