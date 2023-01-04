from collections.abc import Callable

from .constrained import BucketSolverConstrained
from .montecarlo import BucketSolverConstrainedMonteCarlo
from .unconstrained import BucketSolverSimple

SOLVERS: dict[str, Callable] = {
    "montecarlo": lambda step_size: dict(solver=BucketSolverConstrainedMonteCarlo, step_size=step_size),
    "constrained": lambda step_size: dict(solver=BucketSolverConstrained),
    "unconstrained": lambda step_size: dict(solver=BucketSolverSimple),
}
