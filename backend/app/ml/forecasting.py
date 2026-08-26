import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from app.ml.evaluation import regression_metrics, select_lowest_mae


FEATURES = ["slot", "day_of_week", "lag_1", "lag_4", "lag_96"]


def _training_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    work["lag_1"] = work["power_kw"].shift(1)
    work["lag_4"] = work["power_kw"].shift(4)
    work["lag_96"] = work["power_kw"].shift(96)
    return work.dropna()


def seasonal_forecast(frame: pd.DataFrame) -> list[float]:
    averages = frame.groupby("slot")["power_kw"].mean()
    fallback = float(frame["power_kw"].mean())
    return [round(float(averages.get(slot, fallback)), 3) for slot in range(96)]


def random_forest_forecast(frame: pd.DataFrame) -> list[float]:
    train = _training_frame(frame)
    if len(train) < 192:
        return seasonal_forecast(frame)
    model = RandomForestRegressor(n_estimators=160, max_depth=11, min_samples_leaf=2, random_state=42, n_jobs=-1)
    model.fit(train[FEATURES], train["power_kw"])
    history = list(frame["power_kw"].astype(float))
    next_dow = int((frame.index[-1].dayofweek + 1) % 7)
    predictions = []
    for slot in range(96):
        row = pd.DataFrame([{"slot":slot,"day_of_week":next_dow,"lag_1":history[-1],"lag_4":history[-4],"lag_96":history[-96]}])
        value = max(0, float(model.predict(row[FEATURES])[0]))
        history.append(value)
        predictions.append(round(value, 3))
    return predictions


def forecast_next_day(frame: pd.DataFrame) -> list[float]:
    return random_forest_forecast(frame)


def _prediction_interval(forecast: list[float], error_kw: float) -> tuple[list[float], list[float]]:
    margin = max(0.2, 1.645 * error_kw)
    lower = [round(max(0, value - margin), 3) for value in forecast]
    upper = [round(value + margin, 3) for value in forecast]
    return lower, upper


def forecast_with_evaluation(frame: pd.DataFrame) -> dict:
    model_name = "Seasonal baseline"
    evaluation = {"status":"unavailable","reason":"At least 3 days are required for chronological evaluation"}
    forecast = seasonal_forecast(frame)
    error_kw = max(0.2, float(frame["power_kw"].std()) * 0.25)
    if len(frame) >= 288:
        train, actual = frame.iloc[:-96], frame.iloc[-96:]["power_kw"].to_numpy()
        rf_pred = random_forest_forecast(train)
        seasonal_pred = seasonal_forecast(train)
        comparison = {
            "Random Forest": regression_metrics(actual, rf_pred),
            "Seasonal baseline": regression_metrics(actual, seasonal_pred),
        }
        model_name = select_lowest_mae(comparison)
        forecast = random_forest_forecast(frame) if model_name == "Random Forest" else seasonal_forecast(frame)
        predicted = rf_pred if model_name == "Random Forest" else seasonal_pred
        error_kw = comparison[model_name]["rmse_kw"]
        evaluation = {
            "status":"measured", "method":"chronological last-day holdout", "test_points":96,
            **comparison[model_name], "models":comparison, "selected_model":model_name,
            "actual_kw":[round(float(value),3) for value in actual],
            "predicted_kw":[round(float(value),3) for value in predicted],
        }
    lower, upper = _prediction_interval(forecast, error_kw)
    return {
        "forecast_kw":forecast, "forecast_lower_kw":lower, "forecast_upper_kw":upper,
        "interval_confidence":0.90, "evaluation":evaluation, "model":model_name, "data_label":"forecast",
    }
