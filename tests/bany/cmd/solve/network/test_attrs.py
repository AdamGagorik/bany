"""
Unit tests for module.
"""
import dataclasses

import pytest

from bany.cmd.solve.network.attrs import DISPLAY_INP
from bany.cmd.solve.network.attrs import node_attrs


def test_subset_default():
    observed = list(node_attrs.subset())
    expected = [getattr(node_attrs, f.name) for f in dataclasses.fields(node_attrs)]
    assert expected == observed


def test_subset_given_name():
    observed = list(node_attrs.subset(name="column"))
    expected = [getattr(node_attrs, f.name).column for f in dataclasses.fields(node_attrs)]
    assert expected == observed


def test_subset_given_mask():
    observed = list(node_attrs.subset(filters=DISPLAY_INP))
    expected = [getattr(node_attrs, f.name) for f in dataclasses.fields(node_attrs)]
    expected = [f for f in expected if f.filters & DISPLAY_INP]
    assert expected == observed


def test_subset_given_unknown_raises():
    with pytest.raises(ValueError, match="missing"):
        list(node_attrs.subset("missing"))


def test_subset_given_unknown_ignores_when_not_strict():
    observed = list(node_attrs.subset("missing", strict=False))
    assert not observed
