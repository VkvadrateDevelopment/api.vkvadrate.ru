from datetime import datetime

from pydantic import BaseModel

# class SOrderUpdate(BaseModel):
#     RequestUrl: str = None

class SOrderUpdate(BaseModel):
    ИдентификаторЗаказаVK: str = None
    ЗаказКлиента_id: str = None
    ДокументОплаты_id: str = None
    СуммаОплаты: float = None

class SOrderResult(BaseModel):
    success: bool
    error: str = None