"""
Command line scripts for dealing with budgets.
"""

import logging
from functools import partial
from pathlib import Path
from typing import Annotated, cast

import pandas
import pandas as pd
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from typer import Option, Typer

DEFAULT_CONFIG: Path = Path.cwd().joinpath("config.yml")

app = Typer(add_completion=False, help=__doc__, rich_markup_mode="rich", pretty_exceptions_show_locals=False)


@app.callback()
def setup(
    verbose: Annotated[bool, Option()] = False,
) -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                show_path=False,
                rich_tracebacks=False,
                tracebacks_show_locals=False,
                tracebacks_suppress=(pandas,),
                console=Console(theme=Theme({"repr.number": ""})),
            )
        ],
    )
    logging.getLogger("pdfminer").setLevel(logging.WARNING)

    pd.set_option("display.width", 1024)
    pd.set_option("display.max_rows", 512)
    pd.set_option("display.max_columns", 512)


app.add_typer(sub := Typer(), name="solve", help="Solve the bucket partitioning problem.")


@sub.command()
def montecarlo(
    config: Annotated[Path, Option(help="The config file to use.")] = DEFAULT_CONFIG,
    step_size: Annotated[float, Option(help="The Monte Carlo step size to use.")] = 0.01,
    sheet_name: Annotated[str, Option(help="The sheet name or # when loading xlsx")] = "Sheet1",
) -> None:
    """
    Solve the partitioning problem using Monte Carlo techniques.
    """
    from bany.cmd.solve.app import main
    from bany.cmd.solve.solvers.basesolver import BucketSolver
    from bany.cmd.solve.solvers.montecarlo import BucketSolverConstrainedMonteCarlo

    main(
        config=config,
        solver=cast(
            type[BucketSolver],
            partial(
                BucketSolverConstrainedMonteCarlo.solve,
                step_size=step_size,
            ),
        ),
        sheet_name=sheet_name,
    )


@sub.command()
def constrained(
    config: Annotated[Path, Option(help="The config file to use.")] = DEFAULT_CONFIG,
    sheet_name: Annotated[str, Option(help="The sheet name or # when loading xlsx")] = "Sheet1",
) -> None:
    """
    Solve the partitioning problem using constrained optimization.
    """
    from bany.cmd.solve.app import main
    from bany.cmd.solve.solvers.basesolver import BucketSolver
    from bany.cmd.solve.solvers.constrained import BucketSolverConstrained

    main(
        config=config,
        solver=cast(
            type[BucketSolver],
            partial(
                BucketSolverConstrained.solve,
            ),
        ),
        sheet_name=sheet_name,
    )


@sub.command()
def unconstrained(
    config: Annotated[Path, Option(help="The config file to use.")] = DEFAULT_CONFIG,
    sheet_name: Annotated[str, Option(help="The sheet name or # when loading xlsx")] = "Sheet1",
) -> None:
    """
    Solve the partitioning problem using unconstrained optimization.
    """
    from bany.cmd.solve.app import main
    from bany.cmd.solve.solvers.basesolver import BucketSolver
    from bany.cmd.solve.solvers.unconstrained import BucketSolverSimple

    main(
        config=config,
        solver=cast(
            type[BucketSolver],
            partial(
                BucketSolverSimple.solve,
            ),
        ),
        sheet_name=sheet_name,
    )


@app.command()
def split() -> None:
    """
    Itemize and split a receipt between people.
    """
    from bany.cmd.split.app import App

    raise SystemExit(App().cmdloop())


app.add_typer(sub := Typer(), name="extract", help="Parse an input file and create transactions in YNAB.")


@sub.command()
def pdf(
    inp: Annotated[Path, Option(help="The input file to parse.")],
    config: Annotated[Path, Option(help="The config file to use.")] = DEFAULT_CONFIG,
    upload: Annotated[bool, Option(help="Upload transactions to YNAB budget?")] = False,
) -> None:
    """
    Parse a PDF file and create transactions in YNAB.
    """
    from bany.cmd.extract.app import main

    main(extractor="pdf", inp=inp, config=config, upload=upload)


@app.command()
def ynab(
    budget_name: Annotated[str, Option(help="The name of the YNAB budget.")],
    show_categories: Annotated[bool, Option(help="Upload transactions to YNAB budget?")] = False,
) -> None:
    """
    Display queries from the YNAB budget API.
    """
    from bany.cmd.ynab.app import main

    main(budget_name=budget_name, show_categories=show_categories)


if __name__ == "__main__":
    app()
