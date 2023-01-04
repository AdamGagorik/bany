"""
Methods for creating a graph representation of the problem.
"""
import logging

import networkx as nx
import networkx.exception
import numpy as np
import pandas as pd

from bany.cmd.solve.network import algo
from bany.core.logger import logger


def validate(graph: nx.DiGraph, *checks) -> bool:
    """
    Check each check in turn.

    Parameters:
        graph: The network to validate.
        checks: Functions that take a graph and return True if graph is valid.

    Returns:
        True if the network passes all the checks.
    """
    valid = True
    # noinspection PyBroadException
    try:
        for check in checks:
            if not check(graph):
                valid = False
    except Exception:
        logging.exception("caught exception while checking graph!")
        valid = False
    return valid


def network_has_no_cycles(graph: nx.DiGraph) -> bool:
    """
    The network is a directed acyclic graph?
    """
    try:
        cycle = nx.algorithms.find_cycle(graph, orientation="ignore")
        logging.error("network cycle found!")
        for edge in cycle:
            logging.error("edge: %s -> %s", *edge[:2])
        return False
    except networkx.exception.NetworkXNoCycle:
        return True


def network_has_no_orphan_children(graph: nx.DiGraph) -> bool:
    """
    All children in the network have a parent?
    """
    graph = graph.to_undirected(as_view=True)
    connected = nx.is_connected(graph)
    if not connected:
        logging.error("network is not connected!")
        for subgraph in nx.connected_components(graph):
            logging.error("sub graph: %s", subgraph)
        return False
    else:
        return True


def network_children_only_have_single_parent(graph: nx.DiGraph) -> bool:
    """
    All children in the network have a single parent?
    """
    valid = True
    if len(graph) > 1:
        # noinspection PyTypeChecker
        for n, degree in graph.in_degree:
            if degree > 1:
                logging.error("degree %d > 1 for node: %s", degree, n)
                valid = False

    if not valid:
        logging.error("nodes have multiple predecessors!")

    return valid


def network_sums_to_100_percent_at_each_level(graph: nx.DiGraph, key: str, expected: float = 1.0) -> bool:
    """
    The fraction desired at each level sums to 100 percent?
    """
    source = algo.get_graph_root(graph)
    values = nx.get_node_attributes(graph, key)
    depths = networkx.single_source_shortest_path_length(graph, source)
    totals = pd.DataFrame(depths, index=[0]).T.groupby(by=0).apply(lambda group: sum(group.index.map(values)))
    is_100 = np.isclose(totals.values, expected, rtol=1.0e-5, atol=1.0e-8)
    if not np.all(is_100):
        for level, level_is_100 in enumerate(is_100):
            if not level_is_100:
                logging.error("%s does not sum to 100 for level %d", key, level)
        return False
    else:
        return True


def network_child_node_values_sum_to_parent_node_value(graph: nx.DiGraph, key: str) -> bool:
    """
    For a given node, ensure that parent[attr] = sum(child[attr] for child in node).
    """

    def it():
        source = algo.get_graph_root(graph)
        for node, successors in nx.algorithms.bfs_successors(graph, source):
            p_value = graph.nodes[node].get(key, 0.0)
            c_value = sum(graph.nodes[child].get(key, 0.0) for child in successors)
            yield dict(node=node, p_value=p_value, c_value=c_value)

    valid = True
    frame = pd.DataFrame(it())
    if not frame.empty:
        frame["is_close"] = np.isclose(frame.p_value, frame.c_value, rtol=1.0e-5, atol=1.0e-8)
        for index, row in frame.iterrows():
            if not row.is_close:
                valid = False
                logger.error("%s does not sum over children to the expected amount for node %s!", key, row.node)
                logger.error("expected: %.3e", row.p_value)
                logger.error("observed: %.3e", row.c_value)

    return valid
