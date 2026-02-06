"""Store and query corrections for learning loop."""
from __future__ import annotations
from collections import Counter, defaultdict


class CorrectionEntry:
    def __init__(
        self,
        field_path: str,
        extracted_value: str,
        corrected_value: str,
        correction_type: str,
        utility: str | None = None,
        commodity: str | None = None,
        fingerprint: str | None = None,
        reason: str | None = None,
        category: str | None = None,
    ):
        self.field_path = field_path
        self.extracted_value = extracted_value
        self.corrected_value = corrected_value
        self.correction_type = correction_type
        self.utility = utility
        self.commodity = commodity
        self.fingerprint = fingerprint
        self.reason = reason
        self.category = category


class CorrectionStore:
    """Correction store for learning loop, backed by database."""

    def __init__(self):
        self._corrections: list[CorrectionEntry] = []
        self._loaded_from_db = False

    async def load_from_database(self) -> None:
        """Load all corrections from the database."""
        if self._loaded_from_db:
            return

        from ..storage.database import AsyncSessionLocal
        from ..storage.repositories import CorrectionRepo
        from .correction_inference import infer_correction_category

        async with AsyncSessionLocal() as session:
            repo = CorrectionRepo(session)
            db_corrections = await repo.list_all()

            for c in db_corrections:
                context = c.invoice_context_json or {}
                # Use stored category or auto-infer
                category = getattr(c, 'correction_category', None)
                if not category:
                    category = infer_correction_category(
                        c.field_path,
                        c.extracted_value,
                        c.corrected_value,
                    )
                entry = CorrectionEntry(
                    field_path=c.field_path,
                    extracted_value=c.extracted_value or "",
                    corrected_value=c.corrected_value,
                    correction_type=c.correction_type,
                    utility=context.get("utility"),
                    commodity=context.get("commodity"),
                    fingerprint=context.get("fingerprint"),
                    reason=c.correction_reason,
                    category=category,
                )
                self._corrections.append(entry)

        self._loaded_from_db = True

    def store(self, entry: CorrectionEntry) -> None:
        self._corrections.append(entry)

    def query(
        self,
        utility: str | None = None,
        commodity: str | None = None,
        fingerprint: str | None = None,
        min_recurrence: int = 1,
    ) -> list[CorrectionEntry]:
        results = self._corrections
        if utility:
            results = [c for c in results if c.utility == utility]
        if commodity:
            results = [c for c in results if c.commodity == commodity]
        if fingerprint:
            results = [c for c in results if c.fingerprint == fingerprint]

        if min_recurrence > 1:
            # Group by field_path and filter by count
            counts = Counter(c.field_path for c in results)
            qualifying = {fp for fp, count in counts.items() if count >= min_recurrence}
            results = [c for c in results if c.field_path in qualifying]

        return results

    def group_by_pattern(
        self,
        utility: str | None = None,
        commodity: str | None = None,
    ) -> list[dict]:
        corrections = self.query(utility=utility, commodity=commodity)
        groups: dict[str, list[CorrectionEntry]] = defaultdict(list)
        for c in corrections:
            groups[c.field_path].append(c)

        result = []
        for fp, entries in sorted(groups.items(), key=lambda x: -len(x[1])):
            # Determine most common category for this field
            categories = [e.category for e in entries if e.category]
            most_common_category = max(set(categories), key=categories.count) if categories else None

            result.append({
                "field_path": fp,
                "count": len(entries),
                "category": most_common_category,
                "examples": [
                    {
                        "extracted": e.extracted_value,
                        "corrected": e.corrected_value,
                        "reason": e.reason,
                        "category": e.category,
                    }
                    for e in entries[:3]
                ],
            })

        return result
