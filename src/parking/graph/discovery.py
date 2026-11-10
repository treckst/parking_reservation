"""Scoped SQL discovery and short, staged customer replies from public results."""

import asyncio
from datetime import date, datetime

from parking.graph.collection import draft_snapshot, missing_details_question, public_details
from parking.graph.schemas import ParkingSearch


FACILITIES = {"CTR": "City Centre", "RIV": "Riverside", "STA": "Station", "AIR": "Airport"}


def search_filters(state, *, spot_id=None):
    search = ParkingSearch.model_validate(state.get("parking_search", {})).model_dump()
    draft = state.get("booking_draft", {})
    if not search["facility"] and draft.get("spot_id"):
        prefix = draft["spot_id"].upper().split("-")[0]
        if prefix in FACILITIES:
            search["facility"] = prefix
    missing = draft_snapshot(draft)["missing_fields"]
    complete = "start" not in missing and "end" not in missing
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
        if not filters["facility"]:
            return {"parking_options": []}
        spots = await asyncio.to_thread(self.store.find_slots, **filters)
        draft = dict(state.get("booking_draft", {}))
        if draft.get("spot_id"):
            selected = await asyncio.to_thread(self.store.find_slots, **{**filters, "spot_id": draft["spot_id"]})
            if selected:
                spots = selected
            else:
                draft["spot_id"] = None
        return {"parking_options": spots,
                "booking_draft": draft,
                "parking_search": {key: filters[key] for key in ("facility", "slot_date", "duration_hours")},
                "reservation_state": public_details(draft_snapshot(draft)["draft"], [filters["facility"]])}

    def record(self, state):
        filters = search_filters(state, spot_id=state.get("booking_draft", {}).get("spot_id"))
        if not filters["facility"]:
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
    spots = state.get("parking_options", [])
    explanation = f"A spot ID is a parking space label, such as {search.facility or 'CTR'}-001. " if state.get("intent", {}).get("explain_spot_id") else ""
    if not search.facility:
        return explanation + "Where would you like to park: City Centre, Riverside, Station or Airport?"
    if not spots:
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
    label = "available" if checked else "spaces"
    quote = f"{FACILITIES[search.facility]}{when} — {label}: " + "; ".join(entries) + "."
    if not checked:
        quote += " Availability needs exact times."

    if not search.slot_date:
        question = "Please provide a date, start time and duration."
    elif "start" in missing:
        duration = f" for your {search.duration_hours:g}-hour stay" if search.duration_hours else ""
        question = f"What start time{duration}? Hours: {display[0]['working_hours']}."
    elif "end" in missing:
        question = "What end time or duration?"
    elif "spot_id" in missing:
        question = "Which space would you like?"
    else:
        question = missing_details_question(draft) if missing else "Would you like to submit this reservation for approval?"
    return explanation + quote + " " + question
