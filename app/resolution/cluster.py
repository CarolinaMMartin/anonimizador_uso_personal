"""Clustering de menciones en identidades sugeridas."""
from collections import defaultdict

from app.anonymize.placeholders import build_detections_from_mentions
from app.models.schemas import Cluster, Confidence, Detection, Mention, Position
from app.resolution.graph import build_graph, connected_components
from app.resolution.normalize import get_surnames, normalize_mention, tokenize_name
from app.resolution.similarity import compute_edge, link_personas_near_identifier


def _best_confidence(reasons: list[str], scores: list[float]) -> Confidence:
    if "shared_identifier" in reasons or "exact" in reasons:
        return "alta"
    if "initials_match" in reasons or "fuzzy_high" in reasons:
        return "alta"
    if max(scores, default=0) >= 0.92:
        return "alta"
    if "shared_surname" in reasons or "proximity" in reasons:
        return "media"
    if max(scores, default=0) >= 0.85:
        return "media"
    return "baja"


def _exact_match_groups(mentions: list[Mention]) -> dict[tuple[str, str], list[Mention]]:
    groups: dict[tuple[str, str], list[Mention]] = defaultdict(list)
    for m in mentions:
        groups[(m.cat, normalize_mention(m.surface))].append(m)
    return groups


def _append_exact_edges(
    edges: list[tuple[str, str, float, str]],
    groups: dict[tuple[str, str], list[Mention]],
) -> None:
    for members in groups.values():
        if len(members) < 2:
            continue
        anchor = members[0]
        for m in members[1:]:
            edges.append((anchor.id, m.id, 1.0, "exact"))


def _try_edge(
    m1: Mention,
    m2: Mention,
    text: str,
    edges: list[tuple[str, str, float, str]],
    seen: set[tuple[str, str]],
) -> None:
    pair = (m1.id, m2.id) if m1.id < m2.id else (m2.id, m1.id)
    if pair in seen:
        return
    seen.add(pair)
    result = compute_edge(m1, m2, text)
    if result:
        weight, _conf, reason = result
        edges.append((m1.id, m2.id, weight, reason))


def build_edges(mentions: list[Mention], text: str) -> list[tuple[str, str, float, str]]:
    """Arma aristas para clustering sin comparar cada par de menciones (O(n²))."""
    edges: list[tuple[str, str, float, str]] = []
    groups = _exact_match_groups(mentions)
    _append_exact_edges(edges, groups)

    representatives = [members[0] for members in groups.values()]
    by_cat: dict[str, list[Mention]] = defaultdict(list)
    for rep in representatives:
        by_cat[rep.cat].append(rep)

    seen: set[tuple[str, str]] = set()
    for cat, cat_reps in by_cat.items():
        if cat == "PERSONA":
            buckets: dict[str, list[Mention]] = defaultdict(list)
            for rep in cat_reps:
                tokens = tokenize_name(normalize_mention(rep.surface))
                surnames = get_surnames(tokens)
                if not surnames:
                    key = tokens[0] if tokens else "_unknown"
                    buckets[key].append(rep)
                    continue
                for surname in surnames:
                    buckets[surname].append(rep)
            for bucket in buckets.values():
                for i, m1 in enumerate(bucket):
                    for m2 in bucket[i + 1 :]:
                        _try_edge(m1, m2, text, edges, seen)
        else:
            for i, m1 in enumerate(cat_reps):
                for m2 in cat_reps[i + 1 :]:
                    _try_edge(m1, m2, text, edges, seen)

    edges.extend(link_personas_near_identifier(mentions))
    return edges


def build_clusters(mentions: list[Mention], text: str) -> list[Cluster]:
    if not mentions:
        return []

    edges = build_edges(mentions, text)
    g = build_graph(mentions, edges)
    components = connected_components(g)

    mention_map = {m.id: m for m in mentions}
    clusters: list[Cluster] = []

    for idx, comp in enumerate(components):
        if len(comp) < 2:
            continue

        comp_mentions = [mention_map[mid] for mid in comp if mid in mention_map]
        if not comp_mentions:
            continue

        surfaces = list({m.surface.strip() for m in comp_mentions})
        # No sugerir grupos solo numéricos (2026, 3310)
        if all(s.isdigit() or (len(s) == 4 and s.isdigit()) for s in surfaces):
            continue
        if all(len(s) < 4 for s in surfaces):
            continue

        cat = comp_mentions[0].cat
        if cat == "DOMICILIO" and not any(
            len(s) > 15 or "calle" in s.lower() or "av" in s.lower() for s in surfaces
        ):
            continue
        reasons: list[str] = []
        scores: list[float] = []
        for a, b, w, r in edges:
            if a in comp and b in comp:
                reasons.append(r)
                scores.append(w)

        confidence = _best_confidence(reasons, scores)
        clusters.append(
            Cluster(
                cluster_id=f"sug_{idx}",
                cat=cat,
                mention_ids=[m.id for m in comp_mentions],
                surfaces=surfaces,
                confidence=confidence,
                status="suggested",
                reasons=list(set(reasons)),
            )
        )

    return clusters


def mentions_to_detections(
    mentions: list[Mention],
    label_mode: str,
    clusters: list[Cluster],
) -> list[Detection]:
    """Detecciones exactas (una por superficie única) para tabla."""
    return build_detections_from_mentions(mentions, label_mode)
