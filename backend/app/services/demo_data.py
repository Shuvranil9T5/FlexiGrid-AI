from datetime import datetime, timedelta
import math
import numpy as np


def generate_demo_readings(days: int = 7, seed: int = 42) -> list[dict]:
    """Generate repeatable 15-minute aggregate building load readings."""
    rng = np.random.default_rng(seed)
    start = datetime(2026, 8, 1)
    readings = []
    for index in range(days * 96):
        timestamp = start + timedelta(minutes=15 * index)
        slot = index % 96
        hour = slot / 4
        base = 2.2 + 0.25 * math.sin((hour - 6) * math.pi / 12)
        occupancy = 1.6 if 32 <= slot < 76 else 0.25
        morning_pump = 2.8 if 28 <= slot < 32 else 0.0
        afternoon_process = 3.5 if 56 <= slot < 64 else 0.0
        evening_charge = 2.4 if 76 <= slot < 84 else 0.0
        noise = rng.normal(0, 0.12)
        power = max(0.2, base + occupancy + morning_pump + afternoon_process + evening_charge + noise)
        readings.append({"timestamp": timestamp.isoformat(), "power_kw": round(power, 3)})
    return readings


def solar_profile() -> list[float]:
    values = []
    for slot in range(96):
        hour = slot / 4
        solar = 0.0 if hour < 6 or hour > 18 else 5.0 * math.sin((hour - 6) * math.pi / 12)
        values.append(round(max(0, solar), 3))
    return values


def tariff_profile() -> list[float]:
    return [8.0 if 72 <= slot < 88 else 4.5 for slot in range(96)]

