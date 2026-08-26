import numpy as np
import pandas as pd


def detect_faults(frame: pd.DataFrame, events: list[dict], patterns: list[dict]) -> list[dict]:
    alerts = []
    power = frame["power_kw"]
    median = float(power.median())
    mad = float((power - median).abs().median())
    spike_limit = median + 6 * 1.4826 * max(mad, 0.05)
    spikes = frame[power > spike_limit]
    if not spikes.empty:
        alerts.append({"code":"LOAD_SPIKE","severity":"high","title":"Unusual demand spike","description":f"{len(spikes)} reading(s) exceeded the robust {spike_limit:.2f} kW limit.","evidence":{"count":len(spikes),"limit_kw":round(spike_limit,2)}})

    off_hours = frame[(frame["slot"] < 28) | (frame["slot"] >= 84)]
    occupied = frame[(frame["slot"] >= 32) & (frame["slot"] < 72)]
    if not off_hours.empty and not occupied.empty:
        off_mean, occupied_mean = float(off_hours["power_kw"].mean()), float(occupied["power_kw"].mean())
        ratio = off_mean / max(occupied_mean, 0.1)
        if ratio > 0.72:
            alerts.append({"code":"HIGH_BASELOAD","severity":"medium","title":"High off-hours baseload","description":f"Off-hours demand is {ratio*100:.0f}% of occupied-period demand.","evidence":{"off_hours_kw":round(off_mean,2),"occupied_kw":round(occupied_mean,2)}})

    daily = frame["power_kw"].resample("1D").mean().dropna()
    if len(daily) >= 5:
        slope = float(np.polyfit(np.arange(len(daily)), daily.to_numpy(), 1)[0])
        if slope > max(0.08, float(daily.mean()) * 0.025):
            alerts.append({"code":"RISING_BASELOAD","severity":"medium","title":"Rising daily baseload","description":f"Average demand increased by approximately {slope:.2f} kW per day.","evidence":{"daily_slope_kw":round(slope,3)}})

    unmatched = max(0, sum(e["event_type"] == "START" for e in events) - sum(e["event_type"] == "STOP" for e in events))
    if unmatched:
        alerts.append({"code":"UNMATCHED_START","severity":"low","title":"Possible incomplete operating cycle","description":f"{unmatched} start event(s) have no compatible stop event in the analysis window.","evidence":{"unmatched_starts":unmatched}})

    if not alerts:
        alerts.append({"code":"NO_MAJOR_ANOMALY","severity":"info","title":"No major anomaly detected","description":"The dataset did not cross the configured statistical fault thresholds.","evidence":{"patterns_reviewed":len(patterns)}})
    return alerts
