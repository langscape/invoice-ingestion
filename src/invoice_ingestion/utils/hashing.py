"""Hashing utilities for deduplication and integrity checks."""

from __future__ import annotations

import hashlib


def compute_file_hash(file_bytes: bytes) -> str:
    """Return the SHA-256 hex digest of raw file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


def compute_string_hash(text: str) -> str:
    """Return the SHA-256 hex digest of a UTF-8 encoded string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_bytes_hash(data: bytes) -> str:
    """Return the SHA-256 hex digest of arbitrary bytes."""
    return hashlib.sha256(data).hexdigest()
