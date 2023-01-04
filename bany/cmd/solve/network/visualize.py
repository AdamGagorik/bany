"""
Methods for creating a graph representation of the problem.
"""
import dataclasses
import io

import networkx as nx
import networkx.exception

from bany.cmd.solve.network import algo
from bany.cmd.solve.network.attrs import DISPLAY_ALL
from bany.cmd.solve.network.attrs import DISPLAY_INP
from bany.cmd.solve.network.attrs import DISPLAY_OUT
from bany.cmd.solve.network.attrs import node_attrs
from bany.core.logger import logger


FORMATS_ALL = {f.column: f.display for f in node_attrs.subset(filters=DISPLAY_ALL)}
FORMATS_INP = {f.column: f.display for f in node_attrs.subset(filters=DISPLAY_INP)}
FORMATS_OUT = {f.column: f.display for f in node_attrs.subset(filters=DISPLAY_OUT)}


def log(key: str, graph: nx.DiGraph, **kwargs):
    """
    Display the graph using ASCII art using logger.
    """
    logger.info("%s:\n%s", key, text(graph, **kwargs))


def text(graph: nx.DiGraph, attrs: bool = False, **kwargs) -> str:
    """
    Display the graph using ASCII art.

    Parameters:
        graph: The DAG to display with ASCII art.
        attrs: Display all node attributes for nodes?
        kwargs: Node attributes to display and their format strings.

    Returns:
        The graph formatted as an ASCII string.
    """
    source = algo.get_graph_root(graph)
    if attrs:
        return TextDisplayer(graph=graph, attrs=True)(source)
    else:
        return TextDisplayer(graph=graph, attrs=kwargs)(source)


@dataclasses.dataclass()
class TextDisplayer:
    """
    Helper class to display DAG as ASCII Art.
    """

    graph: nx.DiGraph
    CROSS: str = " ├─"
    FINAL: str = " └─"
    SPACE: str = "   "
    VLINE: str = " │ "
    attrs: dict | bool = dataclasses.field(default_factory=dict)
    stream: io.StringIO = dataclasses.field(default_factory=io.StringIO)
    depth: int = None
    width: int = None
    source: str = None

    def __call__(self, *sources) -> str:
        self.stream = io.StringIO()
        self.depth = networkx.dag_longest_path_length(self.graph)
        self.width = max(len(str(n)) for n in self.graph.nodes)
        for source in sources:
            self.source = source
            self._write_node(source, "")
        return self.stream.getvalue()

    def _write_node(self, label: str, indent: str):
        if label in self.graph:
            self._write_name(label)
            children = list(self.graph.successors(label))
            for i, child in enumerate(self.graph.successors(label)):
                self._write_child_node(child, indent, i == len(children) - 1)
        else:
            label = label if label is not None else "?"
            self.stream.write(f"{label} [missing]\n")

    def _write_name(self, label):
        if self.attrs:
            level = len(nx.shortest_path(self.graph, self.source, label))
            width = 3 * (self.depth + 1) + 1 - 3 * level + self.width
            self.stream.write(f"{label:<{width}}")
            for key, fmt in self._get_node_attrs(label):
                try:
                    val = fmt.format(self.graph.nodes[label][key])
                except KeyError:
                    # noinspection PyBroadException
                    try:
                        val = "[%s]" % ((len(fmt.format(0)) - 2) * "?")
                    except Exception:
                        val = "?"
                self.stream.write(f" {key}={val}")
            self.stream.write("\n")
        else:
            self.stream.write(f"{label}\n")

    def _get_node_attrs(self, label):
        if isinstance(self.attrs, dict):
            for n, f in self.attrs.items():
                yield n, f if f is not None else "{}"
        else:
            for n in self.graph.nodes[label].keys():
                yield n, "{}"

    def _write_child_node(self, label: str, indent: str, last: bool):
        self.stream.write(indent)

        if last:
            self.stream.write(self.FINAL)
            indent += self.SPACE
        else:
            self.stream.write(self.CROSS)
            indent += self.VLINE

        self._write_node(label, indent)
