from collections import defaultdict
from typing import Dict, Callable, Coroutine

from aiohttp import web

WebHandler = Callable[[web.Request, ...], Coroutine[web.Response]]


class Argantic():
    def __init__(self):
        self._computed_handler: Dict[(int, str), WebHandler] = {}

    def _create_handler(self, handler):
        pass


    def _get_argantic_handler(self, handler: WebHandler, method: str) -> WebHandler:
        handler_key = id(handler, method)
        try:
            return self._computed_handler[handler_key]
        except KeyError:
            argantic_handler = self._create_handler()
            self._computed_handler[handler_key] = argantic_handler
            return argantic_handler

    def create(self) -> WebHandler:
        @web.middleware
        async def argantic_middleware(request: web.Request, handler: WebHandler):
            argantic_handler = self._get_argantic_handler(handler, request.method)
            return await argantic_handler(request)

        return argantic_middleware
