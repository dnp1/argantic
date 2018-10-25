import asyncio
import inspect
import json
from dataclasses import is_dataclass
from typing import Dict, Callable, Awaitable, Optional, Tuple, Any, Iterator, Coroutine

from aiohttp import web
from pydantic import BaseModel

from argantic._util import identity_coro
from argantic.data_sources import DataSource
from argantic.errors import  ArganticIncompatibleType
from argantic.loaders import FormatSupport, AbstractLoader, QueryParamsLoader, RouteParamsLoader, BodyLoader

WebHandler = Callable[..., Awaitable[web.Response]]


class Argantic:
    def __init__(self):
        self._computed_handler: Dict[(int, str), WebHandler] = {}

        self.content_types = {
            'application/json': FormatSupport(mime_type='application/json',
                                              dumps=json.dumps,
                                              loads=json.loads)
        }
        self.default_content_type = 'application/json'
        self._data_source_orders: Dict[str, Tuple[DataSource, ...]] = {
            'GET': (DataSource.QueryParams, DataSource.RouteParams),
            'POST': (DataSource.QueryParams, DataSource.Body, DataSource.RouteParams),
            'PATCH': (DataSource.QueryParams, DataSource.Body, DataSource.RouteParams),
            'PUT': (DataSource.QueryParams, DataSource.Body, DataSource.RouteParams),
            'DELETE': (DataSource.QueryParams, DataSource.RouteParams),
        }

        self._loaders: Dict[DataSource, AbstractLoader] = {
            DataSource.QueryParams: QueryParamsLoader(),
            DataSource.RouteParams: RouteParamsLoader(),
            DataSource.Body: BodyLoader(self.content_types)
        }

        self._type_parsers = {
            str: str,
            int: int,
        }

    def _get_handler_parameter(self, handler) -> Optional[inspect.Parameter]:
        inspect_parameters: Iterator[inspect.Parameter] = iter(inspect.signature(handler).parameters.values())

        # trim request parameter
        next(inspect_parameters)

        parameters = list(inspect_parameters)

        if not parameters:
            return None
        elif len(parameters) > 1:
            raise NotImplemented()

        return parameters[0]

    def _resolve_data_loaders(self, request: web.Request) -> Tuple[
        Tuple[DataSource, Callable[[web.Request], Coroutine]], ...]:
        data_sources = self._data_source_orders[request.method.upper()]

        return tuple((ds, self._loaders[ds].loads) for ds in data_sources)

    def _get_data_parser(self, handler: WebHandler):
        parameter = self._get_handler_parameter(handler)
        if not parameter:
            return None

        annotation = parameter.annotation

        if any([annotation == parameter.empty, annotation == Any]):
            return identity_coro

        if inspect.isclass(annotation):
            if issubclass(annotation, BaseModel):
                return asyncio.coroutine(annotation.parse_obj)
            elif is_dataclass(annotation):
                return asyncio.coroutine(lambda d: annotation(**d))

        annotation = getattr(annotation, '__origin__', annotation)

        async def check(data):
            if type(data) != annotation:
                raise ArganticIncompatibleType()
            return data

        return check

    def _create_handler(self, handler: WebHandler, request: web.Request):
        parser = self._get_data_parser(handler)
        if not parser:
            return handler

        data_loaders = self._resolve_data_loaders(request)

        async def n_handler(request_: web.Request):
            data = {}
            for ds, loader in data_loaders:
                data.update(await loader(request))

            data = await parser(data)

            return await handler(request_, data)

        return n_handler

    def _get_argantic_handler(self, handler: WebHandler, request: web.Request) -> WebHandler:
        handler_key = self._get_handler_identifier(handler, request)
        try:
            return self._computed_handler[handler_key]
        except KeyError:
            argantic_handler = self._create_handler(handler, request)
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
