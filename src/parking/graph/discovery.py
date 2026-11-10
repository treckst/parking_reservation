"""Scoped SQL discovery and short, staged customer replies from public results."""

import asyncio
from datetime import date, datetime

from parking.graph.collection import draft_snapshot, missing_details_question, public_details
from parking.graph.schemas import ParkingSearch
from parking.graph.fields import SEARCH_FIELDS
from parking.graph.selection import awaiting_space_selection


FACILITIES = {"CTR": "City Centre", "RIV": "Riverside", "STA": "Station", "AIR": "Airport"}


def search_filters(state, *, spot_id=None):
    search = ParkingSearch.model_validate(state.get("parking_search", {})).model_dump()
    draft = state.get("booking_draft", {})
    if not search["facility"] and draft.get("spot_id"):
        prefix = draft["spot_id"].upper().split("-")[0]
        if prefix in FACILITIES:
            search["facility"] = prefix
    missing = draft_snapshot(draft)["missing_fields"]
    complete = "start" not in missing and "end" not in missing and not any(
        field in state.get("field_errors", {}) for field in ("slot_date", "start", "end", "duration_hours"))
    if complete:
        start, end = (datetime.fromisoformat(draft[key]) for key in ("start", "end"))
        search.update(slot_date=start.date().isoformat(), duration_hours=(end - start).total_seconds() / 3600)
    return {**search, "start": draft.get("start") if complete else None,
            "end": draft.get("end") if complete else None, "spot_id": spot_id}


class ParkingDiscovery:
    def __init__(self, store):
        self.store = store

    async def lookup(self, state):
        filters = search_filters(state)
        if not filters["facility"] or any(field in state.get("field_errors", {})
                for field in ("facility", "slot_date", "spot_type")):
            return {"parking_options": []}
        spots = await asyncio.to_thread(self.store.find_slots, **filters)
        draft = dict(state.get("booking_draft", {}))
        errors = dict(state.get("field_errors", {}))
        if (state.get("space_choice") == "accept_type" and awaiting_space_selection(state)
                and not state.get("intent", {}).get("lookup_only") and filters["spot_type"]
                and filters["start"] and filters["end"] and spots and not draft.get("spot_id")):
            # A type acceptance authorizes any matching space, not a guessed
            # label. Use freshly scoped/overlap-checked SQL results and state
            # the concrete choice in the reply. This does not create a hold.
            draft["spot_id"] = spots[0]["spot_id"]
            errors.pop("spot_id", None)
        if draft.get("spot_id"):
            selected = await asyncio.to_thread(self.store.find_slots, **{**filters, "spot_id": draft["spot_id"]})
            if selected:
                spots = selected
            else:
                draft["spot_id"] = None
        return {"parking_options": spots,
                "booking_draft": draft,
                "field_errors": errors,
                "parking_search": {key: filters[key] for key in SEARCH_FIELDS},
                "reservation_state": public_details(draft_snapshot(draft)["draft"], [filters["facility"]], filters)}

    def record(self, state):
        filters = search_filters(state, spot_id=state.get("booking_draft", {}).get("spot_id"))
        if not filters["facility"] or any(field in state.get("field_errors", {})
                for field in ("facility", "slot_date", "spot_type")):
            return {}
        key = f"{state['query_index']}:1"
        if key in state.get("evidence", {}):
            return {}
        return {"evidence": {key: {"query_index": state["query_index"], "attempt": 1,
            "question": state["message"], "documents": [],
            "sql_results": [{"filters": filters, "spots": state.get("parking_options", [])}]}}}


def reservation_question(state):
    """Prioritize location, timing and a real space choice before personal details."""
    search = ParkingSearch.model_validate(state.get("parking_search", {}))
    draft = draft_snapshot(state.get("booking_draft", {}))["draft"]
    missing = draft_snapshot(draft)["missing_fields"]
    identity = [field for field in ("name", "surname", "car_number") if field in missing]

    def identity_follow_up():
        if not draft.get("spot_id") or not identity:
            return ""
        return " I’ll also need your " + ", ".join({
            "name": "first name", "surname": "surname", "car_number": "vehicle plate",
        }[field] for field in identity) + "."

    spots = state.get("parking_options", [])
    explanation = f"A spot ID is a parking space label, such as {search.facility or 'CTR'}-001. " if state.get("intent", {}).get("explain_spot_id") else ""
    if not search.facility:
        return explanation + "Where would you like to park: City Centre, Riverside, Station or Airport?"
    if not spots:
        if state.get("field_errors"):
            return explanation + next(iter(state["field_errors"].values()))
        when = " for that interval" if draft.get("start") and draft.get("end") else f" on {search.slot_date}" if search.slot_date else ""
        return explanation + f"No matching spaces at {FACILITIES[search.facility]}{when}. Try another date, time or location."

    # Group equal rates/types so three choices need only one price statement.
    chosen = [spot for spot in spots if spot["spot_id"] == draft.get("spot_id")]
    display = chosen or spots
    groups = {}
    for spot in display:
        key = (spot["type"], spot["hourly_price"], spot["total_price"])
        groups.setdefault(key, []).append(spot["spot_id"])
    entries = []
    for (kind, rate, total), identities in groups.items():
        price = f"{rate:g} PLN/hour"
        if total is not None:
            price += f"; {total:g} PLN for {search.duration_hours:g} hours"
        entries.append(f"{', '.join(identities)} ({kind}) — {price}")
    checked = all(spot["availability_checked"] for spot in display)
    when = ", " + date.fromisoformat(search.slot_date).strftime("%d %b %Y") if search.slot_date else ""
    if draft.get("start") or draft.get("end"):
        when += " " + (draft["start"][11:16] if draft.get("start") else "?") + "–" + (draft["end"][11:16] if draft.get("end") else "?")
    label = "selected" if chosen else "available" if checked else "spaces"
    quote = f"{FACILITIES[search.facility]}{when} — {label}: " + "; ".join(entries) + "."
    if not checked:
        quote += " Availability needs exact times."

    errors = state.get("field_errors", {})
    if errors:
        question = next(iter(errors.values()))
        if next(iter(errors)) == "start":
            question += f" Hours: {display[0]['working_hours']}."
    elif not search.slot_date:
        question = "Please provide a date, start time and duration." + identity_follow_up()
    elif "start" in missing:
        duration = f" for your {search.duration_hours:g}-hour stay" if search.duration_hours else ""
        question = f"What start time{duration}? Hours: {display[0]['working_hours']}." + identity_follow_up()
    elif "end" in missing:
        question = "What end time or duration?" + identity_follow_up()
    elif "spot_id" in missing:
        if state.get("space_choice") == "defer":
            question = "Your type preference is saved. Tell me when you're ready to choose a space."
        elif state.get("space_choice") == "clarify":
            kind = search.spot_type or "matching"
            question = f"Shall I choose any available {kind} space for you, or do you want a particular label?"
        else:
            question = "Which space would you like?"
    else:
        if state.get("space_choice") == "defer":
            question = "Your details are saved. Tell me when you're ready to continue."
        elif state.get("space_choice") == "clarify" and chosen:
            question = f"Do you want to keep {chosen[0]['spot_id']}, or choose a different space?"
        else:
            question = missing_details_question(draft) if missing else "Would you like to submit this reservation for approval?"
    return explanation + quote + " " + question
