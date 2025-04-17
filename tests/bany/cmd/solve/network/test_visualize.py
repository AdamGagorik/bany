"""
Unit tests for module.
"""

import logging

import networkx as nx
import pytest

import bany.cmd.solve.network.visualize
import tests.bany.cmd.cookbook as cookbook


@pytest.mark.parametrize(
    "graph,attrs",
    [
        (
            cookbook.make_graph(
                nodes=[
                    ("0", {"value": 8.00}),
                    ("A", {"value": 2.00}),
                    ("B", {"value": 2.00}),
                    ("C", {"value": 4.00}),
                    ("D", {"value": 4.00}),
                    ("E", {"value": 4.00}),
                ],
                edges=[("0", "A"), ("0", "B"), ("0", "C"), ("C", "D"), ("C", "E")],
            ),
            {"value": "{:.3f}", "other": "{:.3f}"},
        ),
    ],
)
def test_text(graph: nx.DiGraph, attrs: dict):
    logging.debug("\n%s", bany.cmd.solve.network.visualize.text(graph, **attrs))
