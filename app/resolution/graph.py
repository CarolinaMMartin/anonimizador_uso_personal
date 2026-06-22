"""Grafo de menciones y componentes conexas."""
import networkx as nx

from app.models.schemas import Mention


def build_graph(
    mentions: list[Mention],
    edges: list[tuple[str, str, float, str]],
) -> nx.Graph:
    g = nx.Graph()
    for m in mentions:
        g.add_node(m.id, mention=m)
    for a, b, weight, reason in edges:
        g.add_edge(a, b, weight=weight, reason=reason)
    return g


def connected_components(g: nx.Graph) -> list[list[str]]:
    return [list(c) for c in nx.connected_components(g) if len(c) >= 1]
