"""Test image utilities."""
import pytest
from invoice_ingestion.utils.image import image_to_base64, image_to_bytes, compute_quality_score
import base64


class TestBase64RoundTrip:
    def test_round_trip(self):
        original = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        b64 = image_to_base64(original)
        recovered = image_to_bytes(b64)
        assert original == recovered


class TestQualityScore:
    def test_score_range(self):
        # Create a simple test image (1x1 white PNG)
        img_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        score = compute_quality_score(img_bytes)
        assert 0.0 <= score <= 1.0
