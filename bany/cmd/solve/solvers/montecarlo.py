"""
Solve the bucket problem, but do not allow moving values between buckets.
In this version of the problem, we can only add to buckets and an optimal solution may not exist.
This solution uses Monte Carlo and may not offer the optimal allocation of amounts into buckets, but gets close.
"""
import dataclasses

import numpy as np

from bany.cmd.solve.solvers.basesolver import BucketSolver
from bany.cmd.solve.solvers.bucketdata import BucketData
from bany.cmd.solve.solvers.bucketdata import BucketSystem


@dataclasses.dataclass()
class BucketSolverConstrainedMonteCarlo(BucketSolver):
    """
    Solve the bucket problem, but do not allow moving values between buckets.
    In this version of the problem, we can only add to buckets and an optimal solution may not exist.
    This solution uses Monte Carlo and may not offer the optimal allocation of amounts into buckets, but gets close.
    """

    accept: int
    reject: int

    @classmethod
    def solve(
        cls, system: BucketSystem, step_size: float = 0.01, max_steps: int = None
    ) -> "BucketSolverConstrainedMonteCarlo":
        """
        Solve the bucket problem.
        """
        total_added = 0
        accept, reject = 0, 0
        max_steps = max_steps if max_steps is not None else int(1000 * system.amount_to_add)

        n_values = np.copy(system.current.values)
        p_vector = cls._make_p_vector(n_values, system.optimal.values)

        for i in range(max_steps):
            if np.sum(p_vector) <= 0.0:
                break
            if total_added >= (system.amount_to_add - step_size):
                break

            b_index = np.random.randint(0, len(p_vector))
            p_value = p_vector[b_index]

            if np.random.random() <= p_value:
                accept += 1
                total_added += step_size
                n_values[b_index] += step_size
                p_vector = cls._make_p_vector(n_values, system.optimal.values)
            else:
                reject += 1

        p_vector = cls._make_p_vector(n_values, system.optimal.values)
        n_values = n_values - system.current.values

        remaining = system.amount_to_add - np.sum(n_values)

        if abs(remaining) > 2 * step_size or remaining < 0:
            raise ValueError(f"remaining: {remaining}")
        elif remaining > 0:
            n_values[np.argmax(p_vector)] += remaining

        result_delta = BucketData.from_values(values=n_values)
        result_total = BucketData.from_values(values=system.current.values + result_delta.values)

        return cls(system=system, accept=accept, reject=reject, result_delta=result_delta, result_total=result_total)

    @staticmethod
    def _make_p_vector(current: np.array, optimal: np.array) -> np.array:
        """Get the current probability to add to each bucket"""
        p_vector = optimal - current
        p_vector[np.isnan(p_vector)] = 0.0
        p_vector = np.where(p_vector > 0, p_vector, 0.0)
        p_length = np.linalg.norm(p_vector, 1)

        if p_length > 0:
            p_vector = p_vector / p_length
        else:
            p_vector = np.zeros_like(current)

        return p_vector
