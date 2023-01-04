"""
Unit tests for module.
"""
import logging

import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal

import bany.cmd.solve.solvers.bucketdata
import bany.cmd.solve.solvers.constrained


# noinspection DuplicatedCode
def test_solver_solve_simple():
    system = bany.cmd.solve.solvers.bucketdata.BucketSystem.create(
        amount_to_add=10, current_values=[0, 0], optimal_ratios=[0.5, 0.5]
    )
    logging.debug("\n%s", system)

    solver = bany.cmd.solve.solvers.constrained.BucketSolverConstrained.solve(system)
    logging.debug("\n%s", solver)

    totals = pd.Series(solver.result_total.values)
    assert_series_equal(totals, pd.Series([5.0, 5.0]))


# noinspection DuplicatedCode
def test_solver_solve_all_positive():
    system = bany.cmd.solve.solvers.bucketdata.BucketSystem.create(
        amount_to_add=10, current_values=[10, 90], optimal_ratios=[0.5, 0.5]
    )
    logging.debug("\n%s", system)

    solver = bany.cmd.solve.solvers.constrained.BucketSolverConstrained.solve(system)
    logging.debug("\n%s", solver)

    assert np.all(solver.result_delta.values >= 0)
