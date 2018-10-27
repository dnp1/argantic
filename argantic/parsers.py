from typing import Type

from pydantic import BaseModel, ValidationError

from argantic.errors import ArganticValidationError


def parse_model_factory(model: Type[BaseModel]):
    async def parse(data: dict):
        try:
            return model.parse_obj(data)
        except ValidationError as e:
            raise ArganticValidationError(e.errors()) from e

    return parse


def parse_dataclass_factory(data_cls: Type):
    async def parse(data: dict):
        try:
            return data_cls(**data)
        except ValidationError as e:
            raise ArganticValidationError(e.errors()) from e
        except TypeError as e:
            raise ArganticValidationError({'errors': list(e.args)})

    return parse


def parse_ordinary_type_factory(tp: Type):
    async def parse(data: dict):
        if type(data) != tp:
            raise ArganticValidationError({'error': f'{type(data)} value passed, expecting {tp}'})
        return data

    return parse
