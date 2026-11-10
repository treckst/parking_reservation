"""Structural checks accompany model judgements; no customer data tools exist."""

import re

from parking.retrieval import SOURCES


def safe_text(text):
    forbidden = [
        r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}",
        r"(?:[A-Z]:\\|/usr/|/api/|\.sqlite3|ingested_mock_data/)",
        r"(?:system prompt|developer message|LANGSMITH_API_KEY|OPENAI_API_KEY)",
        r"\bsk-[a-zA-Z0-9_-]{10,}",
    ]
    return not any(re.search(pattern, text, re.IGNORECASE) for pattern in forbidden)


def render_answer(answer, assessment, documents):
    by_id = {d["id"]: d for d in documents}
    supported = {identity for claim in assessment.claims for identity in claim.evidence_ids}
    lines = []
    for claim in answer.claims:
        if not claim.evidence_ids or not set(claim.evidence_ids) <= supported:
            raise ValueError("Unsupported citation")
        citations = []
        for identity in dict.fromkeys(claim.evidence_ids):
            document = by_id.get(identity)
            if not document or SOURCES.get(document["source"]) != document["title"]:
                raise ValueError("Unapproved citation")
            citations.append(f"[{document['title']}, p. {document['page'] + 1}]")
        lines.append(f"{claim.text} {' '.join(citations)}")
    if not lines:
        raise ValueError("Missing supported answer")
    if assessment.missing:
        # Only judge-declared missing facts can be described as unavailable.
        lines.extend(assessment.missing)
    text = "\n".join(lines)
    if len(text) > 12000 or not safe_text(text):
        raise ValueError("Unsafe candidate")
    return text
