"""Format fingerprinting for known invoice templates."""
from __future__ import annotations
from pydantic import BaseModel, Field


class FormatFingerprint(BaseModel):
    """A known invoice format template."""
    utility: str
    commodity: str
    detection_signals: dict  # header_pattern, layout_hash, etc.
    known_issues: str = ""
    custom_prompt_additions: str = ""
    accuracy_history: list[bool] = Field(default_factory=list)
    invoices_processed: int = 0

    @property
    def accuracy(self) -> float:
        if not self.accuracy_history:
            return 0.0
        return sum(self.accuracy_history) / len(self.accuracy_history)


class FingerprintLibrary:
    """Library of known invoice format fingerprints."""

    def __init__(self):
        self._fingerprints: list[FormatFingerprint] = []

    def match(self, utility: str, commodity: str, signals: dict | None = None) -> FormatFingerprint | None:
        """Find a matching fingerprint."""
        for fp in self._fingerprints:
            if fp.utility.lower() == utility.lower() and fp.commodity.lower() == commodity.lower():
                return fp
        return None

    def create(self, utility: str, commodity: str, signals: dict) -> FormatFingerprint:
        """Create a new fingerprint."""
        fp = FormatFingerprint(utility=utility, commodity=commodity, detection_signals=signals)
        self._fingerprints.append(fp)
        return fp

    def update_accuracy(self, fingerprint: FormatFingerprint, was_accurate: bool) -> None:
        """Update accuracy history for a fingerprint."""
        fingerprint.accuracy_history.append(was_accurate)
        fingerprint.invoices_processed += 1

    def should_create_new(self, utility: str, similar_count: int) -> bool:
        """Determine if we should create a new fingerprint (need 3+ similar invoices)."""
        return similar_count >= 3 and self.match(utility, "") is None
