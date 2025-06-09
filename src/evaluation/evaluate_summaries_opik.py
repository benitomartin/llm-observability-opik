from collections.abc import Callable
from typing import Any, cast

import pandas as pd
from loguru import logger
from opik import Opik, track
from opik.evaluation import evaluate
from pymongo import MongoClient

from src.configs.settings import Settings
from src.evaluation.metrics import (
    BERTScore,
    BERTScoreConfig,
    CombinedScore,
    CombinedScoreConfig,
    CosineSimilarity,
    CosineSimilarityConfig,
    MetricNames,
)


def prepare_dataset() -> tuple[Any, int]:
    """
    Connects to MongoDB, extracts football team articles and summaries, and constructs
    an evaluation dataset compatible with Opik.

    Returns:
        tuple:
            - dataset: Opik dataset object containing summary-reference pairs.
            - num_teams: Total number of team documents retrieved from the database.
    """
    client: MongoClient = MongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]
    teams_collection = db[settings.mongodb_collection]

    num_teams = teams_collection.count_documents({})
    dataset_items = []
    summary_types = ["default", "recent", "achievements"]

    for team_doc in teams_collection.find().limit(num_teams):
        team_name = team_doc.get("team", "")
        article = team_doc.get("content", "").strip()
        summaries = team_doc.get("summaries", {})

        if not article:
            logger.warning(f"❌ Missing full article content for team {team_name}")
            continue

        for summary_type in summary_types:
            summary = summaries.get(summary_type, "").strip()
            if summary:
                dataset_items.append(
                    {
                        "team": team_name,
                        "summary_type": summary_type,
                        "reference": article,
                        "summary": summary,
                        "article_length": len(article.split()),
                        "summary_length": len(summary.split()),
                    }
                )

    client.close()

    opik_client = Opik()
    dataset_name = f"football_summaries_{pd.Timestamp.now():%Y%m%d_%H%M%S}"

    dataset = opik_client.create_dataset(name=dataset_name, description="Football team summaries evaluation dataset")
    dataset.insert(dataset_items)
    return dataset, num_teams


@track
def summary_evaluation_task(data: dict[str, Any]) -> dict[str, Any]:
    """
    Extracts and prepares data for evaluation, to be consumed by Opik.

    Args:
        data (dict): Input dictionary containing team, reference article, and summary info.

    Returns:
        dict: A structured dictionary with reference, candidate, metadata, and lengths.
    """
    return {
        "reference": data["reference"],
        "candidate": data["summary"],
        "team": data["team"],
        "summary_type": data["summary_type"],
        "article_length": data["article_length"],
        "summary_length": data["summary_length"],
    }


def run_evaluation_with_opik(experiment_name: str | None = None) -> pd.DataFrame:
    """
    Runs an Opik evaluation of football team summaries using BERTScore, Cosine Similarity,
    and a Combined metric. Logs summary statistics and returns results as a DataFrame.

    Args:
        experiment_name (str | None): Optional name for the experiment. If not provided,
        a timestamped name will be generated.

    Returns:
        pd.DataFrame: Evaluation results, including team, summary type, and scores.
    """
    if experiment_name is None:
        experiment_name = f"summary_eval_{pd.Timestamp.now():%Y%m%d_%H%M%S}"

    logger.info("🏈 Starting evaluation with Opik...")

    dataset, num_teams = prepare_dataset()
    dataset_items = list(dataset.get_items())

    if not dataset_items:
        logger.error("❌ No data found for evaluation!")
        return pd.DataFrame()

    logger.info(f"📊 Evaluating {len(dataset_items)} summary-article pairs...")

    # Metric configs
    bert_config = BERTScoreConfig(model_type="distilbert-base-uncased")
    cosine_config = CosineSimilarityConfig(model_name="all-MiniLM-L6-v2")
    combined_config = CombinedScoreConfig(bert_config=bert_config, cosine_config=cosine_config)

    # Initialize metrics
    bert_metric = BERTScore(config=bert_config)
    cosine_metric = CosineSimilarity(config=cosine_config)
    combined_metric = CombinedScore(config=combined_config)

    evaluation_result = evaluate(
        experiment_name=experiment_name,
        dataset=dataset,
        # task=summary_evaluation_task,
        task=cast(Callable[[dict[str, Any]], dict[str, Any]], summary_evaluation_task),
        scoring_metrics=[bert_metric, cosine_metric, combined_metric],
        experiment_config={
            "bert_model": bert_config.model_type,
            "sentence_transformer": cosine_config.model_name,
            "summary_types": ["default", "recent", "achievements"],
            "num_teams": num_teams,
            "evaluation_date": pd.Timestamp.now().isoformat(),
            "combined_score_weights": {"bert_f1": combined_metric.bert_weight, "cosine_sim": combined_metric.cosine_weight},
        },
        task_threads=1,
    )

    results = []
    try:
        for i, test_result in enumerate(evaluation_result.test_results):
            dataset_item = dataset_items[i] if i < len(dataset_items) else {}
            team = dataset_item.get("team", f"team_{i}")
            summary_type = dataset_item.get("summary_type", f"type_{i}")

            score_dict = {}
            if test_result.score_results:
                for score_result in test_result.score_results:
                    score_dict[score_result.name] = float(score_result.value)

            results.append(
                {
                    "team": team,
                    "summary_type": summary_type,
                    "bert_precision": score_dict.get(MetricNames.BERT_PRECISION.value),
                    "bert_recall": score_dict.get(MetricNames.BERT_RECALL.value),
                    "bert_f1": score_dict.get(MetricNames.BERT_F1.value),
                    "cosine_similarity": score_dict.get(MetricNames.COSINE_SIMILARITY.value),
                    "combined_score": score_dict.get(MetricNames.COMBINED_SCORE.value),
                    "summary_length": dataset_item.get("summary_length", 0),
                    "article_length": dataset_item.get("article_length", 0),
                }
            )

    except Exception as e:
        logger.error(f"Error extracting results: {e}")
        for item in dataset_items:
            results.append(
                {
                    "team": item.get("team", "unknown"),
                    "summary_type": item.get("summary_type", "unknown"),
                    "bert_precision": None,
                    "bert_recall": None,
                    "bert_f1": None,
                    "cosine_similarity": None,
                    "combined_score": None,
                    "summary_length": item.get("summary_length", 0),
                    "article_length": item.get("article_length", 0),
                }
            )

    df = pd.DataFrame(results)
    numeric_cols = [
        "bert_precision",
        "bert_recall",
        "bert_f1",
        "cosine_similarity",
        "combined_score",
        "summary_length",
        "article_length",
    ]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    if not df.empty and not df["combined_score"].isna().all():
        logger.info("📈 Evaluation Results Summary:")
        summary_stats = df.groupby("summary_type")[["bert_f1", "cosine_similarity", "combined_score"]].mean()

        for summary_type, stats in summary_stats.iterrows():
            logger.info(
                f"{summary_type:12} | BERT F1: {stats['bert_f1']:.4f} | "
                f"Cosine: {stats['cosine_similarity']:.4f} | Combined: {stats['combined_score']:.4f}"
            )

        valid_scores = df.dropna(subset=["combined_score"])
        if not valid_scores.empty and valid_scores["combined_score"].nunique() > 1:
            best = valid_scores.nlargest(1, "combined_score").iloc[0]
            worst = valid_scores.nsmallest(1, "combined_score").iloc[0]
            logger.info(f"🏆 Best: {best['team']} ({best['summary_type']}): {best['combined_score']:.4f}")
            logger.info(f"⚠️  Worst: {worst['team']} ({worst['summary_type']}): {worst['combined_score']:.4f}")

    logger.success(f"✅ Experiment '{experiment_name}' completed!")
    return df


if __name__ == "__main__":
    settings = Settings()
    results_df = run_evaluation_with_opik()
    logger.info(f"✅ Evaluation complete. Result preview:\n{results_df.head()}")
