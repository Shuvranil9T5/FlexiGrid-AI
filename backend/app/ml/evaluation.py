import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error


def regression_metrics(actual, predicted) -> dict:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    if actual.shape != predicted.shape or actual.size == 0:
        raise ValueError("Actual and predicted values must be non-empty and have the same shape")
    nonzero = np.abs(actual) > 0.1
    mape = np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100 if nonzero.any() else None
    return {
        "mae_kw": round(float(mean_absolute_error(actual, predicted)), 3),
        "rmse_kw": round(float(np.sqrt(mean_squared_error(actual, predicted))), 3),
        "mape_percent": round(float(mape), 2) if mape is not None else None,
    }


def select_lowest_mae(comparison: dict[str, dict]) -> str:
    if not comparison:
        raise ValueError("At least one model result is required")
    return min(comparison, key=lambda name: comparison[name]["mae_kw"])
