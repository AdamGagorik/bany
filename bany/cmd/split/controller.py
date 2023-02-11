"""
Itemize and split a receipt between people.
"""
import dataclasses
import re
import sys
import textwrap
from argparse import Action
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
from moneyed import Money
from moneyed import USD
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


class KwargsAction(Action):
    """
    Parse value of the form key = numeric expression.
    Store the result inside a dictionary called dest.
    """

    def __call__(self, parser: ArgumentParser, namespace: Namespace, values: list[str], option_string: str = None):
        """
        Parse the values expression and update the destination.
        """
        lut = getattr(namespace, self.dest, {})
        lut = lut if lut is not None else {}

        for expr in self._ensure_comma(" ".join(map(str.strip, values))).split(","):
            # expression should be of the form key=value
            if expr.count("=") > 1:
                raise ValueError(f"multiple = sign found in expr! {option_string} {expr}")

            # expression should be of the form key=value
            if expr.count("=") != 1:
                raise ValueError(f"missing = sign in expr! {option_string} {expr}")

            key, value = map(str.strip, expr.split("="))

            # value should not be empty or missing
            if not value:
                raise ValueError(f"missing value after = sign! {option_string} {expr}")

            # key must not already be defined
            if key in lut:
                raise KeyError(f"duplicate key for {option_string} {expr}")

            # substitute in previous values
            for other in lut:
                value = str(value).replace(other, str(lut[other]))

            value = self._safe_eval(value)

            # value must be a number
            if not isinstance(value, (float, int)):
                raise TypeError(f"expecting int or float for {option_string} {expr}")

            # value should be positive definite
            if not value >= 0:
                raise ValueError(f"expecting positive definite value for {option_string} {expr}")

            lut[key] = value
            setattr(namespace, self.dest, lut)

    _REGEX_INSERT_COMMA = re.compile(r"(\d)\s*([a-zA-Z])")

    def _ensure_comma(self, expression: str) -> str:
        """
        Turn `A=1 B=2` into `A=1, B=2`.
        """
        return self._REGEX_INSERT_COMMA.sub(r"\g<1>, \g<2>", expression)

    @staticmethod
    def _safe_eval(expression: str) -> int | float:
        """
        Evaluate simple math expression.
        """
        # value must only contain numbers and operations
        for char in expression:
            if char not in "0123456789+-*(). /":
                raise ValueError(f"invalid character in value: {char}")

        # disable all builtin names in for value
        code = compile(expression, "<string>", "eval")
        if code.co_names:
            raise NameError("Use of names not allowed")

        return eval(expression, {"__builtins__": None}, {})


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
        self.splitter.tax(Tax(rate=0.06, payee="SalesTax"))

    def do_tip(self, _: Statement):
        """
        Add a tip to the previous split.
        """
        self.splitter.tip(Tip(amount=5.00, category="TipA"))

    def do_show(self, _: Statement):
        """
        Show the current split transactions.
        """
        self._display_frame()

    _split_parser = Cmd2ArgumentParser(
        description="Add a split transaction with associated tips and taxes.",
        epilog=textwrap.dedent(
            # fmt: off
            r"""
              examples:
                # Define a transaction using flags
                split --amount 10.00 --payee GiantEagle --category Food --debit Adam=6.00 Doug=4.00 --credit Adam=10.00

                # Short flags can be used instead of long ones
                split -a 10.00 -p GiantEagle -C Food -d Adam=6.00 Doug=4.00 -c Adam=10.00

                # Simple math can be used for debits and credits
                split -a 10.00 -p GiantEagle -C Food -d Adam=3/5 Doug=2/5 -c Adam=1
            """[1:-1]
            # fmt: on
        ),
    )
    _split_parser.add_argument("-a", "--amount", type=lambda v: Money(v, USD), help="the amount of $$$ being split")
    _split_parser.add_argument("-p", "--payee", type=str, default="Restaurant", help="the entity being paid $$$")
    _split_parser.add_argument("-C", "--category", type=str, default="Food", help="the transaction's category")
    _split_parser.add_argument(
        "-d",
        "--debit",
        type=str,
        nargs="*",
        action=KwargsAction,
        metavar="A=100",
        help="a mapping from people to the amounts they owe",
    )
    _split_parser.add_argument(
        "-c",
        "--credit",
        type=str,
        nargs="*",
        action=KwargsAction,
        metavar="B=200",
        help="a mapping from people to the amounts they paid",
    )

    @with_argparser(_split_parser)
    def do_split(self, opts: Namespace):
        """
        Add a split transaction with associated tips and taxes.
        """
        self.splitter.split(
            Split(
                amount=opts.amount,
                payee=opts.payee,
                category=opts.category,
                creditors=opts.credit,
                debtors=opts.debit,
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
