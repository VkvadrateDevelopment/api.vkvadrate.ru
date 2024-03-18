import logging
import pickle
import time

from fastapi import APIRouter, Response, Depends, status, BackgroundTasks
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import requests
from src.schemas import SOrderUpdate, SOrderResult
from typing import Annotated
import secrets


router = APIRouter(
    prefix='/v1',
    tags=['Обмен данными с 1C!'],
)


security = HTTPBasic()


@router.post('/order/')
async def update_order(orders: list[SOrderUpdate], credentials: Annotated[HTTPBasicCredentials, Depends(security)], response: Response, background_tasks: BackgroundTasks) -> SOrderResult:

    auth_res = auth(credentials.username, credentials.password)
    if (auth_res):
        response.status_code = status.HTTP_200_OK
        background_tasks.add_task(send_request_to_1c, orders)
        order_result = SOrderResult(
            success=True,
            error='Async request send'
        )
    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        order_result = SOrderResult(
            success=False,
            error='Incorrect username or password'
        )
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
    else:
        return True


async def send_request_to_1c(orders: list[SOrderUpdate]):
    orders_dict = {}
    res_dict = {'success': True,
                'orders': orders_dict,
                'error': ''}
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': '*/*',
        'Content-Type': 'text/html',
        'Connection': 'keep-alive'}
    for order in orders:
        if len(order.ЗаказКлиента_id) > 0:
            if len(order.ДокументОплаты_id) > 0:
                # Добавление оплаты по заказу
                params = {'order-id': order.ЗаказКлиента_id, 'doc-id': order.ДокументОплаты_id,
                          'sum': order.СуммаОплаты, 'key': 'bc50571e-f48e-4922-9f32-d5a7aa98dccd'}
                logging.info(f"Запрос добавления оплаты к ERP. order-id: {order.ЗаказКлиента_id}", params)
                # Ждем 3 секунды чтобы 1С успела записать заказ
                time.sleep(6)
                try:
                    res = requests.get('https://erp-dev.vkvadrate.ru/api/orders/order-payment/', params=params,
                                       headers=headers).json()
                except requests.exceptions.ConnectionError:
                    logging.error("ConnectionError",exc_info=True)
                logging.info(f"Ответ от ERP. order-id: {order.ЗаказКлиента_id}", res)
            else:
                # обновляем или создаем заказ
                params = {'order-id': order.ЗаказКлиента_id}
                logging.info(f"Запрос обновления заказа к ERP. order-id: {order.ЗаказКлиента_id}", params)
                # Ждем 3 секунды чтобы 1С успела записать заказ
                time.sleep(6)
                try:
                    res = requests.get('https://erp-dev.vkvadrate.ru/api/orders/update-order-status/', params=params,
                                       headers=headers).json()
                except requests.exceptions.ConnectionError:
                    logging.error("ConnectionError",exc_info=True)
                logging.info(f"Ответ от ERP: order-id: {order.ЗаказКлиента_id}", res)
        else:
            logging.error(f"ЗаказКлиента_id is empty")


async def write_log(request_res: dict):
    # current_datetime = datetime.now()
    with open("log.txt", mode="wb") as log:
        pickle.dump(request_res, log)
    # with open("log.txt", mode="w") as log:
    #     log_content = f"==========={current_datetime}=========\n"
    #     log.write(log_content)


def test_requests():
    pass
    # for order in orders:
    #     if len(order.RequestUrl) > 0:
    #         headers = {
    #             'User-Agent': 'Mozilla/5.0',
    #             'Accept': '*/*',
    #             'Content-Type': 'text/html',
    #             'Connection': 'keep-alive'}
    #         url = order.RequestUrl
    #         res = requests.get(url, headers=headers)
    #         orders_dict[1] = res.text
    #         order_result = SOrderResult(
    #             success=True,
    #             orders=orders_dict,
    #             error=''
    #         )
    #     else:
    #         order_result = SOrderResult(
    #             success=False,
    #             orders=orders_dict,
    #             error='RequestUrl empty'
    #         )
    # res = requests.get('https://erp-dev.vkvadrate.ru/api/orders/update-order-status/', params={order-id:order.ЗаказКлиента_id})
    # res = {
    #     'success': True,
    #     'action': 'order_update | order_add | order_payment_add',
    #     'error': ''
    # }
    # url = order.RequestUrl
    #
    # res = requests.get(url, headers=headers)
    # res = requests.get('https://iteem.ru', auth=(username, password), headers=headers)
    # res = requests.get('https://httpbin.org/get', params=params, headers=headers).json()
    # res = requests.get('https://erp-dev.vkvadrate.ru/api/orders/order-payment/', params={'order-id':order.ЗаказКлиента_id, 'doc-id':order.ДокументОплаты_id, 'sum':order.СуммаОплаты, 'key':'bc50571e-f48e-4922-9f32-d5a7aa98dccd'}, headers=headers, verify=False).json()
    #=======JОбращение к 1С напрямую
    # username = "readonlytest"
    # password = "readonlytest"
    # res = requests.get('https://files.finefloor.ru:9443/Trade114-managers-work/hs/vkapi/v1/ExchangeSettings', auth=(username, password))
