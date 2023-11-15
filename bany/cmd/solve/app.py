"""

Parse an input file and create transactions in YNAB.
"""
from pathlib import Path

import networkx as nx
import pandas as pd

import bany.cmd.solve.network.loader
import bany.cmd.solve.network.visualize as visualize
import bany.cmd.solve.solvers.constrained
import bany.cmd.solve.solvers.graphsolver
import bany.cmd.solve.solvers.montecarlo
import bany.cmd.solve.solvers.unconstrained
from bany.cmd.solve.network.algo import aggregate_quantity
from bany.cmd.solve.network.attrs import node_attrs
from bany.cmd.solve.solvers.basesolver import BucketSolver
from bany.cmd.solve.solvers.graphsolver import solve
from bany.core.logger import logger
from bany.core.logger import logline
from bany.core.money import moneyfmt


def main(solver: type[BucketSolver], config: Path) -> None:
    frame: pd.DataFrame = bany.cmd.solve.network.loader.load(path=config)
    logger.info("frame:\n%s\n", frame)

    graph: nx.DiGraph = bany.cmd.solve.network.algo.create(frame)
    visualize.log("graph", graph, **visualize.FORMATS_INP)

    solved: nx.DiGraph = solve(graph, solver=solver, inplace=False)
    visualize.log("solved", solved, **visualize.FORMATS_OUT)

    _display_results(solved, fmt=f"%-{max(15, max(len(n) for n in solved.nodes))}s: %s")


def _display_results(graph: nx.DiGraph, fmt: str):
    amount_to_add: float = aggregate_quantity(graph, key=node_attrs.amount_to_add.column)
    logger.info(fmt, "amount_to_add", moneyfmt(amount_to_add))

    results_value: float = aggregate_quantity(graph, key=node_attrs.results_value.column, leaves=True)
    logger.info(fmt, "results_value", moneyfmt(results_value))

    results_ratio: float = aggregate_quantity(graph, key=node_attrs.results_ratio.column, leaves=True)
    logger.info(fmt, "results_ratio", moneyfmt(results_ratio, decimals=10))

    logline()
    for node in graph:
        # noinspection PyCallingNonCallable
        if graph.out_degree(node) == 0 and graph.in_degree(node) == 1:
            amount_to_add: float = graph.nodes[node][node_attrs.amount_to_add.column]
            logger.info(fmt, node, moneyfmt(amount_to_add))
