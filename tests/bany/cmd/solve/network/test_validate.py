"""
Unit tests for module.
"""

import unittest.mock

import networkx as nx
import pytest

import bany.cmd.solve.network.validate
import tests.bany.cmd.cookbook as cookbook


def test_validate():
    mock_g = nx.DiGraph()
    mock_a = unittest.mock.MagicMock(return_value=True)
    mock_b = unittest.mock.MagicMock(return_value=True)
    assert bany.cmd.solve.network.validate.validate(mock_g, mock_a, mock_b)
    mock_a.assert_called_once_with(mock_g)
    mock_b.assert_called_once_with(mock_g)


@pytest.mark.parametrize(
    "graph,expected_valid",
    [
        (nx.DiGraph([(1, 2), (2, 3), (3, 4)]), True),
        (nx.DiGraph([(1, 2), (2, 3), (3, 1)]), False),
    ],
)
def test_network_has_no_cycles(graph: nx.DiGraph, expected_valid: bool):
    cookbook.show_graph("graph", graph)
    observed_valid: bool = bany.cmd.solve.network.validate.network_has_no_cycles(graph)
    assert observed_valid == expected_valid


@pytest.mark.parametrize(
    "graph,expected_valid",
    [
        (nx.DiGraph({0: [1, 2], 3: [0]}), True),
        (nx.DiGraph({0: [1, 2], 3: [4]}), False),
    ],
)
def test_network_has_no_orphan_children(graph: nx.DiGraph, expected_valid: bool):
    cookbook.show_graph("graph", graph)
    observed_valid: bool = bany.cmd.solve.network.validate.network_has_no_orphan_children(graph)
    assert observed_valid == expected_valid


@pytest.mark.parametrize(
    "graph,expected_valid",
    [
        (nx.DiGraph([(1, 2), (1, 3), (1, 4)]), True),
        (nx.DiGraph([(1, 2), (1, 3), (4, 2)]), False),
    ],
)
def test_network_children_only_have_single_parent(graph: nx.DiGraph, expected_valid: bool):
    cookbook.show_graph("graph", graph)
    observed_valid: bool = bany.cmd.solve.network.validate.network_children_only_have_single_parent(graph)
    assert observed_valid == expected_valid


@pytest.mark.parametrize(
    "graph,key,expected_valid",
    [
        (
            cookbook.make_graph(
                nodes=[
                    ("0", {"value": 1.00}),
                    ("A", {"value": 0.40}),
                    ("B", {"value": 0.25}),
                    ("C", {"value": 0.35}),
                ],
                edges=[("0", "A"), ("0", "B"), ("0", "C")],
            ),
            "value",
            True,
        ),
        (
            cookbook.make_graph(
                nodes=[
                    ("0", {"value": 100.0}),
                    ("A", {"value": 100.0}),
                    ("B", {"value": 100.0}),
                    ("C", {"value": 100.0}),
                ],
                edges=[("0", "A"), ("0", "B"), ("0", "C")],
            ),
            "value",
            False,
        ),
        (
            cookbook.make_graph(
                nodes=[
                    ("0", {"value": 100.0}),
                    ("A", {"value": 0.1}),
                    ("B", {"value": 0.1}),
                    ("C", {"value": 0.1}),
                ],
                edges=[("0", "A"), ("0", "B"), ("0", "C")],
            ),
            "value",
            False,
        ),
    ],
)
def test_network_sums_to_100_percent_at_each_level(graph: nx.DiGraph, key: str, expected_valid: bool):
    cookbook.show_graph("graph", graph)
    observed_valid: bool = bany.cmd.solve.network.validate.network_sums_to_100_percent_at_each_level(graph, key)
    assert observed_valid == expected_valid


@pytest.mark.parametrize(
    "graph,key,expected_valid",
    [
        (
            cookbook.make_graph(
                nodes=[
                    ("W", {"value": 1.00}),
                    ("X", {"value": 0.40}),
                    ("Y", {"value": 0.25}),
                    ("Z", {"value": 0.35}),
                    ("T", {"value": 0.10}),
                    ("U", {"value": 0.20}),
                    ("V", {"value": 0.05}),
                ],
                edges=[("W", "X"), ("W", "Y"), ("W", "Z"), ("Z", "T"), ("Z", "U"), ("Z", "V")],
            ),
            "value",
            True,
        ),
        (
            cookbook.make_graph(
                nodes=[
                    ("N", {"value": 1.00}),
                    ("M", {"value": 0.40}),
                    ("O", {"value": 0.25}),
                ],
                edges=[("M", "N"), ("M", "O")],
            ),
            "value",
            False,
        ),
    ],
)
def test_network_child_node_values_sum_to_parent_node_value(graph: nx.DiGraph, key: str, expected_valid: True):
    cookbook.show_graph("graph", graph)
    observed_valid: bool = bany.cmd.solve.network.validate.network_child_node_values_sum_to_parent_node_value(
        graph, key
    )
    assert observed_valid == expected_valid
