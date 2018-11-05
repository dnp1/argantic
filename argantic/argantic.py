import inspect
import json
from dataclasses import is_dataclass
from json import JSONDecodeError
from typing import Dict, Callable, Awaitable, Optional, Tuple, Any, Iterator, Coroutine, Type, Hashable

from aiohttp import web
from aiohttp.hdrs import ACCEPT
from aiohttp.web_exceptions import HTTPUnprocessableEntity, HTTPNotAcceptable, HTTPClientError, \
    HTTPUnsupportedMediaType, HTTPBadRequest
from pydantic import BaseModel

from argantic.util import identity_coro, update_all
from argantic.errors import ArganticValidationError, ArganticUnsupportedContentType, ArganticDecodeError
from argantic.loaders import FormatSupport, AbstractLoader, QueryParamsLoader, RouteParamsLoader, BodyLoader
from argantic.parsers import parse_ordinary_type_factory, parse_dataclass_factory, parse_model_factory

WebHandler = Callable[..., Awaitable[web.Response]]


class Argantic:

    def __init__(self,
                 apply_params_every_item: bool = True):

        self._apply_params_every_item = apply_params_every_item

        self._computed_handler: Dict[Hashable, WebHandler] = {}
        self.content_types = {
            'application/json': FormatSupport(mime_type='application/json',
                                              dumps=json.dumps,
                                              loads=json.loads,
                                              parse_error=JSONDecodeError)
        }

        query_params_loader = QueryParamsLoader()
        route_params_loader = RouteParamsLoader()
        self.default_content_type = 'application/json'
        body_loader = BodyLoader(self.content_types, default_content_type=self.default_content_type)

        self._invalid_body_exception: Type[HTTPClientError] = HTTPUnprocessableEntity
        self._unsupported_media_type_exception: Type[HTTPClientError] = HTTPUnsupportedMediaType
        self._not_acceptable_request_exception: Type[HTTPClientError] = HTTPNotAcceptable
        self._decode_error_exception = HTTPBadRequest

        self._data_loaders: Dict[str, Tuple[AbstractLoader, ...]] = {
            'GET': (query_params_loader, route_params_loader),
            'POST': (query_params_loader, body_loader, route_params_loader),
            'PATCH': (query_params_loader, body_loader, route_params_loader),
            'PUT': (query_params_loader, body_loader, route_params_loader),
            'DELETE': (query_params_loader, route_params_loader),
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
            raise NotImplementedError()

        return parameters[0]

    def _resolve_data_loaders(self, request: web.Request) -> Tuple[Tuple, Callable[[web.Request], Coroutine]]:
        data_loaders = self._data_loaders[request.method.upper()]
        loaders_types = tuple(type(loader) for loader in data_loaders)

        can_have_list = any(loader.can_return_list for loader in data_loaders)

        if can_have_list and self._apply_params_every_item:

            async def load(req_: web.Request):
                list_value = None
                loaded_data = {}
                for loader in data_loaders:
                    data = await loader.loads(req_)
                    loaded_data[type(loader)] = data

                    if type(data) == list:
                        list_value = type(loader)

                return loaded_data, list_value

            return loaders_types, load
        else:
            async def load(req_: web.Request):
                return {
                           type(loader): await loader.loads(req_) for loader in data_loaders
                       }, False

            return loaders_types, load

    def _get_data_parser(self, handler: WebHandler):
        parameter = self._get_handler_parameter(handler)
        if not parameter:
            return None

        annotation = parameter.annotation

        if annotation == parameter.empty or annotation == Any:
            return identity_coro

        if inspect.isclass(annotation):
            if issubclass(annotation, BaseModel):
                return parse_model_factory(annotation)
            elif is_dataclass(annotation):
                return parse_dataclass_factory(annotation)

        annotation = getattr(annotation, '__origin__', annotation)

        return parse_ordinary_type_factory(annotation)

    def _create_handler(self, handler: WebHandler, request: web.Request):
        parser = self._get_data_parser(handler)
        if not parser:
            return handler

        data_loaders, loads_func = self._resolve_data_loaders(request)

        async def n_handler(req_: web.Request):
            try:
                data_collection, list_key = await loads_func(req_)
            except ArganticUnsupportedContentType as e:
                raise self._unsupported_media_type_exception from e
            except ArganticDecodeError as e:
                raise self._decode_error_exception from e

            if list_key:
                list_data = data_collection[list_key]
                list_inx = data_loaders.index(list_key)
                for inx, loader in enumerate(data_loaders):
                    if inx != list_inx:
                        update_all(list_data, data_collection[loader], override=inx > list_inx)
                data = list_data

            else:
                data = {}
                for loader in data_loaders:
                    data.update(data_collection[loader])

            try:
                data = await parser(data)
            except ArganticValidationError as e:
                raw, content_type = self._create_raw_response_body(req_, e.report)
                raise self._invalid_body_exception(text=raw, content_type=content_type) from e

            return await handler(req_, data)

        return n_handler

    def _create_raw_response_body(self, request: web.Request, data) -> Tuple[str, str]:
        response_content_type = request.content_type or self.default_content_type

        accept_header: str = request.headers.get(ACCEPT)
        if accept_header:
            accept_mime = None
            accept_parts = accept_header.split(';')
            accept_mimes = accept_parts[0].split(',')
            for mime in accept_mimes:
                mime = mime.strip()
                if mime in self.content_types:
                    accept_mime = mime.strip()
                    break
            if accept_mime is not None:
                response_content_type = accept_mime
            elif '*/*' not in accept_header:
                raise self._not_acceptable_request_exception()

        if 'application/octet-stream' == response_content_type or '*/*' in response_content_type:
            response_content_type = self.default_content_type
        return self.content_types[response_content_type].dumps(data), response_content_type

    def _get_argantic_handler(self, handler: WebHandler, request: web.Request) -> WebHandler:
        handler_key = self._get_handler_identifier(request)
        if handler_key is None:
            return handler
        try:
            return self._computed_handler[handler_key]
        except KeyError:
            argantic_handler = self._create_handler(handler, request)
            self._computed_handler[handler_key] = argantic_handler
            return argantic_handler

    def _get_handler_identifier(self, request: web.Request) -> Optional[Hashable]:
        resource = request.match_info.route.resource
        if not resource:
            return None
        return request.match_info.route

    def middleware(self) -> WebHandler:
        @web.middleware
        async def argantic_middleware(request: web.Request, handler: WebHandler):
            argantic_handler = self._get_argantic_handler(handler, request)
            return await argantic_handler(request)

        return argantic_middleware
