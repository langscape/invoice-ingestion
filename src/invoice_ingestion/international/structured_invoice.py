"""Structured invoice detection (Factur-X, ZUGFeRD, FatturaPA)."""
from __future__ import annotations
import xml.etree.ElementTree as ET

STRUCTURED_FORMATS = {
    "factur-x": ["factur-x.xml", "zugferd-invoice.xml"],
    "zugferd": ["zugferd-invoice.xml", "ZUGFeRD-invoice.xml"],
    "fatturapa": ["FatturaPA", "fatturapa"],
}


def check_structured_invoice(pdf_bytes: bytes) -> dict | None:
    """Check if PDF contains structured invoice data (Factur-X/ZUGFeRD/FatturaPA).

    Returns dict with format info and extracted XML data, or None.
    """
    try:
        from ..utils.pdf import extract_pdf_attachments
        attachments = extract_pdf_attachments(pdf_bytes)
    except Exception:
        return None

    if not attachments:
        return None

    for filename, data in attachments:
        filename_lower = filename.lower()

        # Check for Factur-X / ZUGFeRD
        if "factur-x" in filename_lower or "zugferd" in filename_lower:
            return {
                "format": "factur-x/zugferd",
                "filename": filename,
                "xml_data": _try_parse_xml(data),
                "raw_xml": data.decode("utf-8", errors="replace"),
            }

        # Check for FatturaPA
        if "fattura" in filename_lower:
            return {
                "format": "fatturapa",
                "filename": filename,
                "xml_data": _try_parse_xml(data),
                "raw_xml": data.decode("utf-8", errors="replace"),
            }

        # Check if any XML attachment might be structured invoice data
        if filename_lower.endswith(".xml"):
            xml_content = data.decode("utf-8", errors="replace")
            if any(tag in xml_content for tag in ["CrossIndustryInvoice", "rsm:CrossIndustryInvoice", "FatturaElettronica"]):
                detected_format = "factur-x/zugferd" if "CrossIndustryInvoice" in xml_content else "fatturapa"
                return {
                    "format": detected_format,
                    "filename": filename,
                    "xml_data": _try_parse_xml(data),
                    "raw_xml": xml_content,
                }

    return None


def _try_parse_xml(data: bytes) -> dict | None:
    """Try to parse XML and extract key invoice fields."""
    try:
        root = ET.fromstring(data)
        result = {}

        # Try to extract common fields from CrossIndustryInvoice
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            if tag == "GrandTotalAmount" and elem.text:
                result["total_amount"] = elem.text
            elif tag == "DueDateDateTime" and elem.text:
                result["due_date"] = elem.text
            elif tag == "IssueDateTime" and elem.text:
                result["issue_date"] = elem.text
            elif tag == "ID" and not result.get("invoice_number"):
                result["invoice_number"] = elem.text
            elif tag == "TaxTotalAmount" and elem.text:
                result["tax_amount"] = elem.text

        return result if result else None
    except ET.ParseError:
        return None
