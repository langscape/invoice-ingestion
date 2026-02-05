"""Test PDF utilities."""
import pytest
from invoice_ingestion.utils.pdf import detect_file_type


class TestDetectFileType:
    def test_pdf_magic(self):
        assert detect_file_type(b'%PDF-1.4') == "pdf"

    def test_png_magic(self):
        assert detect_file_type(b'\x89PNG\r\n\x1a\n') == "png"

    def test_jpeg_magic(self):
        assert detect_file_type(b'\xff\xd8\xff\xe0') == "jpeg"

    def test_unknown(self):
        assert detect_file_type(b'\x00\x01\x02\x03') == "unknown"
