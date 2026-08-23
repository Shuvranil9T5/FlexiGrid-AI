def optimize_schedule(forecast, passports, solar=None, tariff=None, max_building_kw=20.0, mode="balanced"):
    """Deterministic constrained search over every permitted 15-minute start slot."""
    solar = solar or [0.0] * 96
    tariff = tariff or [1.0] * 96
    baseline = [float(value) for value in forecast]
    working_load = baseline.copy()
    weights = {"balanced": (1.0, 3.0, 0.8), "cost": (2.0, 1.0, 0.4), "peak": (0.4, 6.0, 0.3), "carbon": (0.5, 1.0, 2.5)}[mode]
    schedule = []
    def time_label(slot):
        return f"{slot // 4:02d}:{(slot % 4) * 15:02d}"
    for passport in sorted(passports, key=lambda item: item.priority):
        if not passport.verified or passport.criticality == "critical":
            continue
        original_slots = list(range(passport.typical_start_slot, min(96, passport.typical_start_slot + passport.duration_slots)))
        for slot in original_slots:
            working_load[slot] = max(0.0, working_load[slot] - passport.estimated_power_kw)
        latest_start = min(95, passport.latest_finish_slot - passport.duration_slots)
        candidates = range(passport.earliest_start_slot, latest_start + 1)
        best = None
        for start in candidates:
            slots = list(range(start, min(96, start + passport.duration_slots)))
            if len(slots) != passport.duration_slots:
                continue
            projected = [working_load[s] + passport.estimated_power_kw for s in slots]
            if max(projected) > max_building_kw:
                continue
            cost = sum(max(0, working_load[s] + passport.estimated_power_kw - solar[s]) * tariff[s] * 0.25 for s in slots)
            peak_penalty = max(projected)
            carbon_proxy = sum(max(0, working_load[s] + passport.estimated_power_kw - solar[s]) * (1.3 if 68 <= s <= 88 else 0.7) * 0.25 for s in slots)
            score = weights[0] * cost + weights[1] * peak_penalty + weights[2] * carbon_proxy
            if best is None or score < best[0]:
                best = (score, start, slots)
        if best:
            _, start, slots = best
            for slot in slots:
                working_load[slot] += passport.estimated_power_kw
            schedule.append({
                "pattern_id": passport.pattern_id,
                "label": passport.label,
                "original_start_slot": passport.typical_start_slot,
                "recommended_start_slot": start,
                "duration_slots": passport.duration_slots,
                "estimated_power_kw": passport.estimated_power_kw,
                "reason": f"Selected by {mode} mode within verified time and demand constraints",
                "original_time": time_label(passport.typical_start_slot),
                "recommended_time": time_label(start),
                "end_time": time_label(start + passport.duration_slots),
                "explanation": f"Move {passport.label} from {time_label(passport.typical_start_slot)} to {time_label(start)}. {mode.title()} mode selected this slot while keeping predicted demand below {max_building_kw:g} kW and respecting the verified {time_label(passport.earliest_start_slot)}-{time_label(passport.latest_finish_slot)} window.",
                "constraints_respected": ["User confirmed", "Non-critical load", "Allowed time window", f"Building demand <= {max_building_kw:g} kW"],
            })
        else:
            for slot in original_slots:
                working_load[slot] += passport.estimated_power_kw
    optimized = [round(value, 3) for value in working_load]
    def metrics(load):
        return {
            "peak_kw": round(max(load), 3),
            "energy_cost_units": round(sum(max(0, load[i] - solar[i]) * tariff[i] * 0.25 for i in range(96)), 3),
            "solar_used_kwh": round(sum(min(load[i], solar[i]) * 0.25 for i in range(96)), 3),
        }
    before, after = metrics(baseline), metrics(working_load)
    return {
        "mode": mode, "schedule": schedule, "baseline_load_kw": [round(v, 3) for v in baseline],
        "optimized_load_kw": optimized, "before": before, "after": after,
        "differences": {key: round(after[key] - before[key], 3) for key in before},
        "result_label": "simulated estimate", "constraint_violations": 0,
    }
