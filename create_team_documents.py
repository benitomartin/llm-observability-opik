import os
from datetime import UTC, datetime
from typing import Any

import yaml
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables and config
load_dotenv()

# MONGODB_URI = os.getenv("MONGODB_URI")

MONGODB_URI = "mongodb://root:root@localhost:27017/"


if not MONGODB_URI:
    raise ValueError("MONGODB_URI is not set in environment variables")

with open("config.yaml") as f:
    config = yaml.safe_load(f)

OUTPUT_DIR = config["output_dir"]


def create_document(team_name: str, url: str, content_markdown: str) -> dict[str, Any]:
    return {
        "team": team_name,
        "source_url": url,
        "content": content_markdown,
        "timestamp": datetime.now(UTC),
        "metadata": {"source": "Wikipedia", "language": "en"},
    }


def ingest_to_mongodb(documents: list[dict[str, Any]]) -> None:
    client: MongoClient = MongoClient(MONGODB_URI)
    db = client["football"]
    collection = db["teams"]

    for doc in documents:
        existing = collection.find_one({"team": doc["team"], "source_url": doc["source_url"]})
        if existing:
            if existing.get("content") != doc["content"]:
                collection.replace_one({"team": doc["team"], "source_url": doc["source_url"]}, doc)
                print(f"Updated document for team: {doc['team']}")
            else:
                print(f"No change for team: {doc['team']}, skipping update.")
        else:
            collection.insert_one(doc)
            print(f"Inserted new document for team: {doc['team']}")


if __name__ == "__main__":
    team_docs: list[dict[str, Any]] = []
    for team in config["teams"]:
        filepath = os.path.join(OUTPUT_DIR, team["filename"])
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        doc = create_document(team["name"], team["url"], content)
        team_docs.append(doc)

    ingest_to_mongodb(team_docs)
