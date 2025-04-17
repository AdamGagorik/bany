"""
Unit tests for module.
"""

import logging

import networkx as nx
import pandas as pd
import pytest

import bany.cmd.solve.network.algo
import bany.cmd.solve.network.visualize
import bany.cmd.solve.solvers.graphsolver
import tests.bany.cmd.cookbook as cookbook
from bany.cmd.solve.solvers.basesolver import BucketSolver
from bany.cmd.solve.solvers.constrained import BucketSolverConstrained, BucketSolverSimple


@pytest.mark.parametrize(
    "starting_frame,expected_graph,solver",
    [
        # simple_no_addition : the amounts should be redistributed
        (
            pd.DataFrame([
                {
                    "label": "T",
                    "current_value": 3000.0,
                    "optimal_ratio": 1.00,
                    "amount_to_add": 0.0000,
                    "children": ("H", "I", "J"),
                },
                {"label": "H", "current_value": 3000.0, "optimal_ratio": 0.50, "amount_to_add": 0.0000, "children": ()},
                {"label": "I", "current_value": 0000.0, "optimal_ratio": 0.35, "amount_to_add": 0.0000, "children": ()},
                {"label": "J", "current_value": 0000.0, "optimal_ratio": 0.15, "amount_to_add": 0.0000, "children": ()},
            ]),
            cookbook.make_graph(
                nodes=[
                    ("T", {"results_value": 3000.0 + 3000.0 * 0.00, "amount_to_add": +3000.0 * 0.00}),
                    ("H", {"results_value": 3000.0 - 3000.0 * 0.50, "amount_to_add": -3000.0 * 0.50}),
                    ("I", {"results_value": 0.0000 + 3000.0 * 0.35, "amount_to_add": +3000.0 * 0.35}),
                    ("J", {"results_value": 0.0000 + 3000.0 * 0.15, "amount_to_add": +3000.0 * 0.15}),
                ],
                edges=[("T", "H"), ("T", "I"), ("T", "J")],
            ),
            BucketSolverSimple.solve,
        ),
        # simple_value_added : the amounts should be redistributed and value should be added
        (
            pd.DataFrame([
                {
                    "label": "F",
                    "current_value": 8000.0 + 0.000,
                    "optimal_ratio": 1.00,
                    "amount_to_add": 1000.0,
                    "children": ("U", "V", "W"),
                },
                {
                    "label": "U",
                    "current_value": 4000.0 + 0.000,
                    "optimal_ratio": 0.50,
                    "amount_to_add": 0.0000,
                    "children": (),
                },
                {
                    "label": "V",
                    "current_value": 2800.0 + 256.0,
                    "optimal_ratio": 0.35,
                    "amount_to_add": 0.0000,
                    "children": (),
                },
                {
                    "label": "W",
                    "current_value": 1200.0 - 256.0,
                    "optimal_ratio": 0.15,
                    "amount_to_add": 0.0000,
                    "children": (),
                },
            ]),
            cookbook.make_graph(
                nodes=[
                    (
                        "F",
                        {
                            "results_value": 8000.0 + 0.000 + 1000.0 * 1.00 + 0.000,
                            "amount_to_add": +1000.0 * 0.00 + 0.000,
                        },
                    ),
                    (
                        "U",
                        {
                            "results_value": 4000.0 + 0.000 + 1000.0 * 0.50 + 0.000,
                            "amount_to_add": +1000.0 * 0.50 + 0.000,
                        },
                    ),
                    (
                        "V",
                        {
                            "results_value": 2800.0 + 256.0 + 1000.0 * 0.35 - 256.0,
                            "amount_to_add": +1000.0 * 0.35 - 256.0,
                        },
                    ),
                    (
                        "W",
                        {
                            "results_value": 1200.0 - 256.0 + 1000.0 * 0.15 + 256.0,
                            "amount_to_add": +1000.0 * 0.15 + 256.0,
                        },
                    ),
                ],
                edges=[("F", "U"), ("F", "V"), ("F", "W")],
            ),
            BucketSolverSimple.solve,
        ),
        # constrained_simple : values are only added to the final result and are in perfect ratios
        (
            pd.DataFrame([
                {
                    "label": "A",
                    "current_value": 4000.0,
                    "optimal_ratio": 1.00,
                    "amount_to_add": 1000.0,
                    "children": ("0", "1", "2"),
                },
                {"label": "0", "current_value": 2000.0, "optimal_ratio": 0.50, "amount_to_add": 0.0000, "children": ()},
                {"label": "1", "current_value": 1000.0, "optimal_ratio": 0.25, "amount_to_add": 0.0000, "children": ()},
                {"label": "2", "current_value": 1000.0, "optimal_ratio": 0.25, "amount_to_add": 0.0000, "children": ()},
            ]),
            cookbook.make_graph(
                nodes=[
                    ("A", {"results_value": 4000.0 + 1000.0 * 1.00, "amount_to_add": 1000.0 * 0.00}),
                    ("0", {"results_value": 2000.0 + 1000.0 * 0.50, "amount_to_add": 1000.0 * 0.50}),
                    ("1", {"results_value": 1000.0 + 1000.0 * 0.25, "amount_to_add": 1000.0 * 0.25}),
                    ("2", {"results_value": 1000.0 + 1000.0 * 0.25, "amount_to_add": 1000.0 * 0.25}),
                ],
                edges=[("A", "0"), ("A", "1"), ("A", "2")],
            ),
            BucketSolverConstrained.solve,
        ),
        # constrained_complex : values are only added to the final result and are in perfect ratios
        (
            pd.DataFrame([
                {
                    "label": "B",
                    "current_value": 8000.0,
                    "optimal_ratio": 1.00,
                    "amount_to_add": 4000.0,
                    "children": ("3", "4", "5"),
                },
                {"label": "3", "current_value": 4000.0, "optimal_ratio": 0.50, "amount_to_add": 0.0000, "children": ()},
                {"label": "4", "current_value": 2000.0, "optimal_ratio": 0.25, "amount_to_add": 0.0000, "children": ()},
                {
                    "label": "5",
                    "current_value": 2000.0,
                    "optimal_ratio": 0.25,
                    "amount_to_add": 0.0000,
                    "children": ("C", "D"),
                },
                {"label": "C", "current_value": 1000.0, "optimal_ratio": 0.50, "amount_to_add": 0.0000, "children": ()},
                {
                    "label": "D",
                    "current_value": 1000.0,
                    "optimal_ratio": 0.50,
                    "amount_to_add": 0.0000,
                    "children": ("6", "7"),
                },
                {"label": "6", "current_value": 2.50e2, "optimal_ratio": 0.25, "amount_to_add": 0.0000, "children": ()},
                {"label": "7", "current_value": 7.50e2, "optimal_ratio": 0.75, "amount_to_add": 0.0000, "children": ()},
            ]),
            cookbook.make_graph(
                nodes=[
                    (
                        "B",
                        {
                            "results_value": 8000.0 + 4000.0 * 1.00 * 1.00 * 1.00,
                            "amount_to_add": 4000.0 * 0.00 * 1.00 * 1.00,
                        },
                    ),
                    (
                        "3",
                        {
                            "results_value": 4000.0 + 4000.0 * 0.50 * 1.00 * 1.00,
                            "amount_to_add": 4000.0 * 0.50 * 1.00 * 1.00,
                        },
                    ),
                    (
                        "4",
                        {
                            "results_value": 2000.0 + 4000.0 * 0.25 * 1.00 * 1.00,
                            "amount_to_add": 4000.0 * 0.25 * 1.00 * 1.00,
                        },
                    ),
                    (
                        "5",
                        {
                            "results_value": 2000.0 + 4000.0 * 0.25 * 1.00 * 1.00,
                            "amount_to_add": 4000.0 * 0.00 * 1.00 * 1.00,
                        },
                    ),
                    (
                        "C",
                        {
                            "results_value": 1000.0 + 4000.0 * 0.25 * 0.50 * 1.00,
                            "amount_to_add": 4000.0 * 0.25 * 0.50 * 1.00,
                        },
                    ),
                    (
                        "D",
                        {
                            "results_value": 1000.0 + 4000.0 * 0.25 * 0.50 * 1.00,
                            "amount_to_add": 4000.0 * 0.00 * 0.50 * 1.00,
                        },
                    ),
                    (
                        "6",
                        {
                            "results_value": 2.50e2 + 4000.0 * 0.25 * 0.50 * 0.25,
                            "amount_to_add": 4000.0 * 0.25 * 0.50 * 0.25,
                        },
                    ),
                    (
                        "7",
                        {
                            "results_value": 7.50e2 + 4000.0 * 0.25 * 0.50 * 0.75,
                            "amount_to_add": 4000.0 * 0.25 * 0.50 * 0.75,
                        },
                    ),
                ],
                edges=[("B", "3"), ("B", "4"), ("B", "5"), ("5", "C"), ("5", "D"), ("D", "6"), ("D", "7")],
            ),
            BucketSolverConstrained.solve,
        ),
    ],
    ids=[
        "simple_no_addition",
        "simple_value_added",
        "constrained_simple",
        "constrained_complex",
    ],
)
def test_solve(starting_frame: pd.DataFrame, expected_graph: nx.DiGraph, solver: type[BucketSolver]):
    logging.debug("starting_frame:\n%s", starting_frame)
    starting_graph: nx.DiGraph = bany.cmd.solve.network.algo.create(starting_frame)
    cookbook.show_graph("starting_graph", starting_graph, **bany.cmd.solve.network.visualize.FORMATS_INP)
    cookbook.show_graph("expected_graph", expected_graph, **bany.cmd.solve.network.visualize.FORMATS_OUT)
    observed_graph: nx.DiGraph = bany.cmd.solve.solvers.graphsolver.solve(starting_graph, solver=solver, inplace=False)
    cookbook.show_graph("observed_graph", observed_graph, **bany.cmd.solve.network.visualize.FORMATS_OUT)
    node_match = nx.algorithms.isomorphism.numerical_node_match(["results_value", "amount_to_add"], [-1000, -1000])
    assert nx.is_isomorphic(observed_graph, expected_graph, node_match=node_match)
