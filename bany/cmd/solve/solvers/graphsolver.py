"""
Solve the bucket problem over a hierarchy of buckets.

For example, given the following input::

A    level=[0] current_value=[ 4,000.00] optimal_ratio=[1.000] amount_to_add=[ 1,000.00]
 ├─0 level=[1] current_value=[ 2,000.00] optimal_ratio=[0.500] amount_to_add=[     0.00]
 ├─1 level=[1] current_value=[ 1,000.00] optimal_ratio=[0.250] amount_to_add=[     0.00]
 └─2 level=[1] current_value=[ 1,000.00] optimal_ratio=[0.250] amount_to_add=[     0.00]

Compute the amount to add to each bucket::

A    level=[0] results_value=[ 5,000.00] results_ratio=[1.000] amount_to_add=[     0.00]
 ├─0 level=[1] results_value=[ 2,500.00] results_ratio=[0.500] amount_to_add=[   500.00]
 ├─1 level=[1] results_value=[ 1,250.00] results_ratio=[0.250] amount_to_add=[   250.00]
 └─2 level=[1] results_value=[ 1,250.00] results_ratio=[0.250] amount_to_add=[   250.00]
"""
import copy
import typing

import networkx as nx

import bany.cmd.solve.network.algo
import bany.cmd.solve.network.validate
from bany.cmd.solve.network.attrs import node_attrs
from bany.cmd.solve.solvers.basesolver import BucketSolver
from bany.cmd.solve.solvers.bucketdata import BucketSystem
from bany.cmd.solve.solvers.constrained import BucketSolverConstrained


def solve(
    graph: nx.DiGraph,
    solver: type[BucketSolver] = BucketSolverConstrained,
    inplace: bool = False,
    max_attempts: int = 10,
    **kwargs,
) -> nx.DiGraph:
    """
    Solve the bucket problem over a hierarchy of buckets.

    Parameters:
        graph: The DAG to process.
        solver: The bucket solver during traversal.
        inplace: Should the operation happen in place or on a copy?
        max_attempts: The maximum allowed passes through the network.
        **kwargs: Extra key word arguments to the solver's solve method.

    Returns:
        The modified graph, with the results_value and results_delta updated.
    """
    if not inplace:
        graph = copy.deepcopy(graph)

    # applying the solver here allows initial redistribution for unconstrained solvers
    _apply_solver_over_graph(graph, solver, lambda a: a >= 0, **kwargs)
    for attempt in range(max_attempts):
        stop_algorithm = _apply_solver_over_graph(graph, solver, lambda a: a > 0, **kwargs)
        if stop_algorithm:
            break
    else:
        raise RuntimeError("max attempts reached in network solver!")

    graph = _finalize_graph(graph)

    # validate the results
    if not bany.cmd.solve.network.validate.validate(
        graph,
        lambda g: bany.cmd.solve.network.validate.network_sums_to_100_percent_at_each_level(
            g, node_attrs.results_ratio.column, 1.0
        ),
        lambda g: bany.cmd.solve.network.validate.network_child_node_values_sum_to_parent_node_value(
            g, node_attrs.results_value.column
        ),
    ):
        raise ValueError("invalid network (after solver ran)")

    return graph


def _apply_solver_over_graph(
    graph: nx.DiGraph, solver: type[BucketSolver], condition: typing.Callable, **kwargs
) -> bool:
    """
    Walk the graph from the bottom up, solving the bucket problem over the set of children for each parent.

    Parameters:
        graph: The DAG to process.
        solver: The bucket solver during traversal.
        condition: The continue condition to apply on the amount to add.
        **kwargs: Extra key word arguments to the solver's solve method.

    Returns:
        True if the continue condition was never met.
    """
    stop_algorithm = True
    # walk the graph from the bottom up, solving the bucket problem set of children
    source = bany.cmd.solve.network.algo.get_graph_root(graph)
    for parent, children in reversed(list(nx.bfs_successors(graph, source))):
        amount_to_add = graph.nodes[parent][node_attrs.amount_to_add.column]

        if condition(amount_to_add):
            current_values = [graph.nodes[n][node_attrs.current_value.column] for n in children]
            optimal_ratios = [graph.nodes[n][node_attrs.optimal_ratio.column] for n in children]
            stop_algorithm = False

            # solve the bucket problem over the children
            system = BucketSystem.create(
                amount_to_add=amount_to_add,
                current_values=current_values,
                optimal_ratios=optimal_ratios,
                labels=children,
            )
            solved = solver.solve(system, **kwargs)

            # negate the amount to add, so we don't try to add it again on the next pass
            graph.nodes[parent][node_attrs.amount_to_add.column] = -amount_to_add

            # increment the amount to add value for the children of this node
            for i, child in enumerate(children):
                graph.nodes[child][node_attrs.amount_to_add.column] += solved.result_delta.values[i]

    return stop_algorithm


def _finalize_graph(graph: nx.DiGraph) -> nx.DiGraph:
    """
    Finalize the amount_to_add, results_value, and results_ratio column for the graph.

    Parameters:
        graph: The DAG to process.

    Returns:
        The processed DAG.
    """
    # finalize the amounts to add and the results_value column
    for node in graph:
        # noinspection PyCallingNonCallable
        if graph.out_degree(node):
            graph.nodes[node][node_attrs.amount_to_add.column] = 0
        else:
            graph.nodes[node][node_attrs.results_value.column] = (
                graph.nodes[node][node_attrs.current_value.column] + graph.nodes[node][node_attrs.amount_to_add.column]
            )

    source = bany.cmd.solve.network.algo.get_graph_root(graph)
    for parent, children in reversed(list(nx.bfs_successors(graph, source))):
        graph.nodes[parent][node_attrs.results_value.column] = sum(
            graph.nodes[child][node_attrs.results_value.column] for child in children
        )

    # calculate the final ratios for the results column
    graph = bany.cmd.solve.network.algo.normalize(
        graph, inplace=True, key=node_attrs.results_value.column, out=node_attrs.results_ratio.column
    )

    return graph
