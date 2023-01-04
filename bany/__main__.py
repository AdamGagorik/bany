import logging
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from pathlib import Path

import pandas
import pandas as pd
from rich.logging import RichHandler

import bany.cmd.extract
import bany.cmd.solve
from bany.core.logger import console
from bany.core.logger import logger
from bany.core.settings import Settings


def main() -> int:
    parent = ArgumentParser(add_help=False)
    parent.add_argument("--verbose", action="store_true", help="use verbose logging?")
    opts, remaining = parent.parse_known_args()

    logging.basicConfig(
        level=logging.DEBUG if opts.verbose else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(show_path=False, rich_tracebacks=True, console=console, tracebacks_suppress=(pandas,))],
    )
    logging.getLogger("pdfminer").setLevel(logging.WARNING)

    pd.set_option("display.width", 1024)
    pd.set_option("display.max_rows", 512)
    pd.set_option("display.max_columns", 512)

    parser = ArgumentParser(
        usage=f"{Path(__file__).parent.name}",
        description=__doc__,
        parents=[parent],
        formatter_class=RawTextHelpFormatter,
    )

    subparsers = parser.add_subparsers(title="commands")

    for controller in (bany.cmd.extract.Controller, bany.cmd.solve.Controller):
        subparser = subparsers.add_parser(controller.__module__.split(".")[-2])
        subparser.set_defaults(controller=controller)
        controller.add_args(subparser)

    opts = parser.parse_args(args=remaining)

    if hasattr(opts, "controller"):
        # noinspection PyBroadException
        try:
            opts.controller(environ=Settings(), options=opts)()
            return 0
        except Exception:
            logger.exception("caught unhandled exception!")
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
