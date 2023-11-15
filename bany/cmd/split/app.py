"""
Itemize and split a receipt between people.
"""
import functools
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
from rich.console import Console
from rich.prompt import Confirm

from bany.cmd.split.splitter import Split
from bany.cmd.split.splitter import Splitter
from bany.cmd.split.splitter import Tax
from bany.cmd.split.splitter import Tip
from bany.core.money import as_money


class App(Cmd):
    """
    This is a simple app to try out the cmd2 module.
    """

    def __init__(self):
        super().__init__(
            allow_cli_args=False, shortcuts={"?": "help", "@": "run_script"}, command_sets=[SplitTransactions()]
        )
        del Cmd.do_py
        del Cmd.do_ipy
        del Cmd.do_edit
        del Cmd.do_shell
        del Cmd.do_macro
        del Cmd.do_alias
        del Cmd.do_run_pyscript
        self.rich_stderr = Console(stderr=True)
        self.rich_stdout = Console(file=self.stdout)
        self.prompt = "bany > "

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


def safe_eval(expression: str) -> int | float:
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


class MoneyAction(Action):
    """
    Parse an expression with simple math into a Money instance.
    """

    def __call__(self, parser: ArgumentParser, namespace: Namespace, values: list[str], option_string: str = None):
        """
        Parse the values expression and update the destination.
        """
        expr = " ".join(map(str.strip, values))
        value = safe_eval(expr)

        # value must be a number
        if not isinstance(value, (float, int)):
            raise TypeError(f"expecting int or float for {option_string} {expr}")

        # value should be positive definite
        if not value >= 0:
            raise ValueError(f"expecting positive definite value for {option_string} {expr}")

        setattr(namespace, self.dest, as_money(value))


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

            value = safe_eval(value)

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


@functools.lru_cache(maxsize=1)
def tax_parser() -> ArgumentParser:
    parser = Cmd2ArgumentParser(
        description="Add a tax to the previous split.",
        epilog=textwrap.dedent(
            # fmt: off
            r"""
              examples:
                # Add tax to the most recently added split.
                tax --group -1 --payee SalesTax --rate 0.06
            """[1:-1]
            # fmt: on
        ),
    )
    parser.add_argument("-g", "--groups", type=int, nargs="*", default=[-1], help="the groups to modify (see table)")
    parser.add_argument("-p", "--payee", type=str, default="SalesTax", help="the entity being paid $$$")
    parser.add_argument("-r", "--rate", type=float, required=True, help="the tax percentage")
    return parser


@functools.lru_cache(maxsize=1)
def tip_parser() -> ArgumentParser:
    parser = Cmd2ArgumentParser(
        description="Add a tip to the previous split.",
        epilog=textwrap.dedent(
            # fmt: off
            r"""
              examples:
                # Add tip to the most recently added split.
                tax --group -1 --category Tip --amount 5.00
            """[1:-1]
            # fmt: on
        ),
    )
    parser.add_argument("-g", "--groups", type=int, nargs="*", default=[-1], help="the groups to modify (see table)")
    parser.add_argument(
        "-a",
        "--amount",
        type=str,
        nargs="*",
        action=MoneyAction,
        required=True,
        metavar="EXPRESSION",
        help="the amount of $$$ being tipped",
    )
    parser.add_argument("-C", "--category", type=str, default="Tip", help="the tip's category")
    return parser


@functools.lru_cache(maxsize=1)
def split_parser() -> ArgumentParser:
    parser = Cmd2ArgumentParser(
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
    parser.add_argument(
        "-a",
        "--amount",
        type=str,
        nargs="*",
        action=MoneyAction,
        required=True,
        metavar="EXPRESSION",
        help="the amount of $$$ being split",
    )
    parser.add_argument("-p", "--payee", type=str, default="Restaurant", help="the entity being paid $$$")
    parser.add_argument("-C", "--category", type=str, default="Food", help="the transaction's category")
    parser.add_argument(
        "-d",
        "--debit",
        type=str,
        nargs="*",
        action=KwargsAction,
        metavar="A=100",
        help="a mapping from people to the amounts they owe",
    )
    parser.add_argument(
        "-c",
        "--credit",
        type=str,
        nargs="*",
        action=KwargsAction,
        metavar="B=200",
        help="a mapping from people to the amounts they paid",
    )
    return parser


@functools.lru_cache(maxsize=1)
def delete_parser() -> ArgumentParser:
    parser = Cmd2ArgumentParser(description="Remove specific split transactions.")
    parser.add_argument("-g", "--groups", type=int, nargs="*", default=[-1], help="the groups to modify (see table)")
    return parser


@with_default_category("My Category")
class SplitTransactions(CommandSet):
    """
    Manage a list of split transactions.
    """

    def __init__(self):
        super().__init__()
        self.splitter = Splitter()

    @with_argparser(tax_parser())
    def do_tax(self, opts: Namespace):
        if not self.splitter.splits:
            self._cmd.perror("no transactions to tax!")
            return

        for group in opts.groups:
            self._cmd.poutput(f"[red underline]tax group [{group:>3}] at: {opts.rate*100:6.2f}%")
            self.splitter.tax(Tax(rate=opts.rate, payee=opts.payee))

    @with_argparser(tip_parser())
    def do_tip(self, opts: Namespace):
        if not self.splitter.splits:
            self._cmd.perror("no transactions to tip!")
            return

        for group in opts.groups:
            self._cmd.poutput(f"[red underline]tip group [{group:>3}] at: {str(opts.amount):>7}")
            self.splitter.tip(Tip(amount=opts.amount, category=opts.category))

    def do_show(self, _: Statement):
        """
        Show the current split transactions.
        """
        if not self.splitter.splits:
            self._cmd.perror("no transactions to display!")
            return

        self._display_frame()

    @with_argparser(split_parser())
    def do_split(self, opts: Namespace):
        """
        Add a split transaction with associated tips and taxes.
        """
        split = Split(
            amount=opts.amount,
            payee=opts.payee,
            category=opts.category,
            creditors=opts.credit,
            debtors=opts.debit,
        )
        group = self.splitter.split(split)
        self._cmd.poutput(f"[red underline]add group [{group:>3}] at: {str(opts.amount):>7}")

    def do_summarize(self, _: Statement):
        """
        Group by category and payee to summarize the current transactions.
        """
        if not self.splitter.splits:
            self._cmd.perror("no transactions to summarize!")
            return

        self._display_frame(frame=self.splitter.summary)

    def do_clear(self, _: Statement):
        """
        Remove all split transactions.
        """
        if not self.splitter.splits:
            self._cmd.perror("no transactions to delete!")
            return

        if Confirm.ask("Remove all transactions?"):
            self.splitter.clear()
            self._cmd.poutput("[red underline]all transactions removed!")

    @with_argparser(delete_parser())
    def do_delete(self, opts: Namespace):
        if not self.splitter.splits:
            self._cmd.perror("no transactions to delete!")
            return

        if opts.groups is not None:
            keys = list(self.splitter.splits.keys())
            opts.groups = [keys[group] for group in keys]
            subset = self.splitter.frame.loc[self.splitter.frame["group"].isin(opts.groups), :]
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

        if frame is None or frame.empty:
            self._cmd.perror("no frame to display")
            return

        self._cmd.poutput(frame)
