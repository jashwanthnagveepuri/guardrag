"""Retrieval content filtering guardrail.

Filters retrieved chunks for:
- PII detection and redaction
- Toxic content filtering
- Source attribution enforcement
"""

from __future__ import annotations

import logging
import re
from typing import Any

from guardrag.core.constants import GuardrailAction, GuardrailLayer
from guardrag.core.models import GuardrailDecision

logger = logging.getLogger(__name__)

# PII regex patterns
PII_PATTERNS: dict[str, tuple[re.Pattern, str]] = {
    "ssn": (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
    "credit_card": (re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), "[REDACTED-CC]"),
    "email": (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED-EMAIL]"),
    "phone": (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED-PHONE]"),
    "api_key": (re.compile(r"\b(?:sk|pk)_(?:live|test|prod)_[a-zA-Z0-9]{24,}\b"), "[REDACTED-KEY]"),
}

# Toxic keywords (basic heuristic)
TOXIC_KEYWORDS: list[str] = [
    "kill yourself", "kys", "die in", "hope you die",
    "worthless", "pathetic", "stupid idiot",
    "hate speech", "racial slur", "nazi",
    "terrorist", "bomb making", "child abuse",
    "illegal content", "extremist",
]


class RetrievalGuard:
    """Content filtering for retrieved chunks.

    Detects and redacts PII, filters toxic content,
    and enforces source attribution.
    """

    def __init__(self) -> None:
        self._pii_patterns = PII_PATTERNS
        self._toxic_keywords = [kw.lower() for kw in TOXIC_KEYWORDS]

    def filter_chunks(
        self,
        chunks: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], GuardrailDecision]:
        """Filter and redact retrieved chunks.

        Args:
            chunks: List of chunk dicts with 'document' text.

        Returns:
            Tuple of (filtered_chunks, guardrail_decision).
        """
        filtered: list[dict[str, Any]] = []
        total_pii_redactions = 0
        total_toxic_filtered = 0

        for chunk in chunks:
            text = chunk.get("document", "")
            if not text:
                continue

            # Check for toxic content
            if self._is_toxic(text):
                total_toxic_filtered += 1
                logger.debug("Filtered toxic chunk from doc %s", chunk.get("metadata", {}).get("document_id", "?"))
                continue

            # Redact PII
            redacted_text, pii_count = self._redact_pii(text)
            total_pii_redactions += pii_count

            if pii_count > 0:
                chunk["document"] = redacted_text
                chunk["metadata"] = chunk.get("metadata", {})
                chunk["metadata"]["pii_redacted"] = True
                chunk["metadata"]["pii_redaction_count"] = pii_count

            filtered.append(chunk)

        # Build guardrail decision
        if total_toxic_filtered > 0 or total_pii_redactions > 0:
            decision = GuardrailDecision(
                triggered=total_toxic_filtered > 0,
                layer=GuardrailLayer.RETRIEVAL,
                action=GuardrailAction.WARN if total_toxic_filtered == 0 else GuardrailAction.BLOCK,
                reason="PII_DETECTED" if total_pii_redactions > 0 else "TOXIC_CONTENT",
                confidence=0.9 if total_toxic_filtered > 0 else 0.7,
                detail=f"PII redactions: {total_pii_redactions}, Toxic filtered: {total_toxic_filtered}",
                pii_redacted=total_pii_redactions,
                toxic_filtered=total_toxic_filtered,
            )
        else:
            decision = GuardrailDecision(
                triggered=False,
                layer=GuardrailLayer.RETRIEVAL,
                action=GuardrailAction.PASS,
            )

        return filtered, decision

    def _is_toxic(self, text: str) -> bool:
        """Check if text contains toxic keywords.

        Args:
            text: The text to check.

        Returns:
            True if toxic content is detected.
        """
        text_lower = text.lower()
        for keyword in self._toxic_keywords:
            if keyword in text_lower:
                return True
        return False

    def _redact_pii(self, text: str) -> tuple[str, int]:
        """Redact PII patterns from text.

        Args:
            text: The text to redact.

        Returns:
            Tuple of (redacted_text, redaction_count).
        """
        redacted = text
        count = 0
        for pii_type, (pattern, replacement) in self._pii_patterns.items():
            matches = list(pattern.finditer(redacted))
            # Replace in reverse to preserve positions
            for match in reversed(matches):
                redacted = redacted[:match.start()] + replacement + redacted[match.end():]
                count += 1
        return redacted, count

    @staticmethod
    def enforce_source_attribution(answer: str, sources: list[dict[str, Any]]) -> bool:
        """Check that the answer cites available sources.

        Args:
            answer: The LLM-generated answer.
            sources: List of source chunks that were provided.

        Returns:
            True if answer contains citations.
        """
        if not sources:
            return True  # No sources to cite

        # Check for [Source N] or [1], [2] style citations
        has_citation = bool(re.search(r"\[\s*(?:Source\s+)?\d+\s*\]", answer))
        return has_citation
