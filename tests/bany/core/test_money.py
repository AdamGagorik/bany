"""
Unit tests for module.
"""
import pytest

import bany.core.money


@pytest.mark.parametrize(
    "values,decimals,width,expected_str",
    [
        ([0.01], 2, 4, "0.01"),
        ([0.02], 2, 5, " 0.02"),
        ([0.03, 0.04], 2, 4, "0.03, 0.04"),
        ([1e-10], 2, 4, "0.00"),
    ],
)
def test_moneyfmt(values: list, decimals: int, width: int, expected_str: str):
    observed_str = bany.core.money.moneyfmt(*values, width=width, decimals=decimals)
    assert observed_str == expected_str
