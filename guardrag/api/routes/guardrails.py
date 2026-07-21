"""Guardrail API routes."""

from __future__ import annotations

import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from guardrag.api.dependencies import get_db, get_input_guardrail
from guardrag.core.constants import GuardrailAction, GuardrailLayer
from guardrag.core.models import (
    ErrorResponse,
    GuardrailLayerStats,
    GuardrailScanRequest,
    GuardrailScanResponse,
    GuardrailStats,
    HeuristicDetail,
    LLMClassifierDetail,
)
from guardrag.infra.database import GuardrailLog
from guardrag.services.guardrails.input_guardrail import InputGuardrail

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


@router.post(
    "/scan",
    response_model=GuardrailScanResponse,
    responses={422: {"model": ErrorResponse}},
)
async def scan_text(
    request: Request,
    scan_request: GuardrailScanRequest,
    db: AsyncSession = Depends(get_db),
    input_guardrail: InputGuardrail = Depends(get_input_guardrail),
) -> GuardrailScanResponse:
    """Scan text for prompt injection and jailbreak attempts.

    Runs both heuristic and LLM classifier (if paranoid mode or heuristic triggers).
    """
    start_time = time.monotonic()

    result = await input_guardrail.scan(
        scan_request.text,
        paranoid_mode=scan_request.paranoid_mode,
    )

    latency_ms = int((time.monotonic() - start_time) * 1000)

    # Log the scan
    log = GuardrailLog(
        layer=result.layer.value,
        action=result.action.value,
        reason=result.reason,
        confidence=result.confidence,
        input_text=scan_request.text[:1000],
        query_hash=__import__("hashlib").sha256(scan_request.text.encode()).hexdigest(),
        details={"heuristic": "scanned", "llm": "scanned"},
    )
    db.add(log)
    await db.commit()

    return GuardrailScanResponse(
        scanned=True,
        action=result.action,
        composite_score=result.confidence or 0.0,
        threshold=0.75,
        heuristic=HeuristicDetail(
            score=result.confidence or 0.0,
            matched_patterns=[result.reason or ""],
        ),
        llm_classifier=LLMClassifierDetail(
            is_malicious=result.action == GuardrailAction.BLOCK,
            confidence=result.confidence or 0.0,
            category=result.reason,
            reasoning=result.detail,
        ),
        latency_ms=latency_ms,
    )


@router.get(
    "/stats",
    response_model=GuardrailStats,
)
async def get_guardrail_stats(
    request: Request,
    period: str = Query("24h", description="Aggregation period: 1h, 24h, 7d, 30d"),
    db: AsyncSession = Depends(get_db),
) -> GuardrailStats:
    """Get guardrail statistics for the specified period.

    Aggregates scan counts, block rates, and latency metrics from the guardrail_logs table.
    """
    # Parse period
    period_map = {"1h": 1, "24h": 1, "7d": 7, "30d": 30}
    days = period_map.get(period, 1)

    since = datetime.utcnow() - timedelta(days=days)

    # Build layer stats
    layers = ["input", "retrieval", "output"]
    layer_stats: dict[str, GuardrailLayerStats] = {}

    for layer in layers:
        # Total scanned
        total_result = await db.execute(
            select(func.count())
            .where(GuardrailLog.layer == layer)
            .where(GuardrailLog.created_at >= since)
        )
        total = total_result.scalar() or 0

        # Passed
        passed_result = await db.execute(
            select(func.count())
            .where(GuardrailLog.layer == layer)
            .where(GuardrailLog.action == GuardrailAction.PASS.value)
            .where(GuardrailLog.created_at >= since)
        )
        passed = passed_result.scalar() or 0

        # Blocked
        blocked_result = await db.execute(
            select(func.count())
            .where(GuardrailLog.layer == layer)
            .where(GuardrailLog.action == GuardrailAction.BLOCK.value)
            .where(GuardrailLog.created_at >= since)
        )
        blocked = blocked_result.scalar() or 0

        # Warned
        warned_result = await db.execute(
            select(func.count())
            .where(GuardrailLog.layer == layer)
            .where(GuardrailLog.action == GuardrailAction.WARN.value)
            .where(GuardrailLog.created_at >= since)
        )
        warned = warned_result.scalar() or 0

        # Avg latency
        avg_latency_result = await db.execute(
            select(func.avg(GuardrailLog.details["latency_ms"].astext.cast(__import__("sqlalchemy").Float)))
            .where(GuardrailLog.layer == layer)
            .where(GuardrailLog.created_at >= since)
        )
        avg_latency = avg_latency_result.scalar() or 0.0

        # Top reasons
        reasons_result = await db.execute(
            select(GuardrailLog.reason, func.count())
            .where(GuardrailLog.layer == layer)
            .where(GuardrailLog.created_at >= since)
            .where(GuardrailLog.reason.isnot(None))
            .group_by(GuardrailLog.reason)
            .order_by(func.count().desc())
            .limit(5)
        )
        top_reasons = [
            {"reason": r[0], "count": r[1]} for r in reasons_result.all()
        ]

        block_rate = (blocked / total * 100) if total > 0 else 0.0

        layer_stats[layer] = GuardrailLayerStats(
            total_scanned=total,
            passed=passed,
            blocked=blocked,
            warned=warned,
            block_rate_percent=round(block_rate, 2),
            avg_latency_ms=round(float(avg_latency), 2),
            top_reasons=top_reasons,
        )

    total_all = sum(s.total_scanned for s in layer_stats.values())
    blocked_all = sum(s.blocked for s in layer_stats.values())
    overall_rate = (blocked_all / total_all * 100) if total_all > 0 else 0.0

    return GuardrailStats(
        period=period,
        input_layer=layer_stats["input"],
        retrieval_layer=layer_stats["retrieval"],
        output_layer=layer_stats["output"],
        overall_block_rate_percent=round(overall_rate, 2),
    )
