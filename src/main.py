import logging
import uvicorn
from fastapi import FastAPI
from src.exchange1c.router import router as exchange1c_router
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


sentry_sdk.init(
    dsn="https://eb1df35826031919269513ac315327ad@o4506926442610688.ingest.us.sentry.io/4506926446673920",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
    integrations=[
        LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.INFO   # Send records as events
        ),
    ],
)

logging.basicConfig(level=logging.INFO, filename="app_log.log",filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")


app = FastAPI(
    title='API Вквадрате'
)


app.include_router(exchange1c_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)