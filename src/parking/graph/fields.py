"""Apply explicit field operations independently, then validate their relationships."""

from collections import Counter
from datetime import date, datetime, timedelta
import re
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from parking.graph.schemas import ParkingSearch, ReservationDraft


SEARCH_FIELDS = ("facility", "spot_type", "slot_date", "duration_hours")
QUESTIONS = {
    "facility": "Which parking location would you like?",
    "spot_type": "Which space type: standard, electric, accessible or van?",
    "slot_date": "Please confirm the reservation date, including the month and year.",
    "start": "What exact start time would you like?",
    "end": "What exact end time would you like?",
    "duration_hours": "How many hours would you like to park?",
    "spot_id": "Please choose one of the listed spaces.",
    "name": "Please provide your first name.",
    "surname": "Please provide your surname.",
    "car_number": "Please provide your vehicle plate.",
}
INTERVAL_QUESTION = "Please confirm an end time after the start on the same date."
DURATION_QUESTION = "The duration and start/end times differ. Which should I change?"


def normalize_field(field, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A set operation needs a value")
    value = value.strip()
    if field == "facility":
        value = value.upper()
    elif field == "spot_type":
        value = value.lower()
    elif field == "duration_hours":
        value = float(value)
    elif field == "spot_id":
        value = value.upper()
        if not re.fullmatch(r"(?:CTR|RIV|STA|AIR)-\d{3}", value):
            raise ValueError("Invalid space label")
    elif field in ("name", "surname", "car_number") and len(value) > 120:
        raise ValueError("Field too long")
    schema = ParkingSearch if field in SEARCH_FIELDS else ReservationDraft
    return getattr(schema.model_validate({field: value}), field)


def on_date(timestamp, day):
    local = datetime.combine(date.fromisoformat(day), datetime.fromisoformat(timestamp).time())
    local = local.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
    if local.utcoffset() != local.replace(fold=1).utcoffset():
        raise ValueError("Ambiguous local time")
    return normalize_field("start", local.isoformat())


def apply_field_updates(state, updates):
    draft = dict(state.get("booking_draft", {}))
    search = ParkingSearch.model_validate(state.get("parking_search", {})).model_dump()
    errors = dict(state.get("field_errors", {}))
    counts = Counter(update.field for update in updates)
    touched = set(counts)
    valid = set()
    facilities = state.get("intent", {}).get("facilities", [])
    if "facility" not in touched and len(facilities) == 1:
        search["facility"] = facilities[0]
        errors.pop("facility", None)
    for update in updates:
        field = update.field
        target = search if field in SEARCH_FIELDS else draft
        try:
            if counts[field] != 1 or update.operation == "clarify":
                raise ValueError("Clarification required")
            if update.operation == "clear":
                if update.value is not None:
                    raise ValueError("Clear needs null")
                target[field] = None
            else:
                target[field] = normalize_field(field, update.value)
            errors.pop(field, None)
            valid.add(field)
        except (ValueError, TypeError, ValidationError):
            target[field] = None
            errors[field] = QUESTIONS[field]
    if "slot_date" in touched and not search["slot_date"]:
        for field in ("start", "end"):
            if field not in valid:
                draft[field] = None
        if any(draft.get(field) for field in ("start", "end")):
            errors["slot_date"] = QUESTIONS["slot_date"]
    elif "slot_date" not in touched:
        for field in ("start", "end"):
            if field in valid and draft.get(field):
                search["slot_date"] = draft[field][:10]
                errors.pop("slot_date", None)
                break
    if search["slot_date"]:
        for field in ("start", "end"):
            if draft.get(field) and draft[field][:10] != search["slot_date"]:
                try:
                    if field in touched:
                        raise ValueError("Timestamp conflicts with supplied date")
                    draft[field] = on_date(draft[field], search["slot_date"])
                    errors.pop(field, None)
                except ValueError:
                    draft[field] = None
                    errors[field] = QUESTIONS[field]
    if search["duration_hours"] and "duration_hours" not in errors and valid & {"start", "end", "duration_hours"}:
        if draft.get("start") and "end" not in touched and "end" not in errors and (
                not draft.get("end") or "duration_hours" in valid):
            draft["end"] = (datetime.fromisoformat(draft["start"]) + timedelta(hours=search["duration_hours"])).astimezone(ZoneInfo("Europe/Warsaw")).isoformat()
            errors.pop("end", None)
        elif draft.get("end") and "start" not in touched and "start" not in errors and not draft.get("start"):
            draft["start"] = (datetime.fromisoformat(draft["end"]) - timedelta(hours=search["duration_hours"])).astimezone(ZoneInfo("Europe/Warsaw")).isoformat()
            errors.pop("start", None)
    if draft.get("start") and draft.get("end"):
        start, end = (datetime.fromisoformat(draft[key]) for key in ("start", "end"))
        hours = (end - start).total_seconds() / 3600
        if start.date() != end.date() or not 0 < hours <= 24:
            errors["end"] = INTERVAL_QUESTION
        else:
            if errors.get("end") == INTERVAL_QUESTION:
                errors.pop("end")
            if "duration_hours" in valid and search["duration_hours"] is not None and abs(search["duration_hours"] - hours) > 0.001:
                errors["duration_hours"] = DURATION_QUESTION
            elif errors.get("duration_hours") == DURATION_QUESTION and search["duration_hours"] is not None and abs(search["duration_hours"] - hours) > 0.001:
                pass
            else:
                if errors.get("duration_hours") == DURATION_QUESTION:
                    errors.pop("duration_hours")
                search["duration_hours"] = hours
    if draft.get("spot_id") and search["facility"] and not draft["spot_id"].startswith(search["facility"] + "-"):
        draft["spot_id"] = None
        if "spot_id" in touched:
            errors["spot_id"] = QUESTIONS["spot_id"]
    return {"booking_draft": draft, "parking_search": search, "field_errors": errors,
            "date_clarification": next((errors[key] for key in ("slot_date", "start", "end", "duration_hours") if key in errors), None)}
