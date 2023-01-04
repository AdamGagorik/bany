"""
A base class for solutions to the bucket problem.
"""
import dataclasses

from bany.cmd.solve.solvers.bucketdata import BucketData
from bany.cmd.solve.solvers.bucketdata import BucketSystem
from bany.core.money import moneyfmt


@dataclasses.dataclass()
class BucketSolver:
    """
    A base class for solutions to the bucket problem.
    """

    # The input parameters
    system: BucketSystem
    # The amounts to add to each bucket
    result_delta: BucketData
    # The amounts in each bucket after adding the results
    result_total: BucketData

    @classmethod
    def solve(cls, system: BucketSystem, **kwargs) -> "BucketSolver":
        """
        Solve the bucket problem.
        """
        raise NotImplementedError

    def __str__(self):
        return rf"""
{self.__class__.__name__}
{'=' * len(self.__class__.__name__)}

                 {'  '.join('{:>10}'.format(v) for v in self.system.current.labels)}
delta.values   : {moneyfmt(*self.result_delta.values)}
delta.ratios   : {moneyfmt(*self.result_delta.ratios, decimals=5)}
delta.amount   : {moneyfmt(self.result_delta.amount)}

total.values   : {moneyfmt(*self.result_total.values)}
total.ratios   : {moneyfmt(*self.result_total.ratios, decimals=5)}
total.amount   : {moneyfmt(self.result_total.amount)}

differ.amount  : {moneyfmt(self.result_delta.amount - self.system.amount_to_add)}
differ.ratios  : {moneyfmt(*(self.result_total.ratios - self.system.optimal.ratios), decimals=5)}
"""[
            1:
        ]
