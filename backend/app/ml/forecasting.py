"""Chronological forecasting with advanced models and uncertainty intervals."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from app.ml.features import FEATURE_COLUMNS, build_supervised_frame, next_feature_row
from app.ml.tft import dependency_status as tft_dependency_status
from app.ml.tft import forecast_from_checkpoint


DEFAULT_MODELS = ("Seasonal baseline", "Random Forest", "LightGBM")
SUPPORTED_MODELS = (*DEFAULT_MODELS, "TFT")


def seasonal_forecast(frame: pd.DataFrame) -> list[float]:
    """Forecast from the previous week or historical time-slot averages."""
    if len(frame) >= 672:
        return [round(float(value), 3) for value in frame["power_kw"].iloc[-672:-576]]
    averages = frame.groupby("slot")["power_kw"].mean()
    fallback = float(frame["power_kw"].mean())
    return [round(float(averages.get(slot, fallback)), 3) for slot in range(96)]


def _recursive_forecast(frame: pd.DataFrame, model) -> list[float]:
    history = list(frame["power_kw"].astype(float))
    timestamp = frame.index[-1]
    predictions: list[float] = []
    for _ in range(96):
        timestamp += pd.Timedelta(minutes=15)
        features = pd.DataFrame([next_feature_row(timestamp, history)])[FEATURE_COLUMNS]
        value = max(0.0, float(model.predict(features)[0]))
        history.append(value)
        predictions.append(round(value, 3))
    return predictions


def random_forest_forecast(frame: pd.DataFrame) -> list[float]:
    train = build_supervised_frame(frame)
    if len(train) < 192:
        raise RuntimeError("Random Forest requires at least 3 complete days after lag creation")
    model = RandomForestRegressor(
        n_estimators=180,
        max_depth=12,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train[FEATURE_COLUMNS], train["power_kw"])
    return _recursive_forecast(frame, model)


def lightgbm_dependency_status() -> tuple[bool, str]:
    try:
        import lightgbm  # noqa: F401
    except ImportError:
        return False, "Install lightgbm from backend/requirements.txt"
    return True, "ready"


def lightgbm_forecast(frame: pd.DataFrame) -> list[float]:
    ready, reason = lightgbm_dependency_status()
    if not ready:
        raise RuntimeError(reason)
    from lightgbm import LGBMRegressor

    train = build_supervised_frame(frame)
    if len(train) < 192:
        raise RuntimeError("LightGBM requires at least 3 complete days after lag creation")
    model = LGBMRegressor(
        objective="regression_l1",
        n_estimators=350,
        learning_rate=0.035,
        num_leaves=31,
        max_depth=-1,
        min_child_samples=20,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=0.15,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )
    model.fit(train[FEATURE_COLUMNS], train["power_kw"])
    return _recursive_forecast(frame, model)


def metrics(actual, predicted) -> dict:
    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    mae = float(mean_absolute_error(actual_array, predicted_array))
    rmse = float(np.sqrt(mean_squared_error(actual_array, predicted_array)))
    nonzero = np.abs(actual_array) > 0.1
    mape = (
        float(np.mean(np.abs((actual_array[nonzero] - predicted_array[nonzero]) / actual_array[nonzero])) * 100)
        if nonzero.any()
        else None
    )
    return {
        "mae_kw": round(mae, 3),
        "rmse_kw": round(rmse, 3),
        "mape_percent": round(mape, 2) if mape is not None else None,
    }


def model_capabilities() -> dict[str, dict]:
    lightgbm_ready, lightgbm_reason = lightgbm_dependency_status()
    tft_ready, tft_reason = tft_dependency_status()
    return {
        "Seasonal baseline": {"available": True, "type": "statistical benchmark", "reason": "ready"},
        "Random Forest": {"available": True, "type": "machine-learning benchmark", "reason": "ready"},
        "LightGBM": {"available": lightgbm_ready, "type": "advanced gradient boosting", "reason": lightgbm_reason},
        "TFT": {"available": tft_ready, "type": "advanced deep learning", "reason": tft_reason},
    }


def _model_functions() -> dict[str, Callable[[pd.DataFrame], list[float]]]:
    return {
        "Seasonal baseline": seasonal_forecast,
        "Random Forest": random_forest_forecast,
        "LightGBM": lightgbm_forecast,
        "TFT": forecast_from_checkpoint,
    }


def _prediction_interval(forecast: list[float], error_kw: float) -> tuple[list[float], list[float]]:
    """Build the Phase 2 two-sided 90% prediction interval."""
    margin = max(0.2, 1.645 * error_kw)
    lower = [round(max(0.0, value - margin), 3) for value in forecast]
    upper = [round(value + margin, 3) for value in forecast]
    return lower, upper


def forecast_next_day(frame: pd.DataFrame) -> list[float]:
    """Backward-compatible default forecast entry point."""
    try:
        return random_forest_forecast(frame)
    except RuntimeError:
        return seasonal_forecast(frame)


def forecast_with_evaluation(
    frame: pd.DataFrame,
    requested_models: list[str] | None = None,
) -> dict:
    """Evaluate models chronologically and retain Phase 2 uncertainty fields."""
    selected_names = requested_models or list(DEFAULT_MODELS)
    unknown = sorted(set(selected_names) - set(SUPPORTED_MODELS))
    if unknown:
        raise ValueError(f"Unknown forecast model(s): {', '.join(unknown)}")

    capabilities = model_capabilities()
    if len(frame) < 288:
        prediction = seasonal_forecast(frame)
        error_kw = max(0.2, float(frame["power_kw"].std()) * 0.25)
        if not np.isfinite(error_kw):
            error_kw = 0.2
        lower, upper = _prediction_interval(prediction, error_kw)
        return {
            "forecast_kw": prediction,
            "forecast_lower_kw": lower,
            "forecast_upper_kw": upper,
            "interval_confidence": 0.90,
            "evaluation": {
                "status": "unavailable",
                "reason": "At least 3 complete days are required for chronological evaluation",
                "models": {},
                "unavailable_models": {},
                "selected_model": "Seasonal baseline",
            },
            "model": "Seasonal baseline",
            "model_capabilities": capabilities,
            "data_label": "forecast",
        }

    train = frame.iloc[:-96]
    actual = frame.iloc[-96:]["power_kw"].to_numpy()
    comparison: dict[str, dict] = {}
    holdout_predictions: dict[str, list[float]] = {}
    unavailable: dict[str, str] = {}
    functions = _model_functions()

    for name in selected_names:
        try:
            predicted = functions[name](train)
            comparison[name] = metrics(actual, predicted)
            holdout_predictions[name] = predicted
        except (RuntimeError, ValueError, ImportError) as exc:
            unavailable[name] = str(exc)

    if not comparison:
        raise RuntimeError("No requested forecasting model could run")

    winner = min(comparison, key=lambda name: comparison[name]["mae_kw"])
    next_day = functions[winner](frame)
    lower, upper = _prediction_interval(next_day, comparison[winner]["rmse_kw"])
    evaluation = {
        "status": "measured",
        "method": "chronological final-day holdout",
        "test_points": 96,
        "models": comparison,
        "unavailable_models": unavailable,
        "selected_model": winner,
        **comparison[winner],
        "actual_kw": [round(float(value), 3) for value in actual],
        "predicted_kw": holdout_predictions[winner],
    }
    return {
        "forecast_kw": next_day,
        "forecast_lower_kw": lower,
        "forecast_upper_kw": upper,
        "interval_confidence": 0.90,
        "evaluation": evaluation,
        "model": winner,
        "model_capabilities": capabilities,
        "data_label": "forecast",
    }
