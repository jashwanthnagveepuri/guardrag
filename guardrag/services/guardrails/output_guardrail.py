"""Output verification guardrail for GuardRAG.

Three-stage verification:
1. NLIFactChecker - per-sentence entailment against sources
2. AnswerRelevanceChecker - question-answer relevance
3. ConfidenceScorer - composite confidence score
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sentence_transformers import CrossEncoder

from guardrag.core.config import get_settings
from guardrag.core.constants import GuardrailAction, GuardrailLayer
from guardrag.core.models import GuardrailDecision

logger = logging.getLogger(__name__)

NLI_MODEL = "cross-encoder/nli-deberta-v3-base"
RELEVANCE_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass
class NLIFactCheckResult:
    """Result from NLI fact-checking."""

    entailment_count: int = 0
    contradiction_count: int = 0
    neutral_count: int = 0
    contradiction_rate: float = 0.0
    entailment_rate: float = 0.0
    per_sentence_results: list[dict[str, Any]] = field(default_factory=list)


class NLIFactChecker:
    """Fact-checks LLM output against source chunks using NLI.

    Uses cross-encoder/nli-deberta-v3-base for entailment classification.
    """

    def __init__(self) -> None:
        self._model: CrossEncoder | None = None

    def _get_model(self) -> CrossEncoder:
        """Lazy-load the NLI model."""
        if self._model is None:
            logger.info("Loading NLI model: %s", NLI_MODEL)
            self._model = CrossEncoder(NLI_MODEL)
        return self._model

    def check(
        self,
        answer: str,
        source_chunks: list[dict[str, Any]],
    ) -> NLIFactCheckResult:
        """Check each sentence of the answer against source chunks.

        Args:
            answer: The LLM-generated answer.
            source_chunks: Retrieved source chunks with 'document' text.

        Returns:
            NLIFactCheckResult with entailment statistics.
        """
        if not answer or not source_chunks:
            return NLIFactCheckResult()

        sentences = self._split_sentences(answer)
        if not sentences:
            return NLIFactCheckResult()

        model = self._get_model()
        source_texts = [chunk.get("document", "") for chunk in source_chunks]

        result = NLIFactCheckResult()

        for sentence in sentences:
            if len(sentence) < 5:  # Skip very short fragments
                continue

            pairs = [[sentence, src] for src in source_texts if src.strip()]
            if not pairs:
                continue

            predictions = model.predict(pairs)
            # predictions are arrays of logits for [contradiction, entailment, neutral]

            # Map predictions to labels
            labels = [self._get_label(p) for p in predictions]

            best = max(set(labels), key=labels.count) if labels else "neutral"

            if best == "entailment":
                result.entailment_count += 1
            elif best == "contradiction":
                result.contradiction_count += 1
            else:
                result.neutral_count += 1

            result.per_sentence_results.append({
                "sentence": sentence[:200],
                "best_label": best,
                "label_distribution": {
                    "entailment": labels.count("entailment"),
                    "contradiction": labels.count("contradiction"),
                    "neutral": labels.count("neutral"),
                },
            })

        total = result.entailment_count + result.contradiction_count + result.neutral_count
        if total > 0:
            result.entailment_rate = result.entailment_count / total
            result.contradiction_rate = result.contradiction_count / total

        return result

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences."""
        pattern = r"(?<=[.!?])\s+"
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    @staticmethod
    def _get_label(prediction) -> str:
        """Map prediction logits to label string.

        The model outputs logits for [contradiction, entailment, neutral].
        """
        if isinstance(prediction, (list, np.ndarray)):
            idx = int(np.argmax(prediction))
            labels = ["contradiction", "entailment", "neutral"]
            return labels[idx] if idx < len(labels) else "neutral"
        # Handle single string predictions
        pred_str = str(prediction).lower()
        if "entailment" in pred_str:
            return "entailment"
        if "contradiction" in pred_str:
            return "contradiction"
        return "neutral"


class AnswerRelevanceChecker:
    """Check answer relevance to the original question."""

    def __init__(self) -> None:
        self._model: CrossEncoder | None = None

    def _get_model(self) -> CrossEncoder:
        """Lazy-load the relevance model."""
        if self._model is None:
            logger.info("Loading relevance model: %s", RELEVANCE_MODEL)
            self._model = CrossEncoder(RELEVANCE_MODEL)
        return self._model

    def check(self, question: str, answer: str) -> float:
        """Score answer relevance to the question.

        Args:
            question: The original user question.
            answer: The LLM-generated answer.

        Returns:
            Relevance score between 0 and 1.
        """
        if not question or not answer:
            return 0.0

        model = self._get_model()
        score = model.predict([[question, answer]])[0]

        # Normalize to 0-1
        if score > 1.0 or score < 0.0:
            score = 1.0 / (1.0 + np.exp(-score))

        return float(score)


class ConfidenceScorer:
    """Composite confidence scorer.

    Formula:
        confidence = retrieval_confidence * 0.3 + faithfulness * 0.4 + relevance * 0.3
    """

    @staticmethod
    def compute(
        retrieval_scores: list[float],
        fact_check_result: NLIFactCheckResult,
        relevance_score: float,
    ) -> float:
        """Compute composite confidence score.

        Args:
            retrieval_scores: List of retrieval/re-rank scores.
            fact_check_result: NLI fact-checking result.
            relevance_score: Question-answer relevance score.

        Returns:
            Confidence score between 0 and 1.
        """
        # Retrieval confidence: mean of top scores
        if retrieval_scores:
            retrieval_conf = float(np.mean(sorted(retrieval_scores, reverse=True)[:3]))
        else:
            retrieval_conf = 0.0

        # Faithfulness: entailment rate
        faithfulness = fact_check_result.entailment_rate

        # Composite
        confidence = (
            retrieval_conf * 0.30 +
            faithfulness * 0.40 +
            relevance_score * 0.30
        )

        # Penalize contradictions
        if fact_check_result.contradiction_rate > 0.3:
            confidence *= 0.5

        return round(max(0.0, min(1.0, confidence)), 4)


class OutputGuardrail:
    """Output verification guardrail.

    Runs three checks:
    1. NLI fact-checking against source chunks
    2. Answer relevance to the question
    3. Composite confidence scoring
    """

    def __init__(self) -> None:
        self._nli = NLIFactChecker()
        self._relevance = AnswerRelevanceChecker()
        self._scorer = ConfidenceScorer()

    async def check(
        self,
        question: str,
        answer: str,
        source_chunks: list[dict[str, Any]],
    ) -> tuple[GuardrailDecision, float, float]:
        """Run all output guardrail checks.

        Args:
            question: The original user question.
            answer: The LLM-generated answer.
            source_chunks: Retrieved source chunks.

        Returns:
            Tuple of (GuardrailDecision, confidence_score, hallucination_risk).
        """
        settings = get_settings()

        # Check 1: NLI fact-checking
        fact_result = self._nli.check(answer, source_chunks)

        # Check 2: Answer relevance
        relevance_score = self._relevance.check(question, answer)

        # Check 3: Confidence scoring
        retrieval_scores = [
            chunk.get("rerank_score") or chunk.get("similarity_score", 0.0)
            for chunk in source_chunks
        ]
        confidence = self._scorer.compute(retrieval_scores, fact_result, relevance_score)

        # Hallucination risk: based on contradiction rate and low entailment
        hallucination_risk = fact_result.contradiction_rate * 0.6
        if fact_result.entailment_rate < 0.3:
            hallucination_risk += 0.3
        hallucination_risk = round(min(1.0, hallucination_risk), 4)

        threshold = settings.guardrail_output_threshold

        if confidence < 0.3 or hallucination_risk > 0.5:
            return GuardrailDecision(
                triggered=True,
                layer=GuardrailLayer.OUTPUT,
                action=GuardrailAction.BLOCK,
                reason="LOW_CONFIDENCE" if confidence < 0.3 else "HALLUCINATION_RISK",
                confidence=round(confidence, 4),
                detail=f"confidence={confidence:.3f}, hallucination_risk={hallucination_risk:.3f}, "
                       f"entailment={fact_result.entailment_rate:.3f}, "
                       f"contradiction={fact_result.contradiction_rate:.3f}",
            ), confidence, hallucination_risk

        if confidence < threshold:
            return GuardrailDecision(
                triggered=True,
                layer=GuardrailLayer.OUTPUT,
                action=GuardrailAction.WARN,
                reason="LOW_CONFIDENCE",
                confidence=round(confidence, 4),
                detail=f"Low confidence score: {confidence:.3f} (threshold: {threshold:.3f})",
            ), confidence, hallucination_risk

        return GuardrailDecision(
            triggered=False,
            layer=GuardrailLayer.OUTPUT,
            action=GuardrailAction.PASS,
            confidence=round(confidence, 4),
        ), confidence, hallucination_risk
