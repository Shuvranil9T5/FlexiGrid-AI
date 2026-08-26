from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class EnergyReading(BaseModel):
    timestamp: datetime
    power_kw: float = Field(ge=0)


class AnalysisRequest(BaseModel):
    readings: list[EnergyReading]
    event_threshold_kw: float = Field(default=0.8, gt=0)

class EventDetectionRequest(AnalysisRequest):
    pass

class FlexibilityPassport(BaseModel):
    pattern_id: str
    label: str = "Candidate flexible load"
    typical_start_slot: int = Field(ge=0, le=95)
    duration_slots: int = Field(ge=1, le=96)
    estimated_power_kw: float = Field(gt=0)
    earliest_start_slot: int = Field(ge=0, le=95)
    latest_finish_slot: int = Field(ge=1, le=96)
    priority: int = Field(default=2, ge=1, le=5)
    interruptible: bool = False
    minimum_runtime_slots: int = Field(default=1, ge=1, le=96)
    criticality: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    confidence: float = Field(default=0.5, ge=0, le=1)
    notes: str = ""
    verified: bool = False
    status: str = Field(default="candidate", pattern="^(candidate|confirmed|rejected)$")


class ForecastRequest(BaseModel):
    readings: list[EnergyReading]


class OptimizationRequest(BaseModel):
    forecast_kw: list[float] = Field(min_length=96, max_length=96)
    solar_kw: list[float] | None = None
    tariff: list[float] | None = None
    passports: list[FlexibilityPassport]
    max_building_kw: float = Field(default=20.0, gt=0)
    mode: str = Field(default="balanced", pattern="^(balanced|cost|peak|carbon)$")


class OptimizationReportRequest(BaseModel):
    result: dict[str, Any]
    source_label: str = "simulated"
