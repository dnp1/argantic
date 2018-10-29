from abc import ABCMeta, abstractmethod
from typing import Callable, Union, Dict, Type, List

from aiohttp import web
from attr import dataclass

from argantic.util import multi_dict_to_dict
from argantic.errors import ArganticUnsupportedContentType


@dataclass
class FormatSupport:
    mime_type: str
    dumps: Callable[[object], str]
    loads: Callable[[Union[str, bytes, bytearray]], object]


class AbstractLoader(metaclass=ABCMeta):
    can_return_list = False

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
    can_return_list = True

    def __init__(self, content_types: Dict[str, FormatSupport]):
        self.content_types = content_types

    async def loads(self, request: web.Request):
        raw = await request.text()
        try:
            mime_type_support = self.content_types[request.content_type]
            return mime_type_support.loads(raw)
        except KeyError as e:
            raise ArganticUnsupportedContentType() from e


DATA_SOURCE = Type[AbstractLoader]
DATA = Union[List, Dict]
