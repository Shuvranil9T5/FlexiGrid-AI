import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


def forecast_next_day(frame: pd.DataFrame) -> list[float]:
    """Fit a small RF model when enough history exists; otherwise use slot averages."""
    work = frame.copy()
    work["lag_1"] = work["power_kw"].shift(1)
    work["lag_4"] = work["power_kw"].shift(4)
    work["lag_96"] = work["power_kw"].shift(96)
    train = work.dropna()
    if len(train) < 192:
        averages = frame.groupby("slot")["power_kw"].mean()
        return [round(float(averages.get(slot, frame["power_kw"].mean())), 3) for slot in range(96)]
    features = ["slot", "day_of_week", "lag_1", "lag_4", "lag_96"]
    model = RandomForestRegressor(n_estimators=120, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(train[features], train["power_kw"])
    history = list(frame["power_kw"].astype(float))
    next_dow = int((frame.index[-1].dayofweek + 1) % 7)
    predictions = []
    for slot in range(96):
        row = pd.DataFrame([{
            "slot": slot,
            "day_of_week": next_dow,
            "lag_1": history[-1],
            "lag_4": history[-4],
            "lag_96": history[-96],
        }])
        value = max(0, float(model.predict(row[features])[0]))
        history.append(value)
        predictions.append(round(value, 3))
    return predictions

def seasonal_forecast(frame: pd.DataFrame) -> list[float]:
    averages = frame.groupby("slot")["power_kw"].mean()
    fallback = float(frame["power_kw"].mean())
    return [round(float(averages.get(slot, fallback)), 3) for slot in range(96)]

def metrics(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    mae = float(mean_absolute_error(actual, predicted))
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    nonzero = actual > 0.1
    mape = float(np.mean(np.abs((actual[nonzero]-predicted[nonzero])/actual[nonzero]))*100) if nonzero.any() else None
    return {"mae_kw":round(mae,3),"rmse_kw":round(rmse,3),"mape_percent":round(mape,2) if mape is not None else None}


def forecast_with_evaluation(frame: pd.DataFrame) -> dict:
    """Chronological holdout evaluation; never reports training accuracy as evidence."""
    forecast = forecast_next_day(frame)
    model_name = "Random Forest"
    evaluation = {"status": "unavailable", "reason": "At least 3 days are required for chronological evaluation"}
    if len(frame) >= 288:
        train, actual = frame.iloc[:-96], frame.iloc[-96:]["power_kw"].to_numpy()
        rf_pred, seasonal_pred = forecast_next_day(train), seasonal_forecast(train)
        comparison = {"Random Forest":metrics(actual,rf_pred), "Seasonal baseline":metrics(actual,seasonal_pred)}
        model_name = min(comparison, key=lambda name: comparison[name]["mae_kw"])
        forecast = forecast_next_day(frame) if model_name == "Random Forest" else seasonal_forecast(frame)
        predicted = rf_pred if model_name == "Random Forest" else seasonal_pred
        evaluation = {
            "status": "measured", "method": "chronological last-day holdout",
            "test_points": 96, **comparison[model_name], "models": comparison, "selected_model": model_name,
            "actual_kw": [round(float(value), 3) for value in actual],
            "predicted_kw": [round(float(value), 3) for value in predicted],
        }
    return {"forecast_kw": forecast, "evaluation": evaluation, "model": model_name, "data_label": "forecast"}
