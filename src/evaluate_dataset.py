import json
from typing import Any

from openai import OpenAI
from opik import Opik, track
from opik.evaluation import evaluate
from opik.evaluation.metrics import AnswerRelevance, ContextPrecision, Hallucination
from opik.integrations.openai import track_openai

from src.configs.settings import Settings

# Initialize settings
settings = Settings()

# Load QA pairs from JSON file
with open("real_madrid_qa_dataset.json", encoding="utf-8") as f:
    qa_data = json.load(f)

# Step 1: Track OpenAI API
openai_client = track_openai(OpenAI(api_key=settings.openai_api_key))
MODEL = "gpt-4o-mini"  # Use the same model you used to generate answers


# Step 2: Define your application logic
@track
def your_llm_application(input: str) -> str:
    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": input}],
    )
    content = response.choices[0].message.content
    return content.strip() if content is not None else ""


# Step 3: Define evaluation task for Opik


def evaluation_task(x: dict[str, Any]) -> dict:
    return {"output": your_llm_application(x["input"])}


# Step 4: Initialize Opik & create dataset
client = Opik()
dataset = client.get_or_create_dataset(name="Real Madrid QA Dataset")

# Step 5: Insert dataset items (Opik deduplicates automatically)
dataset.insert(qa_data)

# Step 6: Define metrics (Equals + optional hallucination)
# equals_metric = Equals()
hallucination_metric = Hallucination()
answer_relevance_metric = AnswerRelevance(require_context=False)
context_precision_metric = ContextPrecision()

# Step 7: Run the evaluation
evaluation = evaluate(
    dataset=dataset,
    task=evaluation_task,
    scoring_metrics=[hallucination_metric, answer_relevance_metric, context_precision_metric],
    experiment_config={
        "model": MODEL,
        "description": "Evaluation of Real Madrid QA LLM application using summaries from MongoDB context",
    },
)

print("✅ Evaluation complete.")
