import json
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mineral-pdf")

# ---------------------------------------------------------------------------
# Mock NI 43-101 resource data — approximate Pilgangoora (Pilbara Minerals)
# ---------------------------------------------------------------------------
MOCK_RESOURCES = {
    "pilbara": {
        "company": "Pilbara Minerals Ltd",
        "project": "Pilgangoora Lithium-Tantalum Project",
        "location": "Port Hedland, Western Australia",
        "report_date": "2025-12-15",
        "report_standard": "NI 43-101",
        "commodity": "Lithium (Spodumene)",
        "indicated": {
            "tons": 214_000_000,
            "grade_percent": 1.52,
            "contained_metal_lce": 1_520_000,
            "unit": "tonnes",
            "note": "Indicated Mineral Resource as of Dec 2025"
        },
        "inferred": {
            "tons": 106_000_000,
            "grade_percent": 1.31,
            "contained_metal_lce": 680_000,
            "unit": "tonnes",
            "note": "Inferred Mineral Resource as of Dec 2025"
        },
        "total": {
            "tons": 320_000_000,
            "contained_metal_lce": 2_200_000
        },
        "cutoff_grade": "0.5% Li2O",
        "mineralization_type": "Hard-rock spodumene pegmatite",
        "pdf_source": "Pilgangoora NI 43-101 Technical Report (mock)"
    }
}

# Company name aliases for fuzzy matching
COMPANY_ALIASES = {
    "pilbara": "pilbara",
    "pilgangoora": "pilbara",
    "pls": "pilbara",
    "pilbara minerals": "pilbara",
}


def _lookup_company(text: str) -> Optional[str]:
    """Try to match a company name from the input text (URL or name)."""
    text_lower = text.lower()
    for alias, key in COMPANY_ALIASES.items():
        if alias in text_lower:
            return key
    return None


def _try_parse_real_pdf(pdf_url: str) -> Optional[dict]:
    """Attempt to parse a real NI 43-101 PDF (requires PyMuPDF + network)."""
    try:
        import httpx
        import fitz  # PyMuPDF
    except ImportError:
        return None  # Optional dependencies not installed

    try:
        resp = httpx.get(pdf_url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        doc = fitz.open(stream=resp.content, filetype="pdf")

        # Concatenate all text
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        # Regex patterns for NI 43-101 tables
        patterns = {
            "indicated_tons": r"Indicated[\s\S]{0,300}?(\d[\d,]*)\s*(?:tonnes|tons)",
            "inferred_tons": r"Inferred[\s\S]{0,300}?(\d[\d,]*)\s*(?:tonnes|tons)",
            "grade": r"(\d+\.?\d*)\s*%\s*(Li2O|Li|Li₂O)",
            "cutoff": r"(?:cut-off|cutoff|cut off).*?(\d+\.?\d*)\s*%",
        }

        result = {"company": "Unknown (parsed from PDF)", "pdf_source": pdf_url}
        for key, pattern in patterns.items():
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                result[key] = match.group(1) if key == "cutoff" else match.group(0)

        doc.close()
        return result if len(result) > 1 else None

    except Exception:
        return None


@mcp.tool()
def extract_resources(pdf_url: str) -> str:
    """Extract Indicated / Inferred mineral resources from an NI 43-101 technical report PDF.

    For a demo, pass keywords like 'pilbara' or 'pilgangoora' as the URL
    to receive mock data. For real PDF parsing, pass a valid PDF URL (requires
    PyMuPDF and httpx installed in the container).

    Args:
        pdf_url: PDF URL or a company keyword (e.g. 'pilbara_43-101.pdf')
    """
    # 1. Try mock lookup
    company_key = _lookup_company(pdf_url)
    if company_key and company_key in MOCK_RESOURCES:
        return json.dumps(MOCK_RESOURCES[company_key], ensure_ascii=False, indent=2)

    # 2. Try real PDF parsing (if dependencies available)
    if pdf_url.startswith("http"):
        real_result = _try_parse_real_pdf(pdf_url)
        if real_result:
            return json.dumps(real_result, ensure_ascii=False, indent=2)

    # 3. Fallback — return known companies that can be queried
    return json.dumps({
        "error": f"No resource data found for: {pdf_url}",
        "available_mock_companies": list(MOCK_RESOURCES.keys()),
        "hint": "Pass a company name like 'pilbara' as pdf_url to get mock NI 43-101 data."
    }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run(transport="sse", port=8002)
