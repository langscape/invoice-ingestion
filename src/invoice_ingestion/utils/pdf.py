"""PDF processing utilities using PyMuPDF and pdfplumber."""

from __future__ import annotations

import io

import fitz  # PyMuPDF
import pdfplumber


def render_pdf_to_images(file_bytes: bytes, dpi: int = 300) -> list[bytes]:
    """Render each PDF page to PNG image bytes at the given DPI."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    images: list[bytes] = []
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def extract_text_pymupdf(file_bytes: bytes) -> list[str]:
    """Extract text from each page using PyMuPDF.

    Returns a list of text strings, one per page.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    texts = [page.get_text() for page in doc]
    doc.close()
    return texts


def extract_text_pdfplumber(file_bytes: bytes) -> list[str]:
    """Extract text with layout preservation using pdfplumber.

    Returns a list of text strings, one per page.
    """
    texts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
    return texts


def extract_pdf_attachments(file_bytes: bytes) -> list[tuple[str, bytes]]:
    """Extract embedded files (e.g., Factur-X XML).

    Returns a list of ``(filename, data)`` tuples.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    attachments: list[tuple[str, bytes]] = []
    if doc.embfile_count() > 0:
        for i in range(doc.embfile_count()):
            info = doc.embfile_info(i)
            data = doc.embfile_get(i)
            attachments.append((info["name"], data))
    doc.close()
    return attachments


def detect_file_type(file_bytes: bytes) -> str:
    """Detect file type from magic bytes.

    Returns one of ``"pdf"``, ``"png"``, ``"jpeg"``, ``"tiff"``, or ``"unknown"``.
    """
    if file_bytes[:4] == b"%PDF":
        return "pdf"
    if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if file_bytes[:2] == b"\xff\xd8":
        return "jpeg"
    if file_bytes[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    return "unknown"


def get_page_count(file_bytes: bytes) -> int:
    """Return the number of pages in a PDF."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    count = len(doc)
    doc.close()
    return count
