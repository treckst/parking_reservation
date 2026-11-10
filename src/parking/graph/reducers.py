"""Immutable, replay-safe maps preserve every query and retrieval attempt."""

from copy import deepcopy


def merge_records(left, right):
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise ValueError("Record updates must be maps")
    result = deepcopy(left)
    for key, value in right.items():
        if key in result and result[key] != value:
            raise ValueError("Conflicting immutable record")
        result[key] = deepcopy(value)
    return dict(sorted(result.items()))


def merge_queries(left, right):
    from parking.graph.schemas import QueryRecord

    if not isinstance(right, dict):
        raise ValueError("Query updates must be maps")
    normalized = {}
    for key, value in right.items():
        record = QueryRecord.model_validate(value).model_dump()
        if key != record["request_id"]:
            raise ValueError("Query identity mismatch")
        normalized[key] = record
    result = merge_records(left, normalized)
    indices = [record["index"] for record in result.values()]
    if len(set(indices)) != len(indices):
        raise ValueError("Duplicate query index")
    return result


def merge_evidence(left, right):
    if not isinstance(right, dict):
        raise ValueError("Evidence updates must be maps")
    normalized = {}
    for key, attempt in right.items():
        # Local import avoids the state schema's reducer import cycle.
        from parking.graph.schemas import EvidenceAttempt

        record = EvidenceAttempt.model_validate(attempt).model_dump()
        if key != f"{record['query_index']}:{record['attempt']}":
            raise ValueError("Evidence identity mismatch")
        documents = {}
        for document in record["documents"]:
            identity = document["id"]
            if identity in documents and documents[identity] != document:
                raise ValueError("Conflicting document identity")
            documents[identity] = document
        record["documents"] = sorted(
            documents.values(), key=lambda d: (d["source"], d["page"], d["id"])
        )
        normalized[key] = record
    return merge_records(left, normalized)
