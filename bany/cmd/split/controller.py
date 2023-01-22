"""
Itemize and split a receipt between people.
"""
import dataclasses
from argparse import ArgumentParser
from argparse import Namespace

from bany.cmd.base import Controller as BaseController
from bany.core.settings import Settings


@dataclasses.dataclass(frozen=True)
class Controller(BaseController):
    """
    A class to orchestrate the main logic.
    """

    environ: Settings
    options: Namespace

    @classmethod
    def add_args(cls, parser: ArgumentParser):
        group = parser.add_argument_group("split")
        return group

    def __call__(self):
        pass
