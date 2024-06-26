import logging
import pickle
import time

from fastapi import APIRouter, Response, Depends, status, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import requests
from src.schemas import SOrderUpdate, SResult, SGoodsReturn, SMsg, SMeilisearch
from typing import Annotated
import secrets


router = APIRouter(
    prefix='/v1',
    tags=['Обмен данными с 1C!'],
)


security = HTTPBasic()


html = """
    <!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/v1/ws/${client_id}`);
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

class ConnectionManager:
    def __init__(self):
        # self.active_connections: list[WebSocket] = []
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, client_id:int):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        # self.active_connections.append(websocket)

    def disconnect(self, client_id:int):
        # self.active_connections.remove(websocket)
        del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: int):
        websocket = self.active_connections[client_id]
        await websocket.send_text(message)

    # async def broadcast(self, message: str):
    #     for connection in self.active_connections:
    #         await connection.send_text(message)


manager = ConnectionManager()


@router.get('/')
async def get():
    return HTMLResponse(html)


@router.post('/send-msg')
async def send_msg(msg: SMsg, credentials: Annotated[HTTPBasicCredentials, Depends(security)], response: Response) -> SResult:
    auth_res = auth(credentials.username, credentials.password)
    if (auth_res):
        response.status_code = status.HTTP_200_OK
        msg_text = str(f"{msg.msg}")
        await manager.send_personal_message(msg_text, msg.to_client_id)
        result = get_sucess_result()
    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        result = get_unauthorized_result()
    return result

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

@router.post('/meilisearch/update/')
async def update_order(meilisearch: SMeilisearch, credentials: Annotated[HTTPBasicCredentials, Depends(security)], response: Response, background_tasks: BackgroundTasks) -> SResult:
    auth_res = auth(credentials.username, credentials.password)
    if (auth_res):
        response.status_code = status.HTTP_200_OK
        background_tasks.add_task(update_meilisearch_index, meilisearch)
        result = get_sucess_result()
    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        result = get_unauthorized_result()
    return result

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # active_connections = manager.active_connections
            msg = str(f"Client {client_id} wrote: {data}")
            await manager.send_personal_message(msg, 1713731442678)
            # await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        # await manager.broadcast(f"Client #{client_id} left the chat")


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

async def update_meilisearch_index(meilisearch: SMeilisearch):
    auth_token = '0c6fc32d72cd9642f809c9f95069333e39518df01e82e6f8067f2f594dbfcc76'
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json',
    }
    base_url = 'https://goods.vkvadrate.ru'
    if len(meilisearch.goods) > 0:
        try:
            # Удаление индекса
            url_del = f"{base_url}/indexes/{meilisearch.index_name}"
            res_del = requests.delete(url_del, headers=headers).json()
            print(res_del)

            # Создание индекса post
            url_craete = f"{base_url}/indexes/"
            create = {
              "uid": meilisearch.index_name,
              "primaryKey": "id"
            }
            res_craete = requests.post(url_craete, json=create, headers=headers).json()
            print(res_craete)

            # Добавление товаров в мейлисерч post
            url_add = f"{base_url}/indexes/{meilisearch.index_name}/documents"
            res_add = requests.post(url_add, json=meilisearch.goods, headers=headers).json()
            logging.info(f"Запрос обновления индекса в Meilisearch {url_add}", res_add)
            print(res_add['taskUid'])

            # Обновление Settings https://facet2.vkvadrate.ru/setup.html?index=goods
            if(res_add['taskUid']>0):
                url_settings = f"https://facet2.vkvadrate.ru/setup.html?index={meilisearch.index_name}"
                requests.get(url_settings)


            # Обновление атрибутов
            # settings = {
            #     "rankingRules": [
            #       "words",
            #       "typo",
            #       "proximity",
            #       "attribute",
            #       "sort",
            #       "exactness",
            #       "release_date:desc",
            #       "rank:desc"
            #     ],
            #     "distinctAttribute": "id",
            #     "searchableAttributes": ["*"],
            #     "displayedAttributes": [
            #       "title",
            #       "overview",
            #       "genres",
            #       "release_date"
            #     ],
            #     "stopWords": [
            #       "the",
            #       "a",
            #       "an"
            #     ],
            #     "sortableAttributes": [
            #         "name",
            #         "price",
            #         "price_discount"
            #     ],
            #     "synonyms": {
            #       "wolverine": [
            #         "xmen",
            #         "logan"
            #     ],
            #       "logan": ["wolverine"]
            #     },
            #     "typoTolerance": {
            #       "minWordSizeForTypos": {
            #         "oneTypo": 8,
            #         "twoTypos": 10
            #       },
            #       "disableOnAttributes": ["title"]
            #     },
            #     "pagination": {
            #       "maxTotalHits": 5000
            #     },
            #     "faceting": {
            #       "maxValuesPerFacet": 200
            #     },
            #     "searchCutoffMs": 150
            #   }

            # Displayed attributes method PUT
            # url_displayed_attributes = f"{base_url}/indexes/{meilisearch.index_name}/settings/displayed-attributes"
            # displayed_attributes = ["*"]
            # res_displayed_attributes = requests.put(url_displayed_attributes, displayed_attributes, headers=headers).json()
            # print(res_displayed_attributes)

            # Filterable attributes method PUT
            # url_filterable_attributes = f"{base_url}/indexes/{meilisearch.index_name}/settings/filterable-attributes"
            # filterable_attributes = ["amount", "brand", "catalog_name", "collection", "colors", "dealer_price", "depth_tile", "depth", "design_type", "discount", "fire_hazard_class", "floor_heating", "floor_heating_set", "laying_method", "length_tile", "length", "m2_in_package", "name", "price", "price_discount", "price_m2", "price_m2_discount", "protective_layer", "room_type", "room_type_wet_set", "site_sliv_set", "wear_class", "width_tile", "width", "сountry_of_origin", "gloss_level", "stone_breed", "wood_breed", "integrated_backing", "warm_floors_set", "chamfer", "embossing_type", "product_use_type", "shade"]
            # res_filterable_attributes = requests.put(url_filterable_attributes, filterable_attributes, headers=headers).json()
            # print(res_filterable_attributes)

            # searchable attributes method PUT
            # url_searchable_attributes = f"{base_url}/indexes/{meilisearch.index_name}/settings/searchable-attributes"
            # res_searchable_attributes = requests.put(url_searchable_attributes, ["*"], headers=headers).json()
            # print(res_searchable_attributes)

            # sortable attributes method PUT
            # url_sortable_attributes = f"{base_url}/indexes/{meilisearch.index_name}/settings/sortable-attributes"
            # sortable_attributes = ["name", "price", "price_discount"]
            # res_sortable_attributes = requests.put(url_sortable_attributes, sortable_attributes, headers=headers).json()
            # print(res_sortable_attributes)


        except requests.exceptions.ConnectionError:
            logging.error("ConnectionError",exc_info=True)

    else:
       logging.error(f"Goods for Meilisearch is empty")

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
