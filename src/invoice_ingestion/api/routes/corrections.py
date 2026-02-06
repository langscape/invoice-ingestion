"""Corrections API routes - view learned correction rules."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from ...storage.database import get_session
from ...storage.models import Correction
from ...learning.correction_inference import infer_correction_category, CATEGORY_DESCRIPTIONS

router = APIRouter()


@router.get("")
async def list_corrections(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    field_path: str | None = None,
    category: str | None = None,
    session=Depends(get_session),
):
    """List all corrections with optional filters."""
    stmt = select(Correction).order_by(Correction.created_at.desc())

    if field_path:
        stmt = stmt.where(Correction.field_path == field_path)
    if category:
        stmt = stmt.where(Correction.correction_category == category)

    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    corrections = list(result.scalars().all())

    return {
        "items": [
            {
                "correction_id": str(c.correction_id),
                "extraction_id": str(c.extraction_id),
                "field_path": c.field_path,
                "extracted_value": c.extracted_value,
                "corrected_value": c.corrected_value,
                "correction_type": c.correction_type,
                "correction_category": c.correction_category or infer_correction_category(
                    c.field_path, c.extracted_value, c.corrected_value
                ),
                "correction_reason": c.correction_reason,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "context": c.invoice_context_json,
            }
            for c in corrections
        ],
        "offset": offset,
        "limit": limit,
    }


@router.get("/rules")
async def get_correction_rules(session=Depends(get_session)):
    """Get aggregated correction rules (patterns that have been learned).

    Returns corrections grouped by field_path with counts and examples.
    Only includes patterns with 2+ occurrences (active learning threshold).
    """
    # Get all corrections
    stmt = select(Correction).order_by(Correction.created_at.desc())
    result = await session.execute(stmt)
    corrections = list(result.scalars().all())

    # Group by field_path
    groups: dict[str, list] = {}
    for c in corrections:
        if c.field_path not in groups:
            groups[c.field_path] = []
        groups[c.field_path].append(c)

    # Build rules
    rules = []
    for field_path, field_corrections in sorted(groups.items(), key=lambda x: -len(x[1])):
        # Get most common category
        categories = [
            c.correction_category or infer_correction_category(
                c.field_path, c.extracted_value, c.corrected_value
            )
            for c in field_corrections
        ]
        most_common_category = max(set(categories), key=categories.count) if categories else "other"

        # Get unique correction patterns
        patterns: dict[tuple, int] = {}
        for c in field_corrections:
            key = (c.extracted_value, c.corrected_value)
            patterns[key] = patterns.get(key, 0) + 1

        rules.append({
            "field_path": field_path,
            "total_corrections": len(field_corrections),
            "is_active": len(field_corrections) >= 2,  # Learning threshold
            "category": most_common_category,
            "category_description": CATEGORY_DESCRIPTIONS.get(most_common_category, ""),
            "patterns": [
                {
                    "extracted": ext,
                    "corrected": cor,
                    "count": count,
                }
                for (ext, cor), count in sorted(patterns.items(), key=lambda x: -x[1])[:5]
            ],
            "last_correction": field_corrections[0].created_at.isoformat() if field_corrections else None,
        })

    # Summary stats
    total_corrections = len(corrections)
    active_rules = sum(1 for r in rules if r["is_active"])
    pending_rules = sum(1 for r in rules if not r["is_active"])

    return {
        "summary": {
            "total_corrections": total_corrections,
            "active_rules": active_rules,
            "pending_rules": pending_rules,
        },
        "rules": rules,
        "categories": CATEGORY_DESCRIPTIONS,
    }


@router.get("/stats")
async def get_correction_stats(session=Depends(get_session)):
    """Get correction statistics."""
    # Count by category
    stmt = select(
        Correction.correction_category,
        func.count(Correction.correction_id).label("count")
    ).group_by(Correction.correction_category)
    result = await session.execute(stmt)
    by_category = {row[0] or "uncategorized": row[1] for row in result.all()}

    # Count by field_path
    stmt = select(
        Correction.field_path,
        func.count(Correction.correction_id).label("count")
    ).group_by(Correction.field_path).order_by(func.count(Correction.correction_id).desc()).limit(10)
    result = await session.execute(stmt)
    top_fields = [{"field_path": row[0], "count": row[1]} for row in result.all()]

    # Total count
    stmt = select(func.count(Correction.correction_id))
    result = await session.execute(stmt)
    total = result.scalar() or 0

    return {
        "total": total,
        "by_category": by_category,
        "top_fields": top_fields,
    }
