"""Enumeration constants for GuardRAG."""

from __future__ import annotations

from enum import Enum


class DocumentStatus(str, Enum):
    """Processing status of an uploaded document."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(str, Enum):
    """Role of a message in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class GuardrailAction(str, Enum):
    """Action taken by a guardrail layer."""

    PASS = "pass"
    BLOCK = "block"
    WARN = "warn"


class GuardrailLayer(str, Enum):
    """Layer at which a guardrail operates."""

    INPUT = "input"
    RETRIEVAL = "retrieval"
    OUTPUT = "output"


class ChunkingStrategy(str, Enum):
    """Document chunking strategy."""

    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
