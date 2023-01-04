"""
Solve the bucket problem, allowing amounts to be removed from existing buckets.
This is a pretty straight forward solution and places no major constrains on the problem.
"""
import dataclasses

import numpy as np

from bany.cmd.solve.solvers.basesolver import BucketSolver
from bany.cmd.solve.solvers.bucketdata import BucketData
from bany.cmd.solve.solvers.bucketdata import BucketSystem


@dataclasses.dataclass()
class BucketSolverSimple(BucketSolver):
    """
    Solve the bucket problem, allowing amounts to be removed from existing buckets.
    This is a pretty straight forward solution and places no major constrains on the problem.
    """

    # The matrix A in the equation Ax = b
    a_matrix: np.array
    # The vector b in the equation Ax = b
    b_vector: np.array

    @classmethod
    def solve(cls, system: BucketSystem) -> "BucketSolverSimple":
        """
        Solve the bucket problem.
        """
        a_matrix = cls._make_a_matrix(system)
        b_vector = cls._make_b_vector(system)
        n_values = np.linalg.solve(a_matrix, b_vector)
        result_delta = BucketData.from_values(values=n_values, allow_negative_values=True)
        result_total = BucketData.from_values(values=system.current.values + result_delta.values)
        return cls(
            system=system, result_delta=result_delta, result_total=result_total, a_matrix=a_matrix, b_vector=b_vector
        )

    @staticmethod
    def _make_a_matrix(system: BucketSystem) -> np.array:
        """Create A"""
        return np.identity(len(system.current.values))

    @staticmethod
    def _make_b_vector(system: BucketSystem) -> np.array:
        """Create b"""
        amount_to_add = system.optimal.amount - system.current.amount
        current_value = system.current.amount
        return (amount_to_add + current_value) * system.optimal.ratios - system.current.values
