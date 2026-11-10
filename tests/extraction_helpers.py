"""Explicit structured patches for scripted provider fixtures."""


def updates(values):
    return [{"field": key, "operation": "set" if value is not None else "clear",
             "value": str(value) if value is not None else None} for key, value in values.items()]


def temporal_patch(data):
    fields = data.get("provided_fields", [])
    patch = updates({key: data.get(key) for key in fields})
    if data.get("clarification"):
        patch = [item for item in patch if item["value"] is not None]
        field = "slot_date" if "11/12" in data["clarification"] else "start"
        patch.append({"field": field, "operation": "clarify", "value": None})
    return {"updates": patch}
