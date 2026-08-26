from app.routers import (
    events,
    forecasts,
    optimization,
    passports,
    reports,
    upload,
)


ALL_ROUTERS = (
    upload.router,
    events.router,
    passports.router,
    forecasts.router,
    optimization.router,
    reports.router,
)