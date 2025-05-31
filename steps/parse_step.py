import os
from datetime import UTC, datetime

import yaml
from zenml import step


@step
def parse_step(config_path: str = "config.yaml") -> list:
    with open(config_path) as f:
        config = yaml.safe_load(f)

    output_dir = config["output_dir"]
    docs = []

    for team in config["teams"]:
        path = os.path.join(output_dir, team["filename"])
        with open(path, encoding="utf-8") as f:
            content = f.read()

        doc = {
            "team": team["name"],
            "source_url": team["url"],
            "content": content,
            "timestamp": datetime.now(UTC),
            "metadata": {"source": "Wikipedia", "language": "en"},
        }
        docs.append(doc)

    return docs
