# from typing import Any

# import comet_ml
# import evaluate
# import pandas as pd
# from loguru import logger
# from pymongo import MongoClient
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity

# from src.configs.settings import Settings

# # Initialize settings
# settings = Settings()

# comet_api_key = settings.comet_api_key
# if not comet_api_key:
#     raise ImportError("Comet API key is not set. Please configure it in your settings.")


# class ExperimentTracker:
#     """Unified experiment tracking interface"""

#     def __init__(self, experiment_name: str = "summary_evaluation"):
#         self.experiment_name = experiment_name
#         self.experiment = None
#         self._initialize_tracker()

#     def _initialize_tracker(self) -> None:
#         if comet_api_key:
#             self.experiment = comet_ml.Experiment(
#                 project_name="football-summary-evaluation",
#                 experiment_name=self.experiment_name,
#             )
#             logger.info(f"Initialized Comet ML experiment: {self.experiment_name}")
#         else:
#             logger.warning("Comet ML not available. Using no tracking.")

#     def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
#         if self.experiment:
#             self.experiment.log_metrics(metrics, step=step)

#     def log_parameters(self, params: dict[str, Any]) -> None:
#         if self.experiment:
#             self.experiment.log_parameters(params)

#     def log_table(self, table_name: str, dataframe: pd.DataFrame) -> None:
#         if self.experiment:
#             self.experiment.log_table(f"{table_name}.csv", dataframe)

#     def finish(self) -> None:
#         if self.experiment:
#             self.experiment.end()


# def run_evaluation_with_tracking(experiment_name: str = None) -> pd.DataFrame:
#     if experiment_name is None:
#         experiment_name = f"summary_eval_{pd.Timestamp.now():%Y%m%d_%H%M%S}"

#     tracker = ExperimentTracker(experiment_name)

#     params = {
#         "bert_model": "distilbert-base-uncased",
#         "sentence_transformer": "all-MiniLM-L6-v2",
#         "summary_types": ["default", "recent", "achievements"],
#         "num_teams": 12,
#         "evaluation_date": pd.Timestamp.now().isoformat(),
#         "combined_score_weights": {"bert_f1": 0.6, "cosine_sim": 0.4}
#     }
#     tracker.log_parameters(params)

#     bertscore = evaluate.load("bertscore")
#     sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

#     summary_types = params["summary_types"]
#     results = []

#     logger.info("🏈 Starting evaluation with experiment tracking...")

#     # Setup MongoDB connection
#     client: MongoClient = MongoClient(settings.mongodb_uri)
#     db = client[settings.mongodb_database]
#     teams_collection = db[settings.mongodb_collection]  # Adjust collection name if different

#     # Iterate over team documents, limit to num_teams
#     for step, team_doc in enumerate(teams_collection.find().limit(params["num_teams"])):
#         team_name = team_doc.get("team", "")
#         article = team_doc.get("content", "").strip()

#         if not article:
#             logger.warning(f"❌ Missing full article content for team {team_name}")
#             continue

#         logger.info(f"📊 Evaluating {team_name.replace('_', ' ').title()}:")
#         team_metrics = {}

#         for summary_type in summary_types:
#             logger.info(f"  Processing {summary_type} summary...")

#             summaries = team_doc.get("summaries", {})
#             summary = summaries.get(summary_type, "").strip()

#             if not summary:
#                 logger.warning(f"  ❌ Missing or empty {summary_type} summary for team {team_name}")
#                 continue

#             try:
#                 scores = bertscore.compute(
#                     predictions=[summary],
#                     references=[article],
#                     lang="en",
#                     model_type=params["bert_model"]
#                 )

#                 f1 = scores["f1"][0]
#                 precision = scores["precision"][0]
#                 recall = scores["recall"][0]

#                 summary_embedding = sentence_model.encode([summary])
#                 article_embedding = sentence_model.encode([article])
#                 cos_sim = cosine_similarity(summary_embedding, article_embedding)[0][0]

#                 result = {
#                     'team': team_name,
#                     'summary_type': summary_type,
#                     'bert_precision': precision,
#                     'bert_recall': recall,
#                     'bert_f1': f1,
#                     'cosine_similarity': cos_sim,
#                     'summary_length': len(summary.split()),
#                     'article_length': len(article.split())
#                 }
#                 results.append(result)

#                 team_metrics.update({
#                     f"{team_name}_{summary_type}_bert_f1": f1,
#                     f"{team_name}_{summary_type}_bert_precision": precision,
#                     f"{team_name}_{summary_type}_bert_recall": recall,
#                     f"{team_name}_{summary_type}_cosine_sim": cos_sim,
#                 })

#                 logger.info(f"  ✅ {summary_type:12} | BERTScore F1: {f1:.4f} | Cosine Sim: {cos_sim:.4f}")

#             except Exception as e:
#                 logger.error(f"  ❌ Error processing {summary_type} summary for {team_name}: {e}")

#         if team_metrics:
#             tracker.log_metrics(team_metrics, step=step)

#     client.close()

#     df = pd.DataFrame(results)

#     if not df.empty:
#         logger.info("📈 Logging summary statistics...")

#         overall_stats = {
#             "overall_bert_f1_mean": df['bert_f1'].mean(),
#             "overall_bert_f1_std": df['bert_f1'].std(),
#             "overall_bert_precision_mean": df['bert_precision'].mean(),
#             "overall_bert_precision_std": df['bert_precision'].std(),
#             "overall_bert_recall_mean": df['bert_recall'].mean(),
#             "overall_bert_recall_std": df['bert_recall'].std(),
#             "overall_cosine_sim_mean": df['cosine_similarity'].mean(),
#             "overall_cosine_sim_std": df['cosine_similarity'].std(),
#             "bert_cosine_correlation": df['bert_f1'].corr(df['cosine_similarity']),
#         }
#         tracker.log_metrics(overall_stats)

#         summary_stats = df.groupby('summary_type')[['bert_precision', 'bert_recall', 'bert_f1',
#                                                     'cosine_similarity']].agg(['mean', 'std'])

#         for summary_type in summary_types:
#             if summary_type in summary_stats.index:
#                 stats = summary_stats.loc[summary_type]
#                 type_metrics = {
#                     f"{summary_type}_bert_f1_mean": stats[('bert_f1', 'mean')],
#                     f"{summary_type}_bert_f1_std": stats[('bert_f1', 'std')],
#                     f"{summary_type}_cosine_sim_mean": stats[('cosine_similarity', 'mean')],
#                     f"{summary_type}_cosine_sim_std": stats[('cosine_similarity', 'std')],
#                 }
#                 tracker.log_metrics(type_metrics)

#                 logger.info(f"{summary_type:12} | BERTScore F1: {stats[('bert_f1', 'mean')]:.4f} \
#                     ± {stats[('bert_f1', 'std')]:.4f} | "
#                             f"Cosine: {stats[('cosine_similarity', 'mean')]:.4f} \
#                                 ± {stats[('cosine_similarity', 'std')]:.4f}")

#         tracker.log_table("evaluation_results", df)

#         df['combined_score'] = (df['bert_f1'] * params["combined_score_weights"]["bert_f1"]) + \
#                                (df['cosine_similarity'] * params["combined_score_weights"]["cosine_sim"])
#         best_combined = df.nlargest(3, 'combined_score')
#         worst_combined = df.nsmallest(3, 'combined_score')

#         best_worst_metrics = {
#             "best_combined_score": best_combined.iloc[0]['combined_score'],
#             "worst_combined_score": worst_combined.iloc[0]['combined_score'],
#             "combined_score_range": best_combined.iloc[0]['combined_score'] - worst_combined.iloc[0]['combined_score']
#         }
#         tracker.log_metrics(best_worst_metrics)

#         logger.info(f"🏆 Best Combined Score: {best_combined.iloc[0]['team']} \
#             ({best_combined.iloc[0]['summary_type']}): {best_combined.iloc[0]['combined_score']:.4f}")
#         logger.info(f"⚠️  Worst Combined Score: {worst_combined.iloc[0]['team']} \
#             ({worst_combined.iloc[0]['summary_type']}): {worst_combined.iloc[0]['combined_score']:.4f}")

#     else:
#         logger.warning("❌ No evaluation results to analyze!")

#     tracker.finish()
#     logger.success(f"✅ Experiment '{experiment_name}' completed and logged!")

#     return df


# if __name__ == "__main__":
#     run_evaluation_with_tracking()
