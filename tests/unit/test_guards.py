import pytest

from parking.graph.guards import render_answer, safe_text
from parking.graph.schemas import Answer, EvidenceAssessment


@pytest.mark.parametrize("value", ["OPENAI_API_KEY", "sk-privatecanary123456", "a@private.example", "/usr/private", "data.sqlite3"])
def test_sensitive_text_rejected(value):
    assert not safe_text(value)


def test_forged_citation_rejected():
    answer = Answer(claims=[{"text": "Open always", "evidence_ids": ["forged"]}], unavailable=[])
    assessment = EvidenceAssessment(status="sufficient", claims=[{"claim": "Hours", "facility": "shared", "evidence_ids": ["real"]}], missing=[])
    with pytest.raises(ValueError, match="Unsupported citation"):
        render_answer(answer, assessment, [])
