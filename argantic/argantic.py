import enum
from collections import defaultdict
from typing import Dict, Callable, Awaitable

from aiohttp import web

WebHandler = Callable[..., Awaitable[web.Response]]


class DataSource(enum.Enum):
    UriParams = enum.auto()
    QueryParams = enum.auto()
    FormData = enum.auto()
    Body = enum.auto()


class Argantic:
    def __init__(self):
        self._computed_handler: Dict[(int, str), WebHandler] = {}

    def _create_handler(self, handler, method):
        return handler

    def _get_argantic_handler(self, handler: WebHandler, method: str) -> WebHandler:
        handler_key = (id(handler), method)
        try:
            return self._computed_handler[handler_key]
        except KeyError:
            argantic_handler = self._create_handler(handler, method)
            self._computed_handler[handler_key] = argantic_handler
            return argantic_handler

    def middleware(self) -> WebHandler:
        @web.middleware
        async def argantic_middleware(request: web.Request, handler: WebHandler):
            argantic_handler = self._get_argantic_handler(handler, request.method)
            return await argantic_handler(request)

        return argantic_middleware
