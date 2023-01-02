"""
Extract transactions from a file.
"""
import dataclasses
import pathlib
from collections.abc import Iterator

from bany.ynab.api import YNAB
from bany.ynab.transaction import Transaction


@dataclasses.dataclass()
class Extractor:
    """
    Extract transactions from a file.
    """

    ynab: YNAB

    @classmethod
    def create(cls, config: pathlib.Path, **kwargs) -> "Extractor":
        raise NotImplementedError

    def extract(self, path: pathlib.Path) -> Iterator[Transaction]:
        raise NotImplementedError
