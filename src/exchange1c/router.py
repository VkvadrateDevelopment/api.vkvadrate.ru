import logging
import pickle
import time

from fastapi import APIRouter, Response, Depends, status, BackgroundTasks, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import requests
from src.schemas import SOrderUpdate, SResult, SGoodsReturn
from typing import Annotated
import secrets


router = APIRouter(
    prefix='/v1',
    tags=['Обмен данными с 1C!'],
)


security = HTTPBasic()


@router.get('/')
async def get():
    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Chat</title>
        </head>
        <body>
            <h1>WebSocket Chat</h1>
            <form action="" onsubmit="sendMessage(event)">
                <input type="text" id="messageText" autocomplete="off"/>
                <button>Send</button>
            </form>
            <ul id='messages'>
            </ul>
            <script>
                var ws = new WebSocket("ws://127.0.0.1:8000/v1/ws/");
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                };
                function sendMessage(event) {
                    var input = document.getElementById("messageText")
                    ws.send(input.value)
                    input.value = ''
                    event.preventDefault()
                }
            </script>
        </body>
    </html>
    """
    return HTMLResponse(html)

@router.post('/order/')
async def update_order(orders: list[SOrderUpdate], credentials: Annotated[HTTPBasicCredentials, Depends(security)], response: Response, background_tasks: BackgroundTasks) -> SResult:
    auth_res = auth(credentials.username, credentials.password)
    if (auth_res):
        response.status_code = status.HTTP_200_OK
        background_tasks.add_task(send_orders_to_erp, orders)
        result = get_sucess_result()
    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        result = get_unauthorized_result()
    return result


@router.post('/order/goods-returns/')
async def goods_return(goods_return: list[SGoodsReturn], credentials: Annotated[HTTPBasicCredentials, Depends(security)], response: Response, background_tasks: BackgroundTasks) -> SResult:
    auth_res = auth(credentials.username, credentials.password)
    if (auth_res):
        response.status_code = status.HTTP_200_OK
        background_tasks.add_task(send_goods_return_to_erp, goods_return)
        result = get_sucess_result()
    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        result = get_unauthorized_result()
    return result


@router.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


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


def get_unauthorized_result():
    result = SResult(
        success=False,
        error='Incorrect username or password'
    )
    return result


def get_sucess_result():
    result = SResult(
        success=True,
        error='Async request send'
    )
    return result

async def send_orders_to_erp(orders: list[SOrderUpdate]):
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

async def send_goods_return_to_erp(goods_return: list[SGoodsReturn]):
    orders_dict = {}
    res_dict = {'success': True,
                'orders': orders_dict,
                'error': ''}
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': '*/*',
        'Content-Type': 'text/html',
        'Connection': 'keep-alive'}
    for return_list in goods_return:
        if (len(return_list.id_ЗаказССайта) > 0 or len(return_list.id_ЗаказКлиента) > 0) and len(return_list.id_ВозвратТоваров) > 0:
                # Добавление оплаты по заказу
                params = {'order-id': return_list.id_ЗаказССайта, 'order-1c-id': return_list.id_ЗаказКлиента,
                          'return-id': return_list.id_ВозвратТоваров, 'key': 'bf959cbb-2f4c-43d2-8703-c67abcab80d8'}
                logging.info(f"Запрос возврат товара к ERP. order-id: {return_list.id_ЗаказКлиента}", params)
                # Ждем 6 секунды чтобы 1С успела записать заказ
                time.sleep(6)
                try:
                    res = requests.get('https://erp-dev.vkvadrate.ru/api/orders/return-order-goods/', params=params,
                                       headers=headers).json()
                except requests.exceptions.ConnectionError:
                    logging.error("ConnectionError",exc_info=True)
                logging.info(f"Ответ по возврату от ERP. order-id: {return_list.id_ЗаказКлиента}", res)
                logging.info(f"Ответ : {res}")

        else:
            logging.error(f"id_ЗаказССайта or id_ЗаказКлиента is empty")


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
