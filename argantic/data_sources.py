from enum import Enum, auto


class DataSource(Enum):
    RouteParams = auto()
    QueryParams = auto()
    Body = auto()
