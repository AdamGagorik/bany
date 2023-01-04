"""
Parse an input file and create transactions in YNAB.
"""
import dataclasses
import pathlib
from argparse import ArgumentParser
from argparse import Namespace

import networkx as nx
import pandas as pd

import bany.cmd.solve.network.loader
import bany.cmd.solve.network.visualize as visualize
import bany.cmd.solve.solvers.constrained
import bany.cmd.solve.solvers.graphsolver
import bany.cmd.solve.solvers.montecarlo
import bany.cmd.solve.solvers.unconstrained
from bany.cmd.base import Controller as BaseController
from bany.cmd.solve.network.algo import aggregate_quantity
from bany.cmd.solve.network.attrs import node_attrs
from bany.cmd.solve.solvers import SOLVERS
from bany.cmd.solve.solvers.graphsolver import solve
from bany.core.logger import logger
from bany.core.logger import logline
from bany.core.money import moneyfmt
from bany.core.settings import Settings

DEFAULT_CONFIG: pathlib.Path = pathlib.Path.cwd().joinpath("config.yml")


@dataclasses.dataclass(frozen=True)
class Controller(BaseController):
    """
    A class to orchestrate the main logic.
    """

    environ: Settings
    options: Namespace

    @classmethod
    def add_args(cls, parser: ArgumentParser):
        group = parser.add_argument_group("solve")
        group.add_argument(
            default="constrained",
            dest="solver",
            choices=list(SOLVERS.keys()),
            help="the solver to use",
        )

        group.add_argument("--config", default=DEFAULT_CONFIG, type=pathlib.Path, help="the config file to use")

        group = parser.add_argument_group("montecarlo")
        group.add_argument(
            "--step-size", dest="step_size", type=float, default=0.01, help="the Monte Carlo step size to use"
        )

    def __call__(self):
        frame: pd.DataFrame = bany.cmd.solve.network.loader.load(path=self.options.config)
        logger.info("frame:\n%s\n", frame)

        graph: nx.DiGraph = bany.cmd.solve.network.algo.create(frame)
        visualize.log("graph", graph, **visualize.FORMATS_INP)

        kwargs = SOLVERS[self.options.solver](step_size=self.options.step_size)
        solved: nx.DiGraph = solve(graph, inplace=False, **kwargs)
        visualize.log("solved", graph, **visualize.FORMATS_OUT)

        self._display_results(solved, kvfmt=f"%-{max(15, max(len(n) for n in solved.nodes))}s: %s")

    @staticmethod
    def _display_results(graph: nx.DiGraph, kvfmt: str = "%-20s: %s"):
        amount_to_add: float = aggregate_quantity(graph, key=node_attrs.amount_to_add.column)
        logger.info(kvfmt, "amount_to_add", moneyfmt(amount_to_add))

        results_value: float = aggregate_quantity(graph, key=node_attrs.results_value.column, leaves=True)
        logger.info(kvfmt, "results_value", moneyfmt(results_value))

        results_ratio: float = aggregate_quantity(graph, key=node_attrs.results_ratio.column, leaves=True)
        logger.info(kvfmt, "results_ratio", moneyfmt(results_ratio, decimals=10))

        logline()
        for node in graph:
            # noinspection PyCallingNonCallable
            if graph.out_degree(node) == 0 and graph.in_degree(node) == 1:
                amount_to_add: float = graph.nodes[node][node_attrs.amount_to_add.column]
                logger.info(kvfmt, node, moneyfmt(amount_to_add))
