from enum import Enum
from typing import Any

from evaluate import load
from opik.evaluation.metrics import base_metric, score_result
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class MetricNames(Enum):
    BERT_SCORE = "BERTScore"
    BERT_PRECISION = "BERTPrecision"
    BERT_RECALL = "BERTRecall"
    BERT_F1 = "BERTF1"
    COSINE_SIMILARITY = "CosineSimilarity"
    COMBINED_SCORE = "CombinedScore"


class BERTScoreConfig(BaseModel):
    model_type: str = "distilbert-base-uncased"
    language: str = "en"


class CosineSimilarityConfig(BaseModel):
    model_name: str = "all-MiniLM-L6-v2"


class CombinedScoreConfig(BaseModel):
    bert_weight: float = 0.6
    cosine_weight: float = 0.4
    bert_config: BERTScoreConfig = BERTScoreConfig()
    cosine_config: CosineSimilarityConfig = CosineSimilarityConfig()

    def __post_init_post_parse__(self) -> None:
        total = self.bert_weight + self.cosine_weight
        if not 0.99 <= total <= 1.01:
            raise ValueError("bert_weight and cosine_weight must sum to 1.0")


class BERTScore(base_metric.BaseMetric):
    """
    BERTScore metric implementation using the 'evaluate' package.
    """

    def __init__(self, name: str = MetricNames.BERT_SCORE.value, config: BERTScoreConfig | None = None) -> None:
        if config is None:
            config = BERTScoreConfig()
        self.name = name
        self.language = config.language
        self.model_type = config.model_type
        self.bertscore = load("bertscore")

    def score(self, candidate: str, reference: str, **kwargs: Any) -> list[score_result.ScoreResult]:
        if not candidate.strip() or not reference.strip():
            raise ValueError("Input texts cannot be empty or whitespace.")
        results_dict = self.bertscore.compute(
            predictions=[candidate], references=[reference], lang=self.language, model_type=self.model_type
        )
        return [
            score_result.ScoreResult(value=results_dict["recall"][0], name=MetricNames.BERT_RECALL.value),
            score_result.ScoreResult(value=results_dict["precision"][0], name=MetricNames.BERT_PRECISION.value),
            score_result.ScoreResult(value=results_dict["f1"][0], name=MetricNames.BERT_F1.value),
        ]


class CosineSimilarity(base_metric.BaseMetric):
    """
    Cosine similarity metric using sentence-transformers embeddings.
    """

    def __init__(
        self, name: str = MetricNames.COSINE_SIMILARITY.value, config: CosineSimilarityConfig | None = None
    ) -> None:
        if config is None:
            config = CosineSimilarityConfig()
        self.name = name
        self.model = SentenceTransformer(config.model_name)

    def score(self, candidate: str, reference: str, **kwargs: Any) -> list[score_result.ScoreResult]:
        if not candidate.strip() or not reference.strip():
            raise ValueError("Input texts cannot be empty or whitespace.")
        candidate_embedding = self.model.encode([candidate])
        reference_embedding = self.model.encode([reference])
        cos_sim = cosine_similarity(candidate_embedding, reference_embedding)[0][0]
        return [score_result.ScoreResult(value=float(cos_sim), name=MetricNames.COSINE_SIMILARITY.value)]


class CombinedScore(base_metric.BaseMetric):
    """
    Combined metric: weighted sum of BERTScore F1 and Cosine Similarity.
    """

    def __init__(self, name: str = MetricNames.COMBINED_SCORE.value, config: CombinedScoreConfig | None = None) -> None:
        if config is None:
            config = CombinedScoreConfig()

        self.name = name
        self.bert_weight = config.bert_weight
        self.cosine_weight = config.cosine_weight
        self.bert_metric = BERTScore(config=config.bert_config)
        self.cosine_metric = CosineSimilarity(config=config.cosine_config)

    def score(self, candidate: str, reference: str, **kwargs: Any) -> list[score_result.ScoreResult]:
        bert_results = self.bert_metric.score(candidate, reference)
        cosine_results = self.cosine_metric.score(candidate, reference)

        bert_f1 = next(result.value for result in bert_results if result.name == MetricNames.BERT_F1.value)
        cosine_sim = cosine_results[0].value

        combined = (bert_f1 * self.bert_weight) + (cosine_sim * self.cosine_weight)
        return [score_result.ScoreResult(value=float(combined), name=MetricNames.COMBINED_SCORE.value)]
