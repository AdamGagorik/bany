"""
Extract transactions from a PDF file using regular expressions.
"""
import dataclasses
import logging
import pathlib
import re
from collections.abc import Iterator
from datetime import date
from re import Match
from typing import cast

import dateutil.parser
import pandas as pd
import pdfplumber
from moneyed import Money
from moneyed import USD

from bany.cmd.extract.extractors.base import Extractor as BaseExtractor
from bany.cmd.extract.rules import AmountRule
from bany.cmd.extract.rules import DateRule
from bany.cmd.extract.rules import get_rules
from bany.cmd.extract.rules import Rule
from bany.cmd.extract.rules import Rules
from bany.cmd.extract.rules import SKIP
from bany.core.logger import logger
from bany.core.logger import logline
from bany.ynab.transaction import Transaction


@dataclasses.dataclass()
class Extractor(BaseExtractor):
    """
    Extract transactions from a PDF file using regular expressions.
    """

    rules: Rules
    state: dict = dataclasses.field(default_factory=dict)

    @classmethod
    def create(cls, config: pathlib.Path, **kwargs) -> "Extractor":
        return cls(rules=get_rules(path=config), **kwargs)

    def extract(self, path: pathlib.Path) -> Iterator[Transaction]:
        self.state = {}
        texts = self._get_text_from_pdf(path=path)

        for i, text in enumerate(texts):
            logline(level=logging.DEBUG)
            logger.debug("page %d\n%s", i, text)

        dates = {}
        for key, rule in self.rules.dates.items():
            for i, j, updated in self._get_matches_for_text(rule, texts):
                dates[(i, j, key)] = updated

        amounts = {}
        for key, rule in self.rules.amounts.items():
            for i, j, updated in self._get_matches_for_text(rule, texts):
                amounts[(i, j, key)] = updated

        dates = self._make_frame(dates)
        amounts = self._make_frame(amounts)

        if not dates.empty:
            logline()
            logger.info("dates:\n%s", dates.loc[:, ~dates.columns.isin({"regex", "match"})])

        if not amounts.empty:
            self._display_matches(amounts)

        yield from self._get_transactions_for_matches(dates, amounts)

    @staticmethod
    def _display_matches(amounts: pd.DataFrame, exclude_cols: set = frozenset(("regex", "match"))):
        for group_index, group in amounts.groupby(by="group"):
            logger.info("amounts:\n%s", group.loc[:, ~group.columns.isin(exclude_cols)])

    @staticmethod
    def _make_frame(rules: dict[tuple[int, int, str], Rule]) -> pd.DataFrame:
        return pd.DataFrame(
            (rule.dict() for rule in rules.values()),
            index=pd.MultiIndex.from_tuples(tuples=list(rules.keys()), names=("page", "match", "key")),
        )

    @staticmethod
    def _get_text_from_pdf(path: pathlib.Path) -> tuple[str]:
        with pdfplumber.open(path) as pdf:
            return tuple(page.extract_text() for page in pdf.pages)

    def _get_matches_for_text(self, rule: Rule, texts: tuple[str]) -> tuple[int, int, Rule]:
        count = 0

        if rule.regex is SKIP:
            if isinstance(rule, DateRule) and rule.value is not None:
                count += 1
                match = re.match(f"(?P<DATE>{re.escape(str(rule.value))})", f"{rule.value}")
                yield 0, 0, rule.copy(update=dict(value=self._get_match_as_date(rule, match), match=match))
            else:
                raise NotImplementedError(type(rule))
        else:
            for i, text in enumerate(texts):
                if rule.pages is None or i in rule.pages:
                    for j, match in enumerate(rule.regex.finditer(text)):
                        if isinstance(rule, DateRule):
                            count += 1
                            yield i, j, rule.copy(update=dict(value=self._get_match_as_date(rule, match), match=match))
                        elif isinstance(rule, AmountRule):
                            count += 1
                            yield i, j, rule.copy(update=dict(value=self._get_match_as_money(rule, match), match=match))
                        else:
                            raise NotImplementedError(type(rule))
        if count == 0:
            self._log_block("_get_matches_for_text", "no matches! %s %s", type(rule).__name__, rule.regex.pattern)

    @staticmethod
    def _get_match_as_date(rule: DateRule, match: Match) -> date:
        return dateutil.parser.parse(rule.transform.format(**match.groupdict())).date()

    @staticmethod
    def _get_match_as_money(rule: AmountRule, match: Match) -> Money:
        value = rule.transform.format(**match.groupdict()).replace(",", "")
        money = Money(amount=value, currency=USD)
        if rule.inflow:
            return money
        else:
            return -1 * money

    def _get_transactions_for_matches(self, dates: pd.DataFrame, amounts: pd.DataFrame) -> Iterator[Transaction]:
        for rule in self.rules.transactions:
            if (amount := self._lookup_amount(rule.amount, amounts)) is not None:
                budget_id = self.ynab.budget_id(rule.budget)
                transaction = Transaction(
                    ####################################################################################################
                    # budget
                    ####################################################################################################
                    budget_id=budget_id,
                    budget_name=rule.budget,
                    ####################################################################################################
                    # account
                    ####################################################################################################
                    account_id=self.ynab.account_id(budget_id, rule.account),
                    account_name=rule.account,
                    ####################################################################################################
                    # payee
                    ####################################################################################################
                    payee_id=None if rule.payee is None else self.ynab.payee_id(budget_id, cast(str, rule.payee)),
                    payee_name=rule.payee,
                    ####################################################################################################
                    # category
                    ####################################################################################################
                    category_id=(
                        None if rule.category is None else self.ynab.category_id(budget_id, cast(str, rule.category))
                    ),
                    category_name=rule.category,
                    ####################################################################################################
                    # transaction
                    ####################################################################################################
                    date=self._lookup_date(rule.date, dates),
                    amount=amount.get_amount_in_sub_unit() * 10,
                    ####################################################################################################
                    # extras
                    ####################################################################################################
                    flag_color=rule.color,
                    memo=rule.memo,
                )
                yield transaction

    def _lookup_date(self, key: date | tuple[int, int, str] | None, dates: pd.DataFrame) -> date:
        if key is None:
            return date.today()
        elif isinstance(key, date):
            return key
        elif isinstance(key, tuple):
            try:
                return dates.loc[key, "value"]
            except KeyError:
                self._log_block("_lookup_date", "[%11s] KeyError: %s", "dates".center(11, "-"), key)
                return date(1970, 1, 1)
        else:
            raise NotImplementedError(type(key))

    def _lookup_amount(self, key: int | tuple[int, int, str], amounts: pd.DataFrame) -> Money | None:
        if isinstance(key, Money):
            return key
        elif isinstance(key, tuple):
            try:
                return amounts.loc[key, "value"]
            except KeyError:
                self._log_block("_lookup_date", "[%11s] KeyError: %s", "amounts".center(11, "-"), key)
                return
        else:
            raise NotImplementedError(type(key))

    def _log_block(self, key: str, msg: str, *args, line: int = logging.INFO, level: int = logging.ERROR):
        if not self.state.get(key, False):
            logline(level=line)
            self.state[key] = True
        logger.log(level, msg, *args)
