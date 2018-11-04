from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal
from typing import Any, Dict

from aiohttp import web

from tests.models import DataCls, Model
from tests.utils import multi_dict_to_dict_of_lists


async def post_handler(request: web.Request) -> web.Response:
    body = await request.json()
    return web.json_response(data=body)


async def pure_handler(request: web.Request) -> web.Response:
    params = request.query
    return web.json_response(data=multi_dict_to_dict_of_lists(params))


async def post_handler_without_annotation_argument(_: web.Request, data):
    return web.json_response(data=data)


async def post_handler_with_any_argument(_: web.Request, data: Any):
    return web.json_response(data=data)


async def post_handler_with_dict_argument(_: web.Request, data: dict) -> web.Response:
    return web.json_response(data=data)


async def post_handler_with_dict_typing_argument(_: web.Request, data: Dict) -> web.Response:
    return web.json_response(data=data)


async def handler_with_pydantic_model(_: web.Request, data: Model):
    return web.json_response(body=data.json())


async def handler_with_pydantic_dataclass(_: web.Request, data: DataCls):
    encoders = defaultdict(lambda: lambda x: x)
    encoders[Decimal] = float

    return web.json_response(data={k: (encoders[type(v)])(v) for k, v in asdict(data).items()})
