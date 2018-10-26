from typing import Union


class ArganticError(Exception):
    pass


class ArganticClientError(ArganticError):
    pass


class ArganticServerError(ArganticError):
    pass


class ArganticUnsupportedContentType(ArganticClientError):
    pass


class ArganticIncompatibleType(ArganticClientError):
    pass


class ArganticUnsupportedClassAnnotated(ArganticServerError):
    pass


class ArganticValidationError(ArganticClientError):
    def __init__(self, report: Union[dict, list]):
        self.report = report
