"""
Solve the bucket problem, but do not allow moving values between buckets.
In this version of the problem, we can only add to buckets and an optimal solution may not exist.
"""
import dataclasses
import logging
import typing

import numpy as np
import scipy.optimize

from bany.cmd.solve.solvers.bucketdata import BucketData
from bany.cmd.solve.solvers.bucketdata import BucketSystem
from bany.cmd.solve.solvers.unconstrained import BucketSolverSimple


@dataclasses.dataclass()
class BucketSolverConstrained(BucketSolverSimple):
    """
    Solve the bucket problem, but do not allow moving values between buckets.
    In this version of the problem, we can only add to buckets and an optimal solution may not exist.
    """

    @classmethod
    def solve(cls, system: BucketSystem) -> "BucketSolverConstrained":
        """
        Solve the bucket problem.
        """
        a_matrix = cls._make_a_matrix(system)
        b_vector = cls._make_b_vector(system)
        g_vector = cls._make_g_vector(system)
        opt_func = cls._make_opt_func(system, a_matrix, b_vector)
        opt_cond = cls._make_opt_cond(system, a_matrix, b_vector)

        # noinspection PyTypeChecker
        opt_data = scipy.optimize.minimize(
            opt_func,
            g_vector,
            method="SLSQP",
            bounds=[(0.0, None) for _ in range(len(b_vector))],
            constraints=list(opt_cond),
            options={"disp": False, "ftol": 1e-3},
        )

        if opt_data.success:
            result_delta = BucketData.from_values(values=opt_data.x)
            result_total = BucketData.from_values(values=system.current.values + result_delta.values)
            return cls(
                system=system,
                result_delta=result_delta,
                result_total=result_total,
                a_matrix=a_matrix,
                b_vector=b_vector,
            )
        else:
            logging.error("scipy.optimize.minimize\n%s", opt_data)
            raise RuntimeError("can not solve problem!")

    @staticmethod
    def _make_g_vector(system: BucketSystem) -> np.array:
        """Make g, the intial guess for x"""
        return np.zeros_like(system.current.values)

    # noinspection PyUnusedLocal
    @staticmethod
    def _make_opt_func(system: BucketSystem, a_matrix: np.array, b_vector: np.array) -> typing.Callable:
        """Make the function to optimize"""

        def f(x: np.array):
            y = np.dot(a_matrix, x) - b_vector
            return np.dot(y, y)

        return f

    # noinspection PyUnusedLocal
    @staticmethod
    def _make_opt_cond(
        system: BucketSystem, a_matrix: np.array, b_vector: np.array
    ) -> typing.Generator[dict, None, None]:
        """Make functions to enforce the problem constraints"""
        yield {"type": "eq", "fun": lambda x: x.sum() - system.amount_to_add}
