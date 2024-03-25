"""
Unit tests for module.
"""

import logging

import pytest

import bany.cmd.solve.solvers.bucketdata


def test_create_bucket_data_from_values():
    data = bany.cmd.solve.solvers.bucketdata.BucketData.from_values(values=[1, 2, 3, 4, 5])
    assert len(data.labels) == 5
    assert len(data.values) == 5
    assert len(data.ratios) == 5
    assert sum(data.ratios) == pytest.approx(1.0)


def test_create_bucket_data_from_values_raises_on_negative_values():
    with pytest.raises(ValueError, match="negative values"):
        bany.cmd.solve.solvers.bucketdata.BucketData.from_values(values=[1, -1])


def test_create_bucket_data_from_ratios():
    data = bany.cmd.solve.solvers.bucketdata.BucketData.from_ratios(ratios=[1, 1, 1, 1], amount=1)
    assert len(data.labels) == 4
    assert len(data.values) == 4
    assert len(data.ratios) == 4
    assert sum(data.ratios) == pytest.approx(1.0)


def test_create_bucket_data_from_ratios_raises_on_negative_ratios():
    with pytest.raises(ValueError, match="negative ratios"):
        bany.cmd.solve.solvers.bucketdata.BucketData.from_ratios(ratios=[1, -1], amount=1)


def test_create_bucket_data_from_ratios_raises_on_negative_amount():
    with pytest.raises(ValueError, match="negative amount"):
        bany.cmd.solve.solvers.bucketdata.BucketData.from_ratios(ratios=[1, 1], amount=-1)


def test_create_bucket_system():
    system = bany.cmd.solve.solvers.bucketdata.BucketSystem.create(1, [0, 0], [0.5, 0.5])
    logging.debug("system.current: %s", system.current)
    logging.debug("system.optimal: %s", system.optimal)
    assert len(system.current.labels) == 2
    assert len(system.current.values) == 2
    assert len(system.current.ratios) == 2
    assert len(system.optimal.labels) == 2
    assert len(system.optimal.values) == 2
    assert len(system.optimal.ratios) == 2


def test_create_bucket_system_raises_on_wrong_size():
    with pytest.raises(ValueError, match="length mismatch"):
        bany.cmd.solve.solvers.bucketdata.BucketSystem.create(1, [0], [1, 1])


def test_create_bucket_system_raises_on_negative_amount():
    with pytest.raises(ValueError, match="amount to add is negative"):
        bany.cmd.solve.solvers.bucketdata.BucketSystem.create(-1, [0], [1])
