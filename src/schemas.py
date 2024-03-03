from datetime import datetime

from pydantic import BaseModel

class SOrderUpdate(BaseModel):
    ИдентификаторЗаказаVK: str = None
    ЗаказКлиента_id: str = None
    ДокументОплаты_id: str = None
    СуммаОплаты: int = None

class SOrderResult(BaseModel):
    success: bool
    orders: dict
    credentials: dict
    error: str = None