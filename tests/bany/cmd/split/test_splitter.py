"""
Unit tests for module.
"""

import dataclasses
import logging

import pandas as pd
import pytest
from moneyed import Money
from moneyed import USD
from pandas.testing import assert_frame_equal

import bany.core.config
from bany.cmd.split.splitter import Split
from bany.cmd.split.splitter import Splitter
from bany.cmd.split.splitter import Tax
from bany.cmd.split.splitter import Tip


def _m(*args) -> Money:
    return Money(*args, USD)


@pytest.mark.parametrize(
    "inputs,expected",
    [
        (dict(amount=1, creditors="A", debtors="A"), dict(amount=_m(1.00))),
    ],
)
def test_create_split(inputs: dict, expected: dict):
    observed = Split(**inputs)
    for key, value in expected.items():
        assert getattr(observed, key) == value


@dataclasses.dataclass()
class CheckSplitTableTestData:
    splits: tuple[tuple[Split, tuple[Tax | Tip, ...]], ...]
    expect: pd.DataFrame


def test_splits_table_correct():
    splitter = Splitter()
    splitter.split(Split(amount=1, creditors="A", debtors="A"), Tax(rate=0.5, payee="SalesTax"))
    splitter.split(Split(amount=5, creditors="B", debtors="B"), Tip(amount=2, category="Unknown"))
    expect = pd.DataFrame(
        [
            {"amount": _m(1.00), "A.$": _m(1.00), "B.$": _m(0.00), "rate": 0.0},
            {"amount": _m(0.50), "A.$": _m(0.50), "B.$": _m(0.00), "rate": 0.5},
            {"amount": _m(5.00), "A.$": _m(0.00), "B.$": _m(5.00), "rate": 0.0},
            {"amount": _m(2.00), "A.$": _m(0.00), "B.$": _m(2.00), "rate": 0.4},
        ]
    )

    logging.info("observed\n%s\n", splitter.frame)
    logging.info("expected\n%s\n", expect)
    subset = splitter.frame.loc[:, expect.columns]
    assert_frame_equal(subset, expect)


def test_splits_only_credit():
    splitter = Splitter()
    splitter.split(Split(amount=2, creditors="A", debtors="B", payee="Costco", category="X"))
    splitter.split(Split(amount=2, creditors="A", debtors="B", payee="Costco", category="X"))
    splitter.split(Split(amount=2, creditors="A", debtors="B", payee="Costco", category="Y"))
    splitter.split(Split(amount=2, creditors="A", debtors="B", payee="Costco", category="Y"))
    logging.info("observed\n%s\n", splitter.frame)
    logging.info("observed\n%s\n", splitter.summary)


def setup_module():
    bany.core.config.pandas()
