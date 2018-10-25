from abc import ABCMeta, abstractmethod
from typing import NamedTuple, Callable, Union, Dict

from aiohttp import web

from argantic._util import multi_dict_to_dict
from argantic.errors import ArganticUnsupportedContentType


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
            mime_type_support = self.content_types[request.content_type]
            return mime_type_support.loads(raw)
        except KeyError as e:
            raise ArganticUnsupportedContentType() from e

