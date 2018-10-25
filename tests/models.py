from typing import List

from pydantic import BaseModel, EmailStr, Decimal
from pydantic.dataclasses import dataclass


class Model(BaseModel):
    given_name: str
    family_name: str
    age: int
    preferences: List[str]


@dataclass
class DataCls:
    seller_email: EmailStr
    product_name: str
    price: Decimal
