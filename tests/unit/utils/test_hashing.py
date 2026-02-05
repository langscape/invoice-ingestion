"""Test hashing utilities."""
from invoice_ingestion.utils.hashing import compute_file_hash, compute_string_hash, compute_bytes_hash


class TestHashing:
    def test_deterministic(self):
        data = b"hello world"
        assert compute_file_hash(data) == compute_file_hash(data)

    def test_same_content_same_hash(self):
        assert compute_string_hash("test") == compute_string_hash("test")

    def test_different_content_different_hash(self):
        assert compute_string_hash("a") != compute_string_hash("b")

    def test_file_hash_is_sha256(self):
        h = compute_file_hash(b"test")
        assert len(h) == 64  # SHA-256 hex length

    def test_bytes_hash(self):
        h = compute_bytes_hash(b"data")
        assert len(h) == 64
