from collections.abc import Callable

from bany.cmd.solve.solvers.constrained import BucketSolverConstrained
from bany.cmd.solve.solvers.montecarlo import BucketSolverConstrainedMonteCarlo
from bany.cmd.solve.solvers.unconstrained import BucketSolverSimple

SOLVERS: dict[str, Callable] = {
    "montecarlo": lambda step_size: {"solver": BucketSolverConstrainedMonteCarlo, "step_size": step_size},
    "constrained": lambda step_size: {"solver": BucketSolverConstrained},
    "unconstrained": lambda step_size: {"solver": BucketSolverSimple},
}
