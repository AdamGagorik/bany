"""
Command line scripts for dealing with budgets.
"""
import logging
from functools import partial
from pathlib import Path
from typing import Annotated
from typing import cast

import pandas
import pandas as pd
from rich.logging import RichHandler
from typer import Option
from typer import Typer

from bany.core.logger import console

app = Typer(add_completion=False, help=__doc__, rich_markup_mode="rich")


@app.callback()
def setup(
    verbose: Annotated[bool, Option()] = False,
) -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(show_path=False, rich_tracebacks=True, console=console, tracebacks_suppress=(pandas,))],
    )
    logging.getLogger("pdfminer").setLevel(logging.WARNING)

    pd.set_option("display.width", 1024)
    pd.set_option("display.max_rows", 512)
    pd.set_option("display.max_columns", 512)


app.add_typer(sub := Typer(), name="solve", help="Solve the bucket partitioning problem.")


@sub.command()
def montecarlo(
    config: Annotated[Path, Option(help="The config file to use.")] = Path.cwd().joinpath("config.yml"),
    step_size: Annotated[float, Option(help="The Monte Carlo step size to use.")] = 0.01,
) -> None:
    """
    Solve the partitioning problem using Monte Carlo techniques.
    """
    from bany.cmd.solve.solvers.montecarlo import BucketSolverConstrainedMonteCarlo
    from bany.cmd.solve.solvers.basesolver import BucketSolver
    from bany.cmd.solve.app import main

    main(
        config=config,
        solver=cast(
            type[BucketSolver],
            partial(
                BucketSolverConstrainedMonteCarlo.solve,
                step_size=step_size,
            ),
        ),
    )


@sub.command()
def constrained(
    config: Annotated[Path, Option(help="The config file to use.")] = Path.cwd().joinpath("config.yml"),
) -> None:
    """
    Solve the partitioning problem using constrained optimization.
    """
    from bany.cmd.solve.solvers.constrained import BucketSolverConstrained
    from bany.cmd.solve.solvers.basesolver import BucketSolver
    from bany.cmd.solve.app import main

    main(
        config=config,
        solver=cast(
            type[BucketSolver],
            partial(
                BucketSolverConstrained.solve,
            ),
        ),
    )


@sub.command()
def unconstrained(
    config: Annotated[Path, Option(help="The config file to use.")] = Path.cwd().joinpath("config.yml"),
) -> None:
    """
    Solve the partitioning problem using unconstrained optimization.
    """
    from bany.cmd.solve.solvers.unconstrained import BucketSolverSimple
    from bany.cmd.solve.solvers.basesolver import BucketSolver
    from bany.cmd.solve.app import main

    main(
        config=config,
        solver=cast(
            type[BucketSolver],
            partial(
                BucketSolverSimple.solve,
            ),
        ),
    )


@app.command()
def split() -> None:
    """
    Itemize and split a receipt between people.
    """
    from .cmd.split.app import App

    raise SystemExit(App().cmdloop())


app.add_typer(sub := Typer(), name="extract", help="Parse an input file and create transactions in YNAB.")


@sub.command()
def pdf(
    inp: Annotated[Path, Option(help="The input file to parse.")],
    config: Annotated[Path, Option(help="The config file to use.")] = Path.cwd().joinpath("config.yml"),
    upload: Annotated[bool, Option(help="Upload transactions to YNAB budget?")] = False,
) -> None:
    """
    Parse a PDF file and create transactions in YNAB.
    """
    from bany.cmd.extract.app import main

    main(extractor="", inp=inp, config=config, upload=upload)


if __name__ == "__main__":
    app()
