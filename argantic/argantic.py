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

    def _create_handler(self, handler, handler_key):
        return handler

    def _get_argantic_handler(self, handler: WebHandler, request: web.Request) -> WebHandler:
        handler_key = self._get_handler_identifier(handler, request)
        try:
            return self._computed_handler[handler_key]
        except KeyError:
            argantic_handler = self._create_handler(handler, handler_key)
            self._computed_handler[handler_key] = argantic_handler
            return argantic_handler

    def _get_handler_identifier(self, handler: WebHandler, request: web.Request):
        return id(handler), request.method, request.match_info.route.resource.canonical,

    def middleware(self) -> WebHandler:
        @web.middleware
        async def argantic_middleware(request: web.Request, handler: WebHandler):
            argantic_handler = self._get_argantic_handler(handler, request)
            return await argantic_handler(request)

        return argantic_middleware
