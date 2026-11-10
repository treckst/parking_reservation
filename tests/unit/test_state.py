"""Immutable identity and evidence retention, including reducer order laws."""

from copy import deepcopy

import pytest

from parking.graph.reducers import merge_evidence, merge_queries


def attempt(index=1, number=1):
    return {f"{index}:{number}": {"query_index": index, "attempt": number,
        "question": "Hours?", "documents": [], "sql_results": []}}


def test_retains_questions_and_both_attempts():
    first, retry, later = attempt(), attempt(number=2), attempt(index=2)
    merged = merge_evidence(merge_evidence(first, retry), later)
    assert set(merged) == {"1:1", "1:2", "2:1"}
    assert merged == merge_evidence(first, merge_evidence(retry, later))
    assert merged == merge_evidence(later, merge_evidence(retry, first))
    assert merge_evidence(merged, first) == merged
    assert merge_evidence(merged, {}) == merged


def test_immutable_conflict_and_invalid_update():
    original = attempt()
    conflicting = deepcopy(original)
    conflicting["1:1"]["question"] = "Different"
    with pytest.raises(ValueError):
        merge_evidence(original, conflicting)
    with pytest.raises(ValueError):
        merge_evidence(original, None)
    assert original["1:1"]["question"] == "Hours?"


def test_duplicate_query_index_and_identity_rejected():
    first = {"a": {"index": 1, "request_id": "a", "original_message": "one", "retrieval_question": "one"}}
    later = {"b": {"index": 1, "request_id": "b", "original_message": "two", "retrieval_question": "two"}}
    with pytest.raises(ValueError):
        merge_queries(first, later)
    with pytest.raises(ValueError):
        merge_queries({}, {"wrong": first["a"]})
