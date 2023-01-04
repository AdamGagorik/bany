"""
Methods for creating a graph representation of the problem.
"""
import copy
import functools
import inspect
import logging
import operator
import typing

import networkx as nx
import networkx.exception
import pandas as pd

from bany.cmd.solve.network import validate
from bany.cmd.solve.network.attrs import node_attrs


def get_graph_root(graph: nx.DiGraph) -> typing.Any:
    """
    Assume the graph is a rooted tree and find the root node.
    """
    for n in nx.topological_sort(graph):
        return n


def create(frame: pd.DataFrame) -> nx.DiGraph:
    """
    Transform the input data into a graph object.

    Parameters:
        frame: A dataframe with the data to build the DAG.

    Returns:
        The graph that was constructed.
    """
    attrs = [
        f
        for f in node_attrs.subset()
        if f.column
        not in [
            node_attrs.label.column,
        ]
    ]

    graph = nx.DiGraph()
    for index, data in frame.iterrows():
        label = data[node_attrs.label.column]
        graph.add_node(label, **{attr.column: data.get(attr.column, default=attr.value) for attr in attrs})

    for index, data in frame.iterrows():
        label = data[node_attrs.label.column]
        for child in data.get("children", default=()):
            if label not in graph or child not in graph:
                raise ValueError(f"can not create edge with missing nodes! {label} -> {child}")
            else:
                graph.add_edge(label, child)

    source = get_graph_root(graph)
    depths = networkx.single_source_shortest_path_length(graph, source)
    for label, level in depths.items():
        graph.nodes[label].update(level=level)

    if not validate.validate(
        graph,
        nx.algorithms.is_directed_acyclic_graph,
        validate.network_has_no_cycles,
        validate.network_has_no_orphan_children,
        validate.network_children_only_have_single_parent,
        lambda g: validate.network_child_node_values_sum_to_parent_node_value(g, node_attrs.current_value.column),
    ):
        raise ValueError("invalid network")

    # normalize optimal ratio
    graph = normalize(graph, inplace=True, key=node_attrs.optimal_ratio.column, out=node_attrs.optimal_ratio.column)

    # calculate current ratio
    graph = normalize(graph, inplace=True, key=node_attrs.current_value.column, out=node_attrs.current_ratio.column)

    # compute the product ratio
    graph = aggregate_quantity_along_depth(
        graph, inplace=True, key=node_attrs.optimal_ratio.column, out=node_attrs.product_ratio.column
    )

    # compute the optimal values
    total = (
        aggregate_quantity(graph, key=node_attrs.amount_to_add.column)
        + graph.nodes[source][node_attrs.current_value.column]
    )

    graph = node_apply(
        graph, inplace=True, func=lambda product_ratio: total * product_ratio, out=node_attrs.optimal_value.column
    )

    if not validate.validate(
        graph,
        lambda g: validate.network_sums_to_100_percent_at_each_level(g, node_attrs.optimal_ratio.column, 1.0),
        lambda g: validate.network_sums_to_100_percent_at_each_level(g, node_attrs.current_ratio.column, 1.0),
    ):
        raise ValueError("invalid network")

    return graph


def normalize(
    graph: nx.DiGraph, key: str, out: str = None, levels: int | list[int] | None = None, inplace: bool = True
) -> nx.DiGraph:
    """
    Make it so the amounts at each level sum to 100 percent.

    Parameters:
        graph: The DAG to normalize.
        key: The name of the attribute to normalize.
        out: The name of the attribute to store results under.
        levels: The level(s) of the tree to operate on or None to normalize attrs levels.
        inplace: Should the operation happen in place or on a copy?

    Returns:
        The modified graph, with the value normalized.
    """
    out = out if out is not None else key

    if not inplace:
        graph = copy.deepcopy(graph)

    if isinstance(levels, int):
        levels = [levels]

    source = get_graph_root(graph)
    values = nx.get_node_attributes(graph, key)
    depths = networkx.single_source_shortest_path_length(graph, source)
    dframe = pd.DataFrame(depths, index=["level"]).T

    if levels is not None:
        dframe = dframe[dframe["level"].isin(levels)]

    if not dframe.empty:
        for level, group in dframe.groupby(by="level"):
            group["values"] = group.index.map(values)
            total = group["values"].sum()
            if total > 0:
                group["normed"] = group["values"] / total
            else:
                group["normed"] = 0.0

            for n, d in group.iterrows():
                graph.nodes[n][out] = d["normed"]

    return graph


def node_apply(
    graph: nx.DiGraph, func: typing.Callable, out: str, fresh: bool = False, inplace: bool = False
) -> nx.DiGraph:
    """
    Apply the given function over the nodes (in no particular order).

    Parameters:
        graph: The DAG to traverse.
        func: A function that recieves node attributes as keyword arguments.
        out: The name of the node attribute to store results under.
        fresh: Store the results in a new graph with empty attributes.
        inplace: Should the operation happen in place or on a copy?
    """
    if fresh:
        out_graph = graph.__class__()
        out_graph.add_nodes_from(graph)
        out_graph.add_edges_from(graph.edges)
    else:
        if not inplace:
            out_graph = copy.deepcopy(graph)
        else:
            out_graph = graph

    sig = list(inspect.signature(func).parameters.keys())
    if not sig:
        raise ValueError("func has no parameters")

    for node in graph.nodes:
        try:
            kwargs = {name: graph.nodes[node][name] for name in sig}
        except KeyError:
            logging.error("expected node attributes: %s", ", ".join(sig))
            logging.error("observed node attributes: %s", ", ".join(graph.nodes[node].keys()))
            raise AttributeError("can not call apply with function, node is missing attributes!")

        out_graph.nodes[node][out] = func(**kwargs)

    return out_graph


def aggregate_quantity(
    graph: nx.DiGraph, key: str, reduce: typing.Callable = operator.add, leaves: bool = False
) -> typing.Any:
    """
    Traverse the graph, reducing the node quantity at the key.

    Parameters:
        graph: The DAG to traverse.
        key: The name of the node attribute to aggregate.
        reduce: A function taking two values and returning one value.
        leaves: Aggregate the quantity only over the nodes that are leaves.

    Returns:
        The value of the aggregated quantity.
    """
    if not leaves:
        return functools.reduce(reduce, nx.get_node_attributes(graph, key).values())
    else:
        # noinspection PyCallingNonCallable
        attrs = (graph.nodes[n][key] for n in graph.nodes() if graph.out_degree(n) == 0 and graph.in_degree(n) == 1)
        return functools.reduce(reduce, attrs)


def aggregate_quantity_along_depth(
    graph: nx.DiGraph, key: str, out: str = None, reduce: typing.Callable = operator.mul, inplace: bool = True
) -> nx.DiGraph:
    """
    Traverse the graph in a depth first manner, reducing the node quantity at the key.

    Parameters:
        graph: The DAG to traverse.
        key: The name of the node attribute to aggregate.
        out: The name of the node attribute to store results under.
        reduce: A function taking two values and returning one value.
        inplace: Should the operation happen in place or on a copy?

    Returns:
        The modified graph, with the value normalized.
    """
    out = out if out is not None else key

    if not inplace:
        graph = copy.deepcopy(graph)

    source = get_graph_root(graph)
    graph.nodes[source][out] = graph.nodes[source][key]
    for e1, e2 in nx.dfs_edges(graph, source=source):
        v1 = graph.nodes[e1].get(out, 1.0)
        v2 = graph.nodes[e2].get(key, 1.0)
        graph.nodes[e1][out] = v1
        graph.nodes[e2][out] = reduce(v1, v2)

    return graph


def is_leaf_node(graph: nx.DiGraph, node: str):
    """
    An add_properties filter to check if node is a leaf node.
    """
    # noinspection PyCallingNonCallable
    return graph.out_degree(node) == 0 and graph.in_degree(node) == 1
