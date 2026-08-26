from __future__ import annotations

try:
    from ortools.sat.python import cp_model
except ImportError:  # Local fallback keeps the API usable until requirements are installed.
    cp_model = None


SCALE = 100
MODES = ("balanced", "cost", "peak", "carbon")
WEIGHTS = {
    "balanced": {"cost": 3, "peak": 7, "carbon": 2, "inconvenience": 1},
    "cost": {"cost": 8, "peak": 2, "carbon": 1, "inconvenience": 1},
    "peak": {"cost": 1, "peak": 12, "carbon": 1, "inconvenience": 1},
    "carbon": {"cost": 1, "peak": 3, "carbon": 9, "inconvenience": 1},
}


def _time(slot: int) -> str:
    slot = max(0, min(96, slot))
    return f"{slot // 4:02d}:{(slot % 4) * 15:02d}" if slot < 96 else "24:00"


def _eligible(passports) -> list:
    return [p for p in sorted(passports, key=lambda item: item.priority) if p.verified and p.status == "confirmed" and p.criticality != "critical"]


def _base_without_flexible(load: list[float], passports: list) -> list[float]:
    result = [float(v) for v in load]
    for passport in passports:
        for slot in range(passport.typical_start_slot, min(96, passport.typical_start_slot + passport.duration_slots)):
            result[slot] = max(0.0, result[slot] - passport.estimated_power_kw)
    return result


def _candidate_starts(passport) -> list[int]:
    latest = min(96 - passport.duration_slots, passport.latest_finish_slot - passport.duration_slots)
    return list(range(passport.earliest_start_slot, latest + 1)) if latest >= passport.earliest_start_slot else []


def _robust_power(passport) -> float:
    """Use the Passport's upper power estimate for safety constraints."""
    return float(passport.power_max_kw or passport.estimated_power_kw)


def _choice_score(passport, start: int, base: list[float], solar: list[float], tariff: list[float], mode: str) -> float:
    weights = WEIGHTS[mode]
    slots = range(start, start + passport.duration_slots)
    projected = [base[s] + passport.estimated_power_kw for s in slots]
    cost = sum(max(0, base[s] + passport.estimated_power_kw - solar[s]) * tariff[s] * 0.25 for s in slots)
    carbon = sum(max(0, base[s] + passport.estimated_power_kw - solar[s]) * (1.3 if 68 <= s <= 88 else 0.7) * 0.25 for s in slots)
    inconvenience = abs(start - passport.typical_start_slot) * 0.08
    return weights["cost"] * cost + weights["peak"] * max(projected) + weights["carbon"] * carbon + weights["inconvenience"] * inconvenience


def _fallback_choices(passports: list, robust_base: list[float], solar: list[float], tariff: list[float], limit: float, mode: str) -> tuple[str, dict[str, int]]:
    working = robust_base.copy()
    choices = {}
    for passport in passports:
        feasible = []
        robust_power = _robust_power(passport)
        for start in _candidate_starts(passport):
            slots = range(start, start + passport.duration_slots)
            if all(working[s] + robust_power <= limit for s in slots):
                feasible.append((_choice_score(passport, start, working, solar, tariff, mode), start))
        if not feasible:
            return "INFEASIBLE", {}
        start = min(feasible)[1]
        choices[passport.pattern_id] = start
        for slot in range(start, start + passport.duration_slots):
            working[slot] += robust_power
    return "FEASIBLE", choices


def _cp_sat_choices(passports: list, robust_base: list[float], solar: list[float], tariff: list[float], limit: float, mode: str) -> tuple[str, dict[str, int]]:
    if cp_model is None:
        return _fallback_choices(passports, robust_base, solar, tariff, limit, mode)
    model = cp_model.CpModel()
    choices = {}
    variables = {}
    for passport in passports:
        starts = _candidate_starts(passport)
        if not starts:
            return "INFEASIBLE", {}
        variables[passport.pattern_id] = {start:model.NewBoolVar(f"{passport.pattern_id}_{start}") for start in starts}
        model.Add(sum(variables[passport.pattern_id].values()) == 1)

    limit_i = int(round(limit * SCALE))
    peak = model.NewIntVar(0, max(limit_i, 1), "peak")
    for slot in range(96):
        additions = []
        for passport in passports:
            power_i = int(round(_robust_power(passport) * SCALE))
            for start, variable in variables[passport.pattern_id].items():
                if start <= slot < start + passport.duration_slots:
                    additions.append(power_i * variable)
        load_expression = int(round(robust_base[slot] * SCALE)) + sum(additions)
        model.Add(load_expression <= limit_i)
        model.Add(peak >= load_expression)

    weights = WEIGHTS[mode]
    objective_terms = [weights["peak"] * peak]
    for passport in passports:
        for start, variable in variables[passport.pattern_id].items():
            slots = range(start, start + passport.duration_slots)
            incremental_cost = sum(passport.estimated_power_kw * tariff[s] * 0.25 for s in slots)
            incremental_carbon = sum(passport.estimated_power_kw * (1.3 if 68 <= s <= 88 else 0.7) * 0.25 for s in slots)
            inconvenience = abs(start - passport.typical_start_slot) * 0.08
            coefficient = int(round(100 * (weights["cost"]*incremental_cost + weights["carbon"]*incremental_carbon + weights["inconvenience"]*inconvenience)))
            objective_terms.append(coefficient * variable)
    model.Minimize(sum(objective_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    solver.parameters.num_search_workers = 8
    solved = solver.Solve(model)
    status = solver.StatusName(solved)
    if solved not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return status, {}
    for passport in passports:
        choices[passport.pattern_id] = next(start for start, variable in variables[passport.pattern_id].items() if solver.Value(variable))
    return status, choices


def _metrics(load: list[float], solar: list[float], tariff: list[float]) -> dict:
    return {
        "peak_kw": round(max(load), 3),
        "energy_cost_units": round(sum(max(0, load[i]-solar[i])*tariff[i]*0.25 for i in range(96)), 3),
        "solar_used_kwh": round(sum(min(load[i],solar[i])*0.25 for i in range(96)), 3),
        "grid_energy_kwh": round(sum(max(0,load[i]-solar[i])*0.25 for i in range(96)), 3),
    }


def optimize_schedule(forecast, passports, solar=None, tariff=None, max_building_kw=20.0, mode="balanced", forecast_upper=None, include_scenarios=True):
    solar = list(solar or [0.0]*96)
    tariff = list(tariff or [1.0]*96)
    baseline = [float(v) for v in forecast]
    upper = [float(v) for v in (forecast_upper or forecast)]
    eligible = _eligible(passports)
    if not eligible:
        before = _metrics(baseline, solar, tariff)
        return {"mode":mode,"solver_status":"NO_CONFIRMED_LOADS","solver_engine":"OR-Tools CP-SAT" if cp_model else "deterministic fallback","schedule":[],"baseline_load_kw":baseline,"optimized_load_kw":baseline,"before":before,"after":before,"differences":{key:0 for key in before},"scenarios":[],"result_label":"simulated estimate","constraint_violations":0}

    base = _base_without_flexible(baseline, eligible)
    robust_base = _base_without_flexible(upper, eligible)
    status, choices = _cp_sat_choices(eligible, robust_base, solar, tariff, max_building_kw, mode)
    if not choices:
        before = _metrics(baseline, solar, tariff)
        return {"mode":mode,"solver_status":status,"solver_engine":"OR-Tools CP-SAT" if cp_model else "deterministic fallback","schedule":[],"baseline_load_kw":baseline,"optimized_load_kw":baseline,"before":before,"after":before,"differences":{key:0 for key in before},"scenarios":[],"result_label":"no feasible schedule","constraint_violations":1}

    optimized = base.copy()
    schedule = []
    for passport in eligible:
        start = choices[passport.pattern_id]
        for slot in range(start, start + passport.duration_slots):
            optimized[slot] += passport.estimated_power_kw
        schedule.append({
            "pattern_id":passport.pattern_id,"label":passport.label,"original_start_slot":passport.typical_start_slot,
            "recommended_start_slot":start,"duration_slots":passport.duration_slots,"estimated_power_kw":passport.estimated_power_kw,
            "original_time":_time(passport.typical_start_slot),"recommended_time":_time(start),"end_time":_time(start+passport.duration_slots),
            "reason":f"{mode.title()} scenario selected by a robust constraint model",
            "explanation":f"Move {passport.label} from {_time(passport.typical_start_slot)} to {_time(start)}. The optimizer used the upper forecast bound, the edited tariff, solar availability, and the verified {_time(passport.earliest_start_slot)}-{_time(passport.latest_finish_slot)} operating window.",
            "constraints_respected":["User confirmed","Non-critical load","Allowed time window",f"Upper-bound demand <= {max_building_kw:g} kW"],
        })
    before, after = _metrics(baseline, solar, tariff), _metrics(optimized, solar, tariff)
    result = {
        "mode":mode,"solver_status":status,"solver_engine":"OR-Tools CP-SAT" if cp_model else "deterministic fallback",
        "schedule":schedule,"baseline_load_kw":[round(v,3) for v in baseline],"optimized_load_kw":[round(v,3) for v in optimized],
        "before":before,"after":after,"differences":{key:round(after[key]-before[key],3) for key in before},
        "result_label":"uncertainty-aware simulated estimate","constraint_violations":0,"scenarios":[],
    }
    if include_scenarios:
        scenarios = []
        for scenario_mode in MODES:
            scenario = result if scenario_mode == mode else optimize_schedule(forecast, passports, solar, tariff, max_building_kw, scenario_mode, forecast_upper, False)
            scenarios.append({"mode":scenario_mode,"status":scenario["solver_status"],**scenario["after"],"shifted_loads":len(scenario["schedule"])})
        result["scenarios"] = scenarios
    return result
