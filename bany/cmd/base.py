"""
A class to orchestrate the main logic.
"""
import dataclasses
from argparse import ArgumentParser
from argparse import Namespace

from bany.core.settings import Settings


@dataclasses.dataclass(frozen=True)
class Controller:
    """
    A class to orchestrate the main logic.
    """

    environ: Settings
    options: Namespace

    @classmethod
    def add_args(cls, parser: ArgumentParser):
        raise NotImplementedError

    def __call__(self):
        raise NotImplementedError
