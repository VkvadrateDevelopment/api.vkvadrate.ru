from fastapi import FastAPI
from src.exchange1c.router import router as exchange1c_router


app = FastAPI(
    title='API Вквадрате'
)
app.include_router(exchange1c_router)