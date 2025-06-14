from datetime import datetime
from typing import ClassVar, TypedDict

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Team(BaseModel):
    name: str
    url: str
    filename: str
    metadata: dict[str, str] | None = None


class CrawledDoc(BaseModel):
    team: str
    url: str
    filename: str
    content: str
    timestamp: datetime
    metadata: dict[str, str]


class YamlConfig(BaseModel):
    output_dir: str
    eval_dir: str
    eval_dataset: str
    teams: list[Team]


class SummaryConfig(TypedDict):
    prompt: str
    max_tokens: int


def load_yaml_config(path: str) -> YamlConfig:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return YamlConfig.model_validate(data)  # type: ignore[no-any-return]


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    config_yaml_path: str = Field(default="src/configs/config.yaml", description="Path to the YAML configuration file.")

    # yaml_config: YamlConfig | None = None

    yaml_config: YamlConfig = Field(
        default_factory=lambda: YamlConfig(output_dir="", eval_dir="", eval_dataset="", teams=[])
    )

    # MongoDB connection settings
    mongodb_uri: str = Field(
        default="mongodb://root:root@localhost:27017/", description="MongoDB URI for connecting to the database."
    )
    mongodb_database: str = Field(default="football", description="Name of the MongoDB database to use.")

    mongodb_collection: str = Field(default="teams", description="Name of the MongoDB collection to use.")

    mongodb_collection_index: str = Field(
        default="summary_vectors", description="Name of the MongoDB collection for summary vectors."
    )

    mongodb_collection_index_name: str = Field(
        default="summary_vectors_index", description="Name of the MongoDB vector search index."
    )

    mongodb_query_fields: list[str] = Field(
        default_factory=lambda: ["team", "source_url"], description="Fields to use as the query filter for MongoDB upserts."
    )

    openai_api_key: str = Field(default="", description="OpenAI API key for accessing the OpenAI services.")

    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI model for generating text embeddings."
    )
    openai_llm_model: str = Field(default="gpt-4o-mini", description="OpenAI model for generating text completions.")

    openai_llm_judge_model: str = Field(
        default="gpt-4o", description="OpenAI model for judging the quality of text completions."
    )

    comet_api_key: str = Field(default="", description="Comet API key for tracking experiments.")

    def load_yaml(self) -> None:
        """Loads the YAML configuration file and updates yaml_config."""
        self.yaml_config = load_yaml_config(self.config_yaml_path)
