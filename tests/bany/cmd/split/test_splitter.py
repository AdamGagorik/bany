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


def _m(*args) -> Money:
    return Money(*args, USD)


@pytest.mark.parametrize(
    "inputs,expected",
    [
        (dict(Amount=1, Creditors="A", Debtors="A"), dict(Amount=_m(1.00))),
    ],
)
def test_create_split(inputs: dict, expected: dict):
    observed = Split(**inputs)
    for key, value in expected.items():
        assert getattr(observed, key) == value


@dataclasses.dataclass()
class CheckSplitTableTestData:
    splits: tuple[dict, ...]
    expect: pd.DataFrame


@pytest.mark.parametrize(
    "testData",
    [
        CheckSplitTableTestData(
            splits=(
                dict(Amount=1, Creditors="A", Debtors="A", taxes=dict(SalesTax=0.50)),
                dict(Amount=5, Creditors="B", Debtors="B", tips=[2]),
            ),
            expect=pd.DataFrame(
                [
                    {"Amount": _m(1.00), "A.$": _m(1.00), "B.$": _m(0.00), "Rate": 0.0},
                    {"Amount": _m(0.50), "A.$": _m(0.50), "B.$": _m(0.00), "Rate": 0.5},
                    {"Amount": _m(5.00), "A.$": _m(0.00), "B.$": _m(5.00), "Rate": 0.0},
                    {"Amount": _m(2.00), "A.$": _m(0.00), "B.$": _m(2.00), "Rate": 0.4},
                ]
            ),
        ),
    ],
)
def test_splits_table_correct(testData: CheckSplitTableTestData):
    splitter = Splitter()
    for kwargs in testData.splits:
        splitter.append(**kwargs)

    logging.info("observed\n%s\n", splitter.frame)
    logging.info("expected\n%s\n", testData.expect)
    subset = splitter.frame.loc[:, testData.expect.columns]
    assert_frame_equal(subset, testData.expect)


def setup_module():
    bany.core.config.pandas()
