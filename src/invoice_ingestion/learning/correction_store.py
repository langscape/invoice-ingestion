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
    ):
        self.field_path = field_path
        self.extracted_value = extracted_value
        self.corrected_value = corrected_value
        self.correction_type = correction_type
        self.utility = utility
        self.commodity = commodity
        self.fingerprint = fingerprint
        self.reason = reason


class CorrectionStore:
    """In-memory correction store for learning loop (backed by DB via CorrectionRepo)."""

    def __init__(self):
        self._corrections: list[CorrectionEntry] = []

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

        return [
            {
                "field_path": fp,
                "count": len(entries),
                "examples": [
                    {
                        "extracted": e.extracted_value,
                        "corrected": e.corrected_value,
                        "reason": e.reason,
                    }
                    for e in entries[:3]
                ],
            }
            for fp, entries in sorted(groups.items(), key=lambda x: -len(x[1]))
        ]
