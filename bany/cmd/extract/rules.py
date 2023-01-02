"""
Rules for extraction information from a PDF.
"""
import calendar
import itertools
import pathlib
import re
import uuid
from datetime import date
from re import Match
from re import Pattern
from typing import Any

import yaml
from moneyed import Money
from moneyed import USD
from pydantic import BaseModel
from pydantic import parse_obj_as
from pydantic import validator


CONTEXT = {
    "MONTHS": r"(?:%s)"
    % "|".join(itertools.chain(filter(bool, calendar.month_abbr), filter(bool, calendar.month_name))),
    "AMOUNT": r"(?:[\d,]+\.\d\d?)",
    "NUMBER": r"(?:\d+\.\d\d?)",
}


SKIP = re.compile(f"{uuid.uuid4()}")


class Rule(BaseModel):
    flags: int = re.I | re.X
    regex: Pattern = SKIP
    match: Match | None = None
    group: str = "UNKNOWN"
    transform: str = "{VALUE}"
    pages: set[int] | None = None

    class Config:
        extra = "forbid"
        validate_assignment = True
        arbitrary_types_allowed = True

    # noinspection PyMethodParameters
    @validator("regex", pre=True, always=True)
    def _validate_regex(cls, value: str | Pattern, values: dict[str, Any]):
        if isinstance(value, str):
            return re.compile(value.format(**CONTEXT), values["flags"])
        else:
            return value


class DateRule(Rule):
    transform: str = "{DATE}"
    value: date | None = None


class AmountRule(Rule):
    total: bool = False
    inflow: bool = False
    transform: str = "{MONEY}"
    value: Money | int | None = None

    # noinspection PyMethodParameters
    @validator("value", pre=True, always=True)
    def _validate_value(cls, value: Money | int | None):
        if isinstance(value, int):
            return Money(amount=value, currency=USD)
        return value


class TransactionRule(BaseModel):
    budget: str
    account: str
    payee: str | None = None
    category: str | None = None
    memo: str | None = None
    color: str | None = None
    amount: int | str | tuple[int, int, str]
    date: date | str | tuple[int, int, str]

    # noinspection PyMethodParameters
    @validator("date", pre=True, always=True)
    def _validate_date(cls, value: Money | int | None):
        if isinstance(value, str):
            return 0, 0, value
        return value

    # noinspection PyMethodParameters
    @validator("amount", pre=True, always=True)
    def _validate_amount(cls, value: Money | int | None):
        if isinstance(value, str):
            return 0, 0, value
        return value


class Rules(BaseModel):
    dates: dict[str | tuple[int, int, str], DateRule]
    amounts: dict[str | tuple[int, int, str], AmountRule]
    transactions: tuple[TransactionRule, ...] = ()


YML: frozenset[str] = frozenset((".yml", ".yaml"))


def get_rules(path: pathlib.Path) -> Rules:
    if (ext := path.suffix.lower()) in YML:
        return get_rules_from_yml(path)
    else:
        raise NotImplementedError(f"can not load rules from {ext}")


def get_rules_from_yml(path: pathlib.Path) -> Rules:
    with path.open("r") as stream:
        data = yaml.safe_load(stream)
        return parse_obj_as(Rules, data)
