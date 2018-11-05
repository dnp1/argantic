from abc import ABCMeta, abstractmethod
from typing import Callable, Union, Dict, Type, Optional

from aiohttp import web
from attr import dataclass

from argantic.util import multi_dict_to_dict
from argantic.errors import ArganticUnsupportedContentType, ArganticDecodeError


@dataclass
class FormatSupport:
    mime_type: str
    dumps: Callable[[object], str]
    loads: Callable[[Union[str, bytes, bytearray]], object]
    parse_error: Type[Exception]


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

    def __init__(self, content_types: Dict[str, FormatSupport], default_content_type: Optional[str] = None):
        self._default_content_type = default_content_type
        self._content_types = content_types

    async def loads(self, request: web.Request):
        raw = await request.text()
        try:
            content_type = request.content_type or self._default_content_type
            if not content_type:
                raise ArganticUnsupportedContentType()
            mime_type_support = self._content_types[content_type]
        except KeyError as e:
            raise ArganticUnsupportedContentType() from e

        try:
            return mime_type_support.loads(raw)
        except mime_type_support.parse_error as e:
            raise ArganticDecodeError() from e
