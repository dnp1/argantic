import asyncio
import enum
import inspect
import json
from typing import Dict, Callable, Awaitable, Optional, Tuple, NamedTuple, Union, Any, Iterator, Coroutine

from aiohttp import web
from pydantic import BaseModel

from argantic._util import multi_dict_to_dict

WebHandler = Callable[..., Awaitable[web.Response]]

from abc import ABCMeta, abstractmethod


class FormatSupport(NamedTuple):
    mime_type: str
    dumps: Callable[[object], str]
    loads: Callable[[Union[str, bytes, bytearray]], object]


class AbstractLoader(metaclass=ABCMeta):
    @abstractmethod
    async def loads(self, request: web.Request):
        pass


class QueryParamsLoader(AbstractLoader):
    async def loads(self, request: web.Request):
        return multi_dict_to_dict(request.query)


class RouteParamsLoader(AbstractLoader):
    async def loads(self, request: web.Request):
        return dict(request.match_info)


class BodyLoader(AbstractLoader):
    def __init__(self, content_types: Dict[str, FormatSupport]):
        self.content_types = content_types

    async def loads(self, request: web.Request):
        raw = await request.text()
        try:
            mimetype_support = self.content_types[request.content_type]
            return mimetype_support.loads(raw)
        except KeyError:
            raise UnsupportedContentType()


class DataSource(enum.Enum):
    RouteParams = enum.auto()
    QueryParams = enum.auto()
    Body = enum.auto()


class UnsupportedContentType(Exception):
    pass


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

    def _loads(self, content_type: str, raw: str) -> Any:
        content_type = content_type or self.default_content_type
        try:
            mimetype_support = self.content_types[content_type]
        except KeyError:
            raise UnsupportedContentType()

        return mimetype_support.loads(raw)

    def _get_handler_url_params(self, request: web.Request) -> Optional[Optional[Dict[str, int]]]:
        pattern = request.match_info.route.resource.get_info().get('pattern')
        if pattern:
            return pattern.groupindex

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

    def _resolve_data_loaders(self, request) -> Tuple[Callable[[web.Request], Coroutine], ...]:
        data_sourcres = self._data_source_orders[request.method.upper()]

        return tuple(self._loaders[ds].loads for ds in data_sourcres)

    def _get_data_parser(self, handler: WebHandler):
        parameter = self._get_handler_parameter(handler)
        if not parameter:
            return None

        annotation = parameter.annotation

        identity = asyncio.coroutine(lambda x: x)

        if any([annotation == parameter.empty, annotation == Any]):
            return identity

        if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
            return asyncio.coroutine(annotation.parse_obj)

        return identity

    def _create_handler(self, handler: WebHandler, request: web.Request):
        parser = self._get_data_parser(handler)
        if not parser:
            return handler

        data_retrievers = self._resolve_data_loaders(request)

        async def n_handler(request_: web.Request):
            data = {}
            for loader in data_retrievers:
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
