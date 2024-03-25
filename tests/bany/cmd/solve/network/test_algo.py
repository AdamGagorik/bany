"""
Unit tests for module.
"""

import logging
import typing

import networkx as nx
import pandas as pd
import pytest

import bany.cmd.solve.network.algo
import bany.cmd.solve.network.attrs
import bany.cmd.solve.network.visualize
import tests.bany.cmd.cookbook as cookbook


@pytest.mark.parametrize(
    "graph,expected_root",
    [
        (nx.DiGraph([(1, 2), (2, 3), (3, 4), (3, 5)]), 1),
        (nx.DiGraph([(1, 2), (2, 3), (0, 1), (2, 4)]), 0),
    ],
)
def test_get_graph_root(graph, expected_root: str):
    observed_root = bany.cmd.solve.network.algo.get_graph_root(graph)
    assert observed_root == expected_root


@pytest.mark.parametrize(
    "frame,expected_graph",
    [
        (
            pd.DataFrame(
                [
                    dict(
                        label="0",
                        current_value=8000.0,
                        optimal_ratio=1.0e2,
                        amount_to_add=0.0,
                        children=("X", "Y", "Z"),
                    ),
                    dict(label="X", current_value=2500.0, optimal_ratio=4.5e1, amount_to_add=0.0, children=()),
                    dict(label="Y", current_value=5000.0, optimal_ratio=2.0e1, amount_to_add=0.0, children=()),
                    dict(label="Z", current_value=500.00, optimal_ratio=3.5e1, amount_to_add=0.0, children=("Q", "R")),
                    dict(label="Q", current_value=200.00, optimal_ratio=2.5e1, amount_to_add=0.0, children=()),
                    dict(label="R", current_value=300.00, optimal_ratio=7.5e1, amount_to_add=0.0, children=()),
                ]
            ),
            cookbook.make_graph(
                nodes=[
                    (
                        "0",
                        dict(
                            level=0,
                            current_value=8000.0,
                            results_value=0.0,
                            optimal_value=8000.0 * 1.00,
                            current_ratio=1.0000,
                            optimal_ratio=1.00,
                            results_ratio=0.0,
                            product_ratio=1.00,
                            amount_to_add=0.0,
                        ),
                    ),
                    (
                        "X",
                        dict(
                            level=1,
                            current_value=2500.0,
                            results_value=0.0,
                            optimal_value=8000.0 * 0.45,
                            current_ratio=0.3125,
                            optimal_ratio=0.45,
                            results_ratio=0.0,
                            product_ratio=0.45,
                            amount_to_add=0.0,
                        ),
                    ),
                    (
                        "Y",
                        dict(
                            level=1,
                            current_value=5000.0,
                            results_value=0.0,
                            optimal_value=8000.0 * 0.20,
                            current_ratio=0.6250,
                            optimal_ratio=0.20,
                            results_ratio=0.0,
                            product_ratio=0.20,
                            amount_to_add=0.0,
                        ),
                    ),
                    (
                        "Z",
                        dict(
                            level=1,
                            current_value=500.00,
                            results_value=0.0,
                            optimal_value=8000.0 * 0.35,
                            current_ratio=0.0625,
                            optimal_ratio=0.35,
                            results_ratio=0.0,
                            product_ratio=0.35,
                            amount_to_add=0.0,
                        ),
                    ),
                    (
                        "Q",
                        dict(
                            level=2,
                            current_value=200.00,
                            results_value=0.0,
                            optimal_value=8000.0 * 0.35 * 0.25,
                            current_ratio=0.4000,
                            optimal_ratio=0.25,
                            results_ratio=0.0,
                            product_ratio=0.35 * 0.25,
                            amount_to_add=0.0,
                        ),
                    ),
                    (
                        "R",
                        dict(
                            level=2,
                            current_value=300.00,
                            results_value=0.0,
                            optimal_value=8000.0 * 0.35 * 0.75,
                            current_ratio=0.6000,
                            optimal_ratio=0.75,
                            results_ratio=0.0,
                            product_ratio=0.35 * 0.75,
                            amount_to_add=0.0,
                        ),
                    ),
                ],
                edges=[("0", "X"), ("0", "Y"), ("0", "Z"), ("Z", "Q"), ("Z", "R")],
            ),
        )
    ],
)
def test_create(frame: pd.DataFrame, expected_graph: nx.DiGraph):
    logging.debug("starting_frame\n%s", frame)
    cookbook.show_graph("expected_graph", expected_graph, algo_graph=True)
    observed_graph: nx.DiGraph = bany.cmd.solve.network.algo.create(frame)
    cookbook.show_graph("observed_graph", observed_graph, algo_graph=True)
    attrs, defaults = zip(
        *[
            (f.column, -10000)
            for f in bany.cmd.solve.network.attrs.node_attrs.subset()
            if f.column
            not in [
                bany.cmd.solve.network.attrs.node_attrs.label.column,
            ]
        ]
    )
    node_match = nx.algorithms.isomorphism.numerical_node_match(attrs, defaults)
    assert nx.is_isomorphic(observed_graph, expected_graph, node_match=node_match)


@pytest.mark.parametrize(
    "starting_graph,expected_graph,key,level",
    [
        (
            cookbook.make_graph(
                nodes=[
                    ("0", dict(value=8.00)),
                    ("A", dict(value=2.00)),
                    ("B", dict(value=2.00)),
                    ("C", dict(value=4.00)),
                ],
                edges=[("0", "A"), ("0", "B"), ("0", "C")],
            ),
            cookbook.make_graph(
                nodes=[
                    ("0", dict(value=1.00)),
                    ("A", dict(value=0.25)),
                    ("B", dict(value=0.25)),
                    ("C", dict(value=0.50)),
                ],
                edges=[("0", "A"), ("0", "B"), ("0", "C")],
            ),
            "value",
            None,
        ),
        (
            cookbook.make_graph(
                nodes=[
                    ("1", dict(value=8.00)),
                    ("Q", dict(value=2.00)),
                    ("R", dict(value=2.00)),
                    ("S", dict(value=4.00)),
                ],
                edges=[("1", "Q"), ("1", "R"), ("1", "S")],
            ),
            cookbook.make_graph(
                nodes=[
                    ("1", dict(value=1.00)),
                    ("Q", dict(value=2.00)),
                    ("R", dict(value=2.00)),
                    ("S", dict(value=4.00)),
                ],
                edges=[("1", "Q"), ("1", "R"), ("1", "S")],
            ),
            "value",
            0,
        ),
    ],
)
def test_normalize(starting_graph: nx.DiGraph, expected_graph: nx.DiGraph, key: str, level: int):
    cookbook.show_graph("starting_graph", starting_graph)
    observed_graph: nx.DiGraph = bany.cmd.solve.network.algo.normalize(starting_graph, key, levels=level, inplace=True)
    cookbook.show_graph("expected_graph", expected_graph)
    cookbook.show_graph("observed_graph", observed_graph)
    node_match = nx.algorithms.isomorphism.numerical_node_match(key, 0.0)
    assert nx.is_isomorphic(starting_graph, starting_graph, node_match=node_match)
    assert nx.is_isomorphic(observed_graph, observed_graph, node_match=node_match)
    assert nx.is_isomorphic(expected_graph, expected_graph, node_match=node_match)
    assert nx.is_isomorphic(observed_graph, expected_graph, node_match=node_match)
    assert id(observed_graph) == id(starting_graph)
    assert id(observed_graph) != id(expected_graph)


@pytest.mark.parametrize(
    "starting_graph,expected_graph,func,out",
    [
        (
            cookbook.make_graph(
                nodes=[
                    ("H", dict(inp_value=1)),
                    ("I", dict(inp_value=2)),
                    ("J", dict(inp_value=3)),
                    ("K", dict(inp_value=4)),
                ],
                edges=[
                    ("H", "I"),
                    ("H", "J"),
                    ("H", "K"),
                ],
            ),
            cookbook.make_graph(
                nodes=[
                    ("H", dict(inp_value=1, out_value=2)),
                    ("I", dict(inp_value=2, out_value=4)),
                    ("J", dict(inp_value=3, out_value=6)),
                    ("K", dict(inp_value=4, out_value=8)),
                ],
                edges=[
                    ("H", "I"),
                    ("H", "J"),
                    ("H", "K"),
                ],
            ),
            lambda inp_value: 2 * inp_value,
            "out_value",
        ),
    ],
)
def test_node_apply(starting_graph: nx.DiGraph, expected_graph: nx.DiGraph, func: typing, out: str):
    cookbook.show_graph("starting_graph", starting_graph)
    cookbook.show_graph("expected_graph", expected_graph)
    observed_graph: nx.DiGraph = bany.cmd.solve.network.algo.node_apply(starting_graph, func, out, False, False)
    cookbook.show_graph("observed_graph", observed_graph)
    node_match = nx.algorithms.isomorphism.numerical_node_match(["inp_value", "out_value"], [-1000, -1000])
    assert nx.is_isomorphic(observed_graph, expected_graph, node_match=node_match)
    assert id(observed_graph) != id(starting_graph)


@pytest.mark.parametrize(
    "starting_graph,expected_value,key,leaves",
    [
        (
            cookbook.make_graph(
                nodes=[
                    ("M", dict(inp_value=1.50)),
                    ("N", dict(inp_value=2.50)),
                    ("O", dict(inp_value=3.50)),
                    ("P", dict(inp_value=4.50)),
                ],
                edges=[
                    ("M", "N"),
                    ("N", "O"),
                    ("N", "P"),
                ],
            ),
            12.0,
            "inp_value",
            False,
        ),
        (
            cookbook.make_graph(
                nodes=[
                    ("A", dict(inp_value=1.50)),
                    ("E", dict(inp_value=2.50)),
                    ("L", dict(inp_value=3.50)),
                    ("F", dict(inp_value=4.50)),
                ],
                edges=[
                    ("A", "E"),
                    ("E", "L"),
                    ("E", "F"),
                ],
            ),
            8.0,
            "inp_value",
            True,
        ),
    ],
)
def test_aggregate(starting_graph: nx.DiGraph, expected_value: float, key: str, leaves: bool):
    cookbook.show_graph("starting_graph", starting_graph, inp_value="{:.3f}")
    logging.debug("expected_value: %.3f", expected_value)
    observed_value: float = bany.cmd.solve.network.algo.aggregate_quantity(starting_graph, key, leaves=leaves)
    logging.debug("observed_value: %.3f", observed_value)
    assert observed_value == pytest.approx(expected_value)


@pytest.mark.parametrize(
    "starting_graph,expected_graph,key,out",
    [
        (
            cookbook.make_graph(
                nodes=[
                    ("1", dict(inp_value=0.50)),
                    ("2", dict(inp_value=0.25)),
                    ("3", dict(inp_value=0.50)),
                    ("4", dict(inp_value=0.75)),
                    ("5", dict(inp_value=0.10)),
                    ("6", dict(inp_value=0.10)),
                    ("7", dict(inp_value=0.10)),
                ],
                edges=[("1", "2"), ("1", "3"), ("1", "4"), ("4", "5"), ("5", "6"), ("6", "7")],
            ),
            cookbook.make_graph(
                nodes=[
                    ("1", dict(inp_value=0.50, out_value=0.50)),
                    ("2", dict(inp_value=0.25, out_value=0.50 * 0.25)),
                    ("3", dict(inp_value=0.50, out_value=0.50 * 0.50)),
                    ("4", dict(inp_value=0.75, out_value=0.50 * 0.75)),
                    ("5", dict(inp_value=0.10, out_value=0.50 * 0.75 * 0.10)),
                    ("6", dict(inp_value=0.10, out_value=0.50 * 0.75 * 0.10 * 0.10)),
                    ("7", dict(inp_value=0.10, out_value=0.50 * 0.75 * 0.10 * 0.10 * 0.10)),
                ],
                edges=[("1", "2"), ("1", "3"), ("1", "4"), ("4", "5"), ("5", "6"), ("6", "7")],
            ),
            "inp_value",
            "out_value",
        ),
    ],
)
def test_aggregate_quantity_along_depth(starting_graph: nx.DiGraph, expected_graph: nx.DiGraph, key: str, out: str):
    cookbook.show_graph("starting_graph", starting_graph, inp_value="{:.3f}")
    observed_graph: nx.DiGraph = bany.cmd.solve.network.algo.aggregate_quantity_along_depth(
        starting_graph, key, out, inplace=True
    )
    cookbook.show_graph("expected_graph", expected_graph, inp_value="{:.3f}", out_value="{:.5f}")
    cookbook.show_graph("observed_graph", observed_graph, inp_value="{:.3f}", out_value="{:.5f}")
    node_match = nx.algorithms.isomorphism.numerical_node_match([key, out], [0.0, 0.0])
    assert nx.is_isomorphic(observed_graph, expected_graph, node_match=node_match)


def test_is_leaf_node():
    graph = cookbook.make_graph(nodes=[("A", {}), ("B", {}), ("C", {})], edges=[("A", "B"), ("B", "C")])
    assert bany.cmd.solve.network.algo.is_leaf_node(graph, "C")
    assert bany.cmd.solve.network.algo.is_leaf_node(graph, "A") is False
    assert bany.cmd.solve.network.algo.is_leaf_node(graph, "B") is False
