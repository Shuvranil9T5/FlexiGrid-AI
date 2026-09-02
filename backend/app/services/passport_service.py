from app.database import list_saved_passports, save_passport_record


def build_candidate_passports(patterns: list[dict]) -> list[dict]:
    saved = {item["pattern_id"]: item for item in list_saved_passports()}
    candidates = []
    for pattern in patterns:
        passport = {
            **pattern,
            "label": "User-defined candidate load",
            "earliest_start_slot": max(0, pattern["typical_start_slot"] - 8),
            "latest_finish_slot": min(96, pattern["typical_start_slot"] + 16),
            "priority": 2,
            "interruptible": False,
            "minimum_runtime_slots": 1,
            "criticality": "medium",
            "notes": "",
            "verified": False,
            "status": "candidate",
        }
        if pattern["pattern_id"] in saved:
            passport.update(saved[pattern["pattern_id"]])
            passport.update({key: pattern[key] for key in ("occurrences", "confidence", "duration_observations")})
        candidates.append(passport)
    # DBSCAN cluster labels are not chronological, while pattern IDs are the
    # workflow's user-facing sequence. Keep persisted IDs stable and present
    # the cards in their natural PAT-01, PAT-02, ... order.
    return sorted(candidates, key=lambda item: int(item["pattern_id"].split("-")[-1]))


def store_passport(payload: dict) -> dict:
    payload = dict(payload)
    payload["verified"] = payload["status"] == "confirmed"
    save_passport_record(payload)
    return payload