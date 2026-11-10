"""Reviewed corpus facts are checked locally; provider calls remain mocked."""

import json
from pathlib import Path

from pypdf import PdfReader


def test_reviewed_policy_expectations_match_supplied_pages():
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "tests/cases/policy_cases.json").read_text(encoding="utf-8"))
    for case in cases:
        if "source" not in case:
            continue
        pdf = root / "ingested_mock_data/pdfs" / f"{case['source']}.pdf"
        page = PdfReader(pdf).pages[case["page"] - 1].extract_text()
        for expected in case["expected_terms"]:
            assert expected.lower() in page.lower(), case["id"]
