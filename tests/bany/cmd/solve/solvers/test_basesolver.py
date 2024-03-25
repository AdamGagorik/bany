"""
Unit tests for module.
"""

import pytest

import bany.cmd.solve.solvers.basesolver
import bany.cmd.solve.solvers.bucketdata


def test_base_not_implemented():
    with pytest.raises(NotImplementedError):
        system = bany.cmd.solve.solvers.bucketdata.BucketSystem.create(1, [1, 1], [1, 1])
        bany.cmd.solve.solvers.basesolver.BucketSolver.solve(system)
