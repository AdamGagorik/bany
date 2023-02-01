"""
Itemize and split a receipt between people.
"""
import dataclasses
import sys
from argparse import ArgumentParser
from argparse import Namespace
from typing import Any

import pandas as pd
from cmd2 import Cmd
from cmd2 import Cmd2ArgumentParser
from cmd2 import CommandSet
from cmd2 import Statement
from cmd2 import with_argparser
from cmd2 import with_default_category
from rich.console import Console
from rich.prompt import Confirm

from bany.cmd.base import Controller as BaseController
from bany.cmd.split.splitter import Split
from bany.cmd.split.splitter import Splitter
from bany.cmd.split.splitter import Tax
from bany.cmd.split.splitter import Tip
from bany.core.settings import Settings


class App(Cmd):
    """
    This is a simple app to try out the cmd2 module.
    """

    def __init__(self):
        super().__init__(allow_cli_args=False, shortcuts={"?": "help"}, command_sets=[SplitTransactions()])
        del Cmd.do_py
        del Cmd.do_ipy
        del Cmd.do_edit
        del Cmd.do_shell
        del Cmd.do_macro
        del Cmd.do_alias
        del Cmd.do_run_script
        del Cmd.do_run_pyscript
        self.rich_stderr = Console(stderr=True)
        self.rich_stdout = Console(file=self.stdout)

    def poutput(self, msg: Any = "", *, end: str = "\n") -> None:
        try:
            self.rich_stdout.print(f"{msg}{end}".removesuffix("\n"))
        except BrokenPipeError:
            if self.broken_pipe_warning:
                self.rich_stderr.print(self.broken_pipe_warning.removesuffix("\n"))

    def pexcept(self, msg: Any, *, end: str = "\n", apply_style: bool = True) -> None:
        if self.debug and sys.exc_info() != (None, None, None):
            self.rich_stderr.print_exception(show_locals=True)
        else:
            super().pexcept(msg, end=end, apply_style=apply_style)


@with_default_category("My Category")
class SplitTransactions(CommandSet):
    """
    Manage a list of split transactions.
    """

    def __init__(self):
        super().__init__()
        self.splitter = Splitter()

    def do_tax(self, _: Statement):
        """
        Add a tax to the previous split.
        """
        self.splitter.tax(Tax(Rate=0.06, Payee="SalesTax"))

    def do_tip(self, _: Statement):
        """
        Add a tip to the previous split.
        """
        self.splitter.tip(Tip(Amount=5.00, Category="TipA"))

    def do_show(self, _: Statement):
        """
        Show the current split transactions.
        """
        self._display_frame()

    def do_split(self, _: Statement):
        """
        Add a split transaction with associated tips and taxes.
        """
        self.splitter.split(
            Split(
                Amount=1.99,
                Payee="A",
                Category="Food",
                Creditors="Ethan",
                Debtors={"Adam": 1, "Ethan": 1},
            ),
        )
        self._display_frame()

    def do_clear(self, _: Statement):
        """
        Remove all split transactions.
        """
        if not self.splitter.splits:
            self._cmd.perror("no transactions to delete!")
            return

        if Confirm.ask("Remove all transactions?"):
            self.splitter.splits = []
            self._cmd.poutput("[red underline]all transactions removed!")

    _delete_parser = Cmd2ArgumentParser(description="Remove specific split transactions.")
    _delete_parser.add_argument(
        "--groups", type=int, nargs="*", required=True, help="delete all split transactions for group?"
    )

    @with_argparser(_delete_parser)
    def do_delete(self, opts: Namespace):
        if not self.splitter.splits:
            self._cmd.perror("no transactions to delete!")
            return

        if opts.groups is not None:
            subset = self.splitter.frame.loc[self.splitter.frame["Group"].isin(opts.groups), :]
            if not subset.empty:
                self._display_frame(subset)
                if Confirm.ask("Remove transactions for group?"):
                    self.splitter.remove(*opts.groups)
                    self._display_frame()
            else:
                self._cmd.perror(f"no transactions to delete with group == {opts.group}!")
                return
        else:
            self._cmd.perror(self._delete_parser.format_help())

    def _display_frame(self, frame: pd.DataFrame | None = None):
        if frame is None:
            if self.splitter.splits:
                frame = self.splitter.frame
            else:
                self._cmd.perror("no transactions to display")
                return

        self._cmd.poutput(frame)


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
        raise SystemExit(App().cmdloop())
