from fastapi import APIRouter, Response, Depends, security, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from src.schemas import SOrderUpdate, SOrderResult
import requests
from typing import Annotated
import secrets

router = APIRouter(
    prefix='/v1',
    tags=['Обмен данными с 1C!'],
)

security = HTTPBasic()

@router.post('/order')
async def update_order(orders: list[SOrderUpdate], credentials: Annotated[HTTPBasicCredentials, Depends(security)], response: Response) -> SOrderResult:
    res = {
        'success': False,
        'error': 'Order id exchange empty'
    }
    # убрать перед релизом
    credentials_dict = {"username": credentials.username, "password": credentials.password}
    orders_dict = {}
    auth_res = auth(credentials.username, credentials.password)
    if(auth_res):
        for order in orders:
            if len(order.ЗаказКлиента_id)>0:
                if len(order.ДокументОплаты_id) > 0:
                    res = {
                        'success': True,
                        'error': ''
                    }
                    #добавляем оплату к заказу
                    # url_request = 'https://erp-dev.vkvadrate.ru/api/orders/order-payment/'
                    # res = requests.get('https://erp-dev.vkvadrate.ru/api/orders/order-payment/', params={'order-id':order.ЗаказКлиента_id, 'doc-id':order.ДокументОплаты_id, 'sum':order.СуммаОплаты, 'key':'bc50571e-f48e-4922-9f32-d5a7aa98dccd'}).json()
                    orders_dict[order.ЗаказКлиента_id] = res
                else:
                    # обновляем или создаем заказ
                    # url_request = 'https://erp-dev.vkvadrate.ru/api/orders/update-order-status/?order-id='+order.ЗаказКлиента_id
                    # res = requests.get('https://erp-dev.vkvadrate.ru/api/orders/update-order-status/', params={'order-id':order.ЗаказКлиента_id}).json()
                    # res = requests.get('https://erp-dev.vkvadrate.ru/api/orders/update-order-status/', params={order-id:order.ЗаказКлиента_id})
                    res = {
                        'success': True,
                        'action': 'order_update | order_add | order_payment_add',
                        'error': ''
                    }
                    orders_dict[order.ЗаказКлиента_id] = res
            else:
                res = {
                    'success': False,
                    'error': 'Order id exchange empty'
                }
        order_result = SOrderResult(
            success=res['success'],
            orders=orders_dict,
            credentials=credentials_dict,
            error=''
        )
    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        order_result = SOrderResult(
            success=False,
            orders=orders_dict,
            credentials=credentials_dict,
            error='Incorrect username or password'
        )

    #return order_result
    return order_result

def auth(username, password):
    current_username_bytes = username.encode("utf8")
    correct_username_bytes = b"ffg_dealer_1c"
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = password.encode("utf8")
    correct_password_bytes = b"FE#$jkh@gs"
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        return False
        # raise HTTPException(
        #     status_code=status.HTTP_401_UNAUTHORIZED,
        #     detail="Incorrect username or password",
        #     headers={"WWW-Authenticate": "Basic"},
        # )
    else:
        return True