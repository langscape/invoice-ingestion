"""Async CRUD repositories for all storage models."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from invoice_ingestion.storage.models import (
    Correction,
    DriftEvent,
    Extraction,
    FormatFingerprint,
    LLMCall,
)


# ── Extraction ───────────────────────────────────────────────────────────────


class ExtractionRepo:
    """CRUD operations for the ``extractions`` table."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, extraction: Extraction) -> Extraction:
        self._session.add(extraction)
        await self._session.flush()
        await self._session.refresh(extraction)
        return extraction

    async def get_by_id(self, extraction_id: UUID) -> Extraction | None:
        stmt = select(Extraction).where(Extraction.extraction_id == extraction_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hash(self, file_hash: str) -> Extraction | None:
        stmt = (
            select(Extraction)
            .where(Extraction.file_hash == file_hash)
            .order_by(Extraction.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_extractions(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        commodity: str | None = None,
        confidence_tier: str | None = None,
        status: str | None = None,
    ) -> list[Extraction]:
        stmt = select(Extraction)
        if commodity is not None:
            stmt = stmt.where(Extraction.commodity_type == commodity)
        if confidence_tier is not None:
            stmt = stmt.where(Extraction.confidence_tier == confidence_tier)
        if status is not None:
            stmt = stmt.where(Extraction.status == status)
        stmt = stmt.order_by(Extraction.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_review(self, *, offset: int = 0, limit: int = 50) -> list[Extraction]:
        stmt = (
            select(Extraction)
            .where(Extraction.status == "pending_review")
            .order_by(Extraction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_tier(self) -> dict[str, int]:
        stmt = (
            select(Extraction.confidence_tier, func.count())
            .group_by(Extraction.confidence_tier)
        )
        result = await self._session.execute(stmt)
        return {tier: count for tier, count in result.all()}

    async def update_status(self, extraction_id: UUID, status: str) -> None:
        stmt = (
            update(Extraction)
            .where(Extraction.extraction_id == extraction_id)
            .values(status=status)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def update_result(
        self,
        extraction_id: UUID,
        result_json: dict,
        confidence_score: float,
        confidence_tier: str,
    ) -> None:
        stmt = (
            update(Extraction)
            .where(Extraction.extraction_id == extraction_id)
            .values(
                result_json=result_json,
                confidence_score=confidence_score,
                confidence_tier=confidence_tier,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()


# ── Correction ───────────────────────────────────────────────────────────────


class CorrectionRepo:
    """CRUD operations for the ``corrections`` table."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, correction: Correction) -> Correction:
        self._session.add(correction)
        await self._session.flush()
        await self._session.refresh(correction)
        return correction

    async def get_by_extraction(self, extraction_id: UUID) -> list[Correction]:
        stmt = (
            select(Correction)
            .where(Correction.extraction_id == extraction_id)
            .order_by(Correction.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, limit: int = 1000) -> list[Correction]:
        """Return all corrections (up to limit), ordered by most recent first."""
        stmt = select(Correction).order_by(Correction.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def query_by_context(
        self,
        utility: str | None = None,
        commodity: str | None = None,
        fingerprint: str | None = None,
        min_recurrence: int = 1,
    ) -> list[Correction]:
        """Query corrections filtered by invoice context stored in ``invoice_context_json``.

        The *min_recurrence* parameter filters to corrections whose field_path
        appears at least *min_recurrence* times across matching rows.
        """
        stmt = select(Correction)

        if utility is not None:
            stmt = stmt.where(
                Correction.invoice_context_json["utility"].as_string() == utility
            )
        if commodity is not None:
            stmt = stmt.where(
                Correction.invoice_context_json["commodity"].as_string() == commodity
            )
        if fingerprint is not None:
            stmt = stmt.where(
                Correction.invoice_context_json["fingerprint"].as_string() == fingerprint
            )

        if min_recurrence > 1:
            # Sub-query: field_paths that appear at least *min_recurrence* times
            sub = stmt.with_only_columns(Correction.field_path).group_by(Correction.field_path).having(
                func.count() >= min_recurrence
            ).subquery()
            stmt = stmt.where(Correction.field_path.in_(select(sub.c.field_path)))

        stmt = stmt.order_by(Correction.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def group_by_field_path(
        self,
        utility: str | None = None,
        commodity: str | None = None,
    ) -> list[dict]:
        """Return ``[{field_path, count, examples}]`` grouped by ``field_path``.

        *examples* contains up to 5 representative ``(extracted_value, corrected_value)``
        pairs for each field path.
        """
        base_stmt = select(Correction)
        if utility is not None:
            base_stmt = base_stmt.where(
                Correction.invoice_context_json["utility"].as_string() == utility
            )
        if commodity is not None:
            base_stmt = base_stmt.where(
                Correction.invoice_context_json["commodity"].as_string() == commodity
            )

        # Count per field_path
        count_stmt = (
            base_stmt
            .with_only_columns(Correction.field_path, func.count().label("cnt"))
            .group_by(Correction.field_path)
            .order_by(func.count().desc())
        )
        count_result = await self._session.execute(count_stmt)
        rows = count_result.all()

        groups: list[dict] = []
        for field_path, count in rows:
            # Fetch up to 5 examples for this field_path
            examples_stmt = (
                base_stmt
                .with_only_columns(Correction.extracted_value, Correction.corrected_value)
                .where(Correction.field_path == field_path)
                .order_by(Correction.created_at.desc())
                .limit(5)
            )
            ex_result = await self._session.execute(examples_stmt)
            examples = [
                {"extracted_value": ev, "corrected_value": cv}
                for ev, cv in ex_result.all()
            ]
            groups.append({"field_path": field_path, "count": count, "examples": examples})

        return groups


# ── Fingerprint ──────────────────────────────────────────────────────────────


class FingerprintRepo:
    """CRUD operations for the ``format_fingerprints`` table."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_match(self, utility: str, commodity: str) -> FormatFingerprint | None:
        stmt = select(FormatFingerprint).where(
            FormatFingerprint.utility == utility,
            FormatFingerprint.commodity == commodity,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, fingerprint: FormatFingerprint) -> FormatFingerprint:
        self._session.add(fingerprint)
        await self._session.flush()
        await self._session.refresh(fingerprint)
        return fingerprint

    async def update_accuracy(self, fingerprint_id: UUID, was_accurate: bool) -> None:
        """Append an accuracy entry to the fingerprint's ``accuracy_history``.

        The history is a JSON dict keyed by ISO-8601 date with boolean values.
        We read-modify-write inside a flush to keep atomicity within the session.
        """
        stmt = select(FormatFingerprint).where(FormatFingerprint.fingerprint_id == fingerprint_id)
        result = await self._session.execute(stmt)
        fp = result.scalar_one_or_none()
        if fp is None:
            return

        from datetime import datetime, timezone

        history = dict(fp.accuracy_history) if fp.accuracy_history else {}
        history[datetime.now(timezone.utc).isoformat()] = was_accurate
        fp.accuracy_history = history
        await self._session.flush()

    async def increment_processed(self, fingerprint_id: UUID) -> None:
        stmt = (
            update(FormatFingerprint)
            .where(FormatFingerprint.fingerprint_id == fingerprint_id)
            .values(invoices_processed=FormatFingerprint.invoices_processed + 1)
        )
        await self._session.execute(stmt)
        await self._session.flush()


# ── Drift ────────────────────────────────────────────────────────────────────


class DriftRepo:
    """CRUD operations for the ``drift_events`` table."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, event: DriftEvent) -> DriftEvent:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def get_by_extraction(self, extraction_id: UUID) -> list[DriftEvent]:
        stmt = (
            select(DriftEvent)
            .where(DriftEvent.extraction_id == extraction_id)
            .order_by(DriftEvent.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# ── LLM Calls ────────────────────────────────────────────────────────────────


class LLMCallRepo:
    """CRUD operations for the ``llm_calls`` table."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, call: LLMCall) -> LLMCall:
        self._session.add(call)
        await self._session.flush()
        await self._session.refresh(call)
        return call

    async def get_by_extraction(self, extraction_id: UUID) -> list[LLMCall]:
        stmt = (
            select(LLMCall)
            .where(LLMCall.extraction_id == extraction_id)
            .order_by(LLMCall.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_calls(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        extraction_id: UUID | None = None,
        stage: str | None = None,
        model: str | None = None,
    ) -> list[LLMCall]:
        stmt = select(LLMCall).order_by(LLMCall.created_at.desc())

        if extraction_id:
            stmt = stmt.where(LLMCall.extraction_id == extraction_id)
        if stage:
            stmt = stmt.where(LLMCall.stage == stage)
        if model:
            stmt = stmt.where(LLMCall.model == model)

        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_stats(self) -> dict:
        """Get aggregate stats about LLM calls."""
        # Total calls
        total_stmt = select(func.count(LLMCall.call_id))
        total = (await self._session.execute(total_stmt)).scalar() or 0

        # By stage
        stage_stmt = select(
            LLMCall.stage,
            func.count(LLMCall.call_id),
            func.avg(LLMCall.duration_ms),
            func.sum(LLMCall.total_tokens),
        ).group_by(LLMCall.stage)
        stage_result = await self._session.execute(stage_stmt)
        by_stage = {
            row[0]: {
                "count": row[1],
                "avg_duration_ms": round(row[2]) if row[2] else None,
                "total_tokens": row[3] or 0,
            }
            for row in stage_result.all()
        }

        # By model
        model_stmt = select(
            LLMCall.model,
            func.count(LLMCall.call_id),
            func.sum(LLMCall.total_tokens),
        ).group_by(LLMCall.model)
        model_result = await self._session.execute(model_stmt)
        by_model = {
            row[0]: {"count": row[1], "total_tokens": row[2] or 0}
            for row in model_result.all()
        }

        return {
            "total_calls": total,
            "by_stage": by_stage,
            "by_model": by_model,
        }
