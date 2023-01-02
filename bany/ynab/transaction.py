import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


NS = uuid.UUID("b9b024c9-e918-4447-9b75-2b340535d49e")


class Transaction(BaseModel):
    budget_id: str = Field(exclude=True, repr=False)
    budget_name: str | None = Field(default=None, exclude=True)

    account_id: str = Field(repr=False)
    account_name: str | None = Field(default=None, exclude=True)

    payee_id: str | None = None
    payee_name: str | None = None

    category_id: str | None = None
    category_name: str | None = Field(default=None, exclude=True)

    date: date
    amount: int

    memo: str | None = None
    flag_color: Literal["red", "blue", "green", "yellow"] | None = None
    cleared: str | None = None
    approved: bool = False

    import_index: int = Field(default=0, exclude=True, repr=False)
    import_id: str | None = Field(repr=False)

    class Config:
        extra = "forbid"
        allow_mutation = False

    # noinspection PyMethodParameters
    @validator("import_id", pre=True, always=True)
    def _set_import_id(cls, v, values):
        v = v if v is not None else "{account_id}:{date}:{amount}:{payee_name}:{import_index}"
        return str(uuid.uuid5(NS, v.format(**values)))

    def __hash__(self):
        return hash(self.import_id)


class Transactions(BaseModel):
    transactions: list[Transaction]

    class Config:
        allow_mutation = False
