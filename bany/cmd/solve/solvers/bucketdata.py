"""
Data structures for solvers for the bucket problem.
"""
import dataclasses
import logging

import numpy as np
from numpy.typing import ArrayLike

from bany.core.money import moneyfmt


@dataclasses.dataclass(frozen=True)
class BucketData:
    """
    A container for a set of bucket data, such as the amount in each bucket.
    """

    # The total amount in this set of buckets
    amount: float
    # The value in each bucket of this set
    values: np.array
    # The ratio of values over the bucket set
    ratios: np.array
    # The (optional) labels for the buckets
    labels: list

    @classmethod
    def from_values(cls, values: ArrayLike, labels: list = None, allow_negative_values: bool = False) -> "BucketData":
        """
        Create bucket data set from list of known values.
        """
        labels = labels if labels is not None else list(range(len(values)))
        values: np.array = np.asanyarray(values, dtype=float)

        if not allow_negative_values and np.any(values < 0):
            raise ValueError("negative values in bucket data!")

        amount = float(np.sum(values))
        if amount > 0:
            ratios = values / amount
        else:
            ratios = np.zeros_like(values)
        return cls(amount, values, ratios, labels)

    @classmethod
    def from_ratios(cls, ratios: ArrayLike, amount: float, labels: list = None) -> "BucketData":
        """
        Create bucket data set from list of known ratios and desired total amount.
        """
        if amount < 0:
            raise ValueError("negative amount in bucket data!")

        ratios = np.asanyarray(ratios)
        if np.any(ratios < 0):
            raise ValueError("negative ratios in bucket data!")

        if amount > 0:
            if np.all(ratios <= 0):
                raise ValueError("all ratios are zero with positive amount!")

        labels = labels if labels is not None else list(range(len(ratios)))
        ratios = ratios / np.linalg.norm(ratios, 1)
        ratios[np.isnan(ratios)] = 0.0
        values = amount * ratios
        return cls(amount, values, ratios, labels)


@dataclasses.dataclass()
class BucketSystem:
    """
    A container for all the information required to specify the bucket problem.
    """

    amount_to_add: float
    current: BucketData
    optimal: BucketData

    @classmethod
    def create(
        cls, amount_to_add: float, current_values: ArrayLike, optimal_ratios: ArrayLike, labels: list = None
    ) -> "BucketSystem":
        """
        Create a system to solve from the parameters.
        """
        if amount_to_add < 0:
            logging.error("amount_to_add: %s", amount_to_add)
            raise ValueError("amount to add is negative or zero")

        if len(current_values) != len(optimal_ratios):
            logging.error("current_values: len=%s", len(current_values))
            logging.error("optimal_ratios: len=%s", len(optimal_ratios))
            raise ValueError("length mismatch between values and ratios")

        current = BucketData.from_values(values=current_values, labels=labels)
        optimal = BucketData.from_ratios(ratios=optimal_ratios, amount=current.amount + amount_to_add, labels=labels)
        return cls(amount_to_add, current, optimal)

    def __str__(self):
        return rf"""
System
======

                 {'  '.join('{:>10}'.format(v) for v in self.current.labels)}
amount_to_add  : {moneyfmt(self.amount_to_add)}
current.values : {moneyfmt(*self.current.values)}
current.ratios : {moneyfmt(*self.current.ratios, decimals=5)}
current.amount : {moneyfmt(self.current.amount)}

optimal.values : {moneyfmt(*self.optimal.values)}
optimal.ratios : {moneyfmt(*self.optimal.ratios, decimals=5)}
optimal.amount : {moneyfmt(self.optimal.amount)}
"""[
            1:
        ]
