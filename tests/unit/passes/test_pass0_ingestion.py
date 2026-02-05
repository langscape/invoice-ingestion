"""Test Pass 0 ingestion."""
import pytest
from invoice_ingestion.utils.pdf import detect_file_type


class TestFileTypeDetection:
    def test_pdf(self):
        assert detect_file_type(b'%PDF-1.4 test content') == "pdf"

    def test_png(self):
        assert detect_file_type(b'\x89PNG\r\n\x1a\n rest') == "png"

    def test_jpeg(self):
        assert detect_file_type(b'\xff\xd8\xff rest') == "jpeg"

    def test_tiff_le(self):
        assert detect_file_type(b'II*\x00 rest') == "tiff"

    def test_tiff_be(self):
        assert detect_file_type(b'MM\x00* rest') == "tiff"

    def test_unknown(self):
        assert detect_file_type(b'unknown file content') == "unknown"
