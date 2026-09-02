from app.routers import (
    datasets,
    events,
    forecasts,
    optimization,
    passports,
    reports,
    upload,
)


ALL_ROUTERS = (
    datasets.router,
    upload.router,
    events.router,
    passports.router,
    forecasts.router,
    optimization.router,
    reports.router,
)
