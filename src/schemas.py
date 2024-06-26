from datetime import datetime

from pydantic import BaseModel

# class SOrderUpdate(BaseModel):
#     RequestUrl: str = None

class SOrderUpdate(BaseModel):
    ИдентификаторЗаказаVK: str = None
    ЗаказКлиента_id: str = None
    ДокументОплаты_id: str = None
    СуммаОплаты: float = None

class SGoodsReturn(BaseModel):
    id_ЗаказССайта: str = None
    id_ЗаказКлиента: str = None
    id_ВозвратТоваров: str = None

class SResult(BaseModel):
    success: bool
    error: str = None

class SMsg(BaseModel):
    from_client_id: int
    to_client_id: int
    msg: str = None

class SMeilisearch(BaseModel):
    index_name: str
    goods: list = []