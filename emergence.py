"""
CivGraph -- Emergent properties detection, dynamics, and measurement.

Computes macro-level phenomena that arise from micro-level agent
interactions but cannot be predicted from any single agent's state.

Thirteen computed dimensions:

 1. Polarization Index          (Esteban-Ray / Axelrod cultural dynamics)
 2. Inequality Metrics          (Gini, Palma ratio, Matthew effect)
 3. Collective Intelligence     (Woolley et al. MIT, cognitive diversity)
 4. Social Contagion Risk       (Watts threshold cascade model)
 5. Network Resilience          (Barabasi percolation / scale-free fragility)
 6. Phase Transition Detection  (Granovetter / Centola critical mass)
 7. Echo Chamber Formation      (Sunstein / Pariser filter bubbles)
 8. Power Law Emergence         (Zipf / Pareto in influence & wealth)
 9. Institutional Trust Dynamics (Putnam / Fukuyama social capital)
10. Cultural Convergence        (Henrich dual-inheritance / Boyd-Richerson)
11. Information-Theoretic       (MI, transfer entropy, synergy -- Rosas 2020)
12. Norm Emergence              (Axelrod 1986, Bicchieri 2006)
13. Segregation Dynamics        (Schelling 1971)

Plus: downward causation, adaptive rewiring, inter-dimension coupling,
critical slowing down detection, and per-agent emergence attribution.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field

import networkx as nx


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _agents(G: nx.Graph) -> list:
    return [G.nodes[n]["agent"] for n in G.nodes]


def _safe_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def _gini(values: list[float]) -> float:
    """Gini coefficient (0 = perfect equality, 1 = perfect inequality)."""
    if not values or max(values) == 0:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    total = sum(sorted_v)
    if total == 0:
        return 0.0
    cum = 0.0
    gini_sum = 0.0
    for i, v in enumerate(sorted_v):
        cum += v
        gini_sum += (2 * (i + 1) - n - 1) * v
    return gini_sum / (n * total)


def _palma(values: list[float]) -> float:
    """Palma ratio: income share of top 10% / bottom 40%."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    bottom_40 = sum(s[: max(1, int(n * 0.4))])
    top_10 = sum(s[max(1, int(n * 0.9)):])
    return round(top_10 / max(0.001, bottom_40), 3)


def _entropy(probs: list[float]) -> float:
    """Shannon entropy in nats."""
    return -sum(p * math.log(p) for p in probs if p > 0)


def _mutual_information(xs: list, ys: list) -> float:
    """Discrete mutual information between two categorical sequences."""
    n = len(xs)
    if n == 0:
        return 0.0
    joint = Counter(zip(xs, ys))
    cx = Counter(xs)
    cy = Counter(ys)
    mi = 0.0
    for (x, y), count in joint.items():
        pxy = count / n
        px = cx[x] / n
        py = cy[y] / n
        if pxy > 0 and px > 0 and py > 0:
            mi += pxy * math.log(pxy / (px * py))
    return mi


def _lag1_autocorrelation(series: list[float]) -> float:
    """Lag-1 autocorrelation of a time series."""
    if len(series) < 3:
        return 0.0
    mean = sum(series) / len(series)
    var = sum((v - mean) ** 2 for v in series)
    if var == 0:
        return 0.0
    cov = sum((series[i] - mean) * (series[i + 1] - mean) for i in range(len(series) - 1))
    return cov / var


# ══════════════════════════════════════════════════════════════════════════════
# 1. POLARIZATION INDEX
#    Esteban-Ray (1994) measure adapted for opinion and political dimensions.
# ══════════════════════════════════════════════════════════════════════════════

def compute_polarization(G: nx.Graph) -> dict:
    agents = _agents(G)
    n = len(agents) or 1

    pol_counts = Counter(a.politics.value for a in agents)
    pol_values = {
        "far_left": -3, "left": -2, "center_left": -1, "center": 0,
        "center_right": 1, "right": 2, "far_right": 3,
    }
    alpha = 1.6
    er_sum = 0.0
    for label_i, count_i in pol_counts.items():
        pi = count_i / n
        xi = pol_values.get(label_i, 0)
        for label_j, count_j in pol_counts.items():
            pj = count_j / n
            xj = pol_values.get(label_j, 0)
            er_sum += (pi ** (1 + alpha)) * pj * abs(xi - xj)
    political_polarization = min(1.0, er_sum / 12.0)

    all_topics = set()
    for a in agents:
        all_topics.update(a.opinion_state.keys())

    topic_polarizations = {}
    for topic in all_topics:
        opinions = [a.opinion_state.get(topic, 0.0) for a in agents]
        extreme = sum(1 for o in opinions if abs(o) > 0.5)
        moderate = sum(1 for o in opinions if abs(o) <= 0.2)
        bimodality = extreme / max(1, moderate + extreme)
        variance = _safe_std(opinions) ** 2
        topic_polarizations[topic] = round(min(1.0, bimodality * 0.6 + variance * 0.4), 3)

    overall_opinion_pol = 0.0
    if topic_polarizations:
        overall_opinion_pol = sum(topic_polarizations.values()) / len(topic_polarizations)

    clan_pol = {}
    for a in agents:
        clan_pol.setdefault(a.clan, []).append(a.politics.numeric)
    clan_means = {c: sum(v) / len(v) for c, v in clan_pol.items()}
    clan_pairs = list(clan_means.values())
    inter_clan = 0.0
    count = 0
    for i in range(len(clan_pairs)):
        for j in range(i + 1, len(clan_pairs)):
            inter_clan += abs(clan_pairs[i] - clan_pairs[j])
            count += 1
    inter_clan_distance = inter_clan / max(1, count) / 6.0

    return {
        "political_polarization": round(political_polarization, 3),
        "opinion_polarization": round(overall_opinion_pol, 3),
        "topic_polarizations": topic_polarizations,
        "inter_clan_distance": round(inter_clan_distance, 3),
        "composite": round(
            political_polarization * 0.4 +
            overall_opinion_pol * 0.35 +
            inter_clan_distance * 0.25, 3
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2. INEQUALITY METRICS
# ══════════════════════════════════════════════════════════════════════════════

def compute_inequality(G: nx.Graph) -> dict:
    agents = _agents(G)

    economic = [a.capital.economic for a in agents]
    cultural = [a.capital.cultural for a in agents]
    influence = [a.influence for a in agents]
    total_cap = [a.capital.total_volume for a in agents]

    class_econ = {}
    for a in agents:
        cls = a.habitus.current_class.value
        class_econ.setdefault(cls, []).append(a.capital.economic)
    class_means = {c: round(sum(v) / len(v), 3) for c, v in class_econ.items()}

    degrees = [G.degree(nid) for nid in G.nodes]
    cap_vals = [G.nodes[nid]["agent"].capital.total_volume for nid in G.nodes]
    n = len(degrees)
    if n > 1 and _safe_std(degrees) > 0 and _safe_std(cap_vals) > 0:
        mean_d = sum(degrees) / n
        mean_c = sum(cap_vals) / n
        cov = sum((degrees[i] - mean_d) * (cap_vals[i] - mean_c) for i in range(n)) / n
        matthew_effect = cov / (_safe_std(degrees) * _safe_std(cap_vals))
    else:
        matthew_effect = 0.0

    return {
        "gini_economic": round(_gini(economic), 3),
        "gini_cultural": round(_gini(cultural), 3),
        "gini_influence": round(_gini(influence), 3),
        "gini_total": round(_gini(total_cap), 3),
        "palma_economic": _palma(economic),
        "palma_influence": _palma(influence),
        "matthew_effect": round(matthew_effect, 3),
        "class_economic_means": class_means,
        "composite": round(
            _gini(economic) * 0.3 +
            _gini(influence) * 0.3 +
            abs(matthew_effect) * 0.2 +
            min(1.0, _palma(economic) / 10) * 0.2, 3
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. COLLECTIVE INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

def compute_collective_intelligence(G: nx.Graph) -> dict:
    agents = _agents(G)
    n = len(agents) or 1

    avg_openness = sum(a.openness for a in agents) / n

    interest_counts = Counter()
    for a in agents:
        for interest in a.interests:
            interest_counts[interest] += 1
    total_interests = sum(interest_counts.values()) or 1
    interest_probs = [c / total_interests for c in interest_counts.values()]
    cognitive_diversity = _entropy(interest_probs) / math.log(max(2, len(interest_counts)))

    edu_counts = Counter(a.habitus.education_track.value for a in agents)
    edu_probs = [c / n for c in edu_counts.values()]
    education_diversity = _entropy(edu_probs) / math.log(max(2, len(edu_counts)))

    degrees = [G.degree(nid) for nid in G.nodes]
    max_deg = max(degrees) if degrees else 1
    deg_norm = [d / max_deg for d in degrees]
    degree_equity = 1 - _gini(deg_norm)

    cross_clan = 0
    total_edges = 0
    for u, v in G.edges():
        total_edges += 1
        if G.nodes[u]["agent"].clan != G.nodes[v]["agent"].clan:
            cross_clan += 1
    bridging_ratio = cross_clan / max(1, total_edges)

    avg_clustering = nx.average_clustering(G)
    sample_nodes = list(G.nodes)[:50]
    path_sum = 0
    path_count = 0
    for src in sample_nodes:
        lengths = nx.single_source_shortest_path_length(G, src, cutoff=10)
        for tgt, length in lengths.items():
            if src != tgt:
                path_sum += length
                path_count += 1
    avg_path = path_sum / max(1, path_count)
    small_world = avg_clustering / max(0.1, avg_path / 5)

    composite = (
        avg_openness * 0.15 +
        cognitive_diversity * 0.20 +
        education_diversity * 0.10 +
        degree_equity * 0.15 +
        bridging_ratio * 0.20 +
        min(1.0, small_world) * 0.20
    )

    return {
        "social_sensitivity": round(avg_openness, 3),
        "cognitive_diversity": round(cognitive_diversity, 3),
        "education_diversity": round(education_diversity, 3),
        "degree_equity": round(degree_equity, 3),
        "bridging_ratio": round(bridging_ratio, 3),
        "small_world_coefficient": round(small_world, 3),
        "avg_clustering": round(avg_clustering, 4),
        "avg_path_length": round(avg_path, 2),
        "composite": round(min(1.0, composite), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 4. SOCIAL CONTAGION SUSCEPTIBILITY
# ══════════════════════════════════════════════════════════════════════════════

def compute_contagion_susceptibility(G: nx.Graph) -> dict:
    agents = _agents(G)
    n = len(agents) or 1

    thresholds = []
    for a in agents:
        threshold = 1 - (a.openness * 0.6 + a.assertiveness * 0.4)
        thresholds.append(threshold)
    avg_threshold = sum(thresholds) / n
    vulnerable_fraction = sum(1 for t in thresholds if t < 0.4) / n

    degrees = [(nid, G.degree(nid)) for nid in G.nodes]
    degrees.sort(key=lambda x: x[1], reverse=True)
    top_hubs = [nid for nid, _ in degrees[:5]]
    cascade_reach = set()
    for hub in top_hubs:
        lengths = nx.single_source_shortest_path_length(G, hub, cutoff=3)
        cascade_reach.update(lengths.keys())
    hub_3hop_reach = len(cascade_reach) / n

    open_nodes = [nid for nid in G.nodes if G.nodes[nid]["agent"].openness > 0.3]
    if len(open_nodes) > 1:
        sub = G.subgraph(open_nodes)
        open_density = nx.density(sub)
    else:
        open_density = 0.0

    district_suscept = {}
    district_agents = {}
    for a in agents:
        district_agents.setdefault(a.district, []).append(a)
    for district, d_agents in district_agents.items():
        avg_open = sum(a.openness for a in d_agents) / len(d_agents)
        avg_assert = sum(a.assertiveness for a in d_agents) / len(d_agents)
        district_suscept[district] = round(avg_open * 0.6 + avg_assert * 0.4, 3)

    composite = (
        (1 - avg_threshold) * 0.25 +
        vulnerable_fraction * 0.25 +
        hub_3hop_reach * 0.25 +
        open_density * 0.25
    )

    return {
        "avg_activation_threshold": round(avg_threshold, 3),
        "vulnerable_fraction": round(vulnerable_fraction, 3),
        "hub_3hop_reach": round(hub_3hop_reach, 3),
        "open_subgraph_density": round(open_density, 4),
        "district_susceptibility": district_suscept,
        "composite": round(min(1.0, composite), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. NETWORK RESILIENCE
# ══════════════════════════════════════════════════════════════════════════════

def compute_network_resilience(G: nx.Graph) -> dict:
    n = G.number_of_nodes()
    if n < 5:
        return {"random_robustness": 0, "targeted_fragility": 0, "composite": 0}

    rng = random.Random(42)
    random_removal = rng.sample(list(G.nodes), max(1, n // 10))
    G_random = G.copy()
    G_random.remove_nodes_from(random_removal)
    largest_orig = max(len(c) for c in nx.connected_components(G))
    if G_random.number_of_nodes() > 0:
        largest_random = max(len(c) for c in nx.connected_components(G_random))
    else:
        largest_random = 0
    random_robustness = largest_random / max(1, largest_orig)

    degrees_sorted = sorted([(nid, G.degree(nid)) for nid in G.nodes],
                            key=lambda x: x[1], reverse=True)
    targeted_removal = [nid for nid, _ in degrees_sorted[: max(1, n // 20)]]
    G_targeted = G.copy()
    G_targeted.remove_nodes_from(targeted_removal)
    if G_targeted.number_of_nodes() > 0:
        largest_targeted = max(len(c) for c in nx.connected_components(G_targeted))
    else:
        largest_targeted = 0
    targeted_fragility = 1 - (largest_targeted / max(1, largest_orig))

    avg_clustering = nx.average_clustering(G)

    try:
        assortativity = nx.degree_assortativity_coefficient(G)
    except Exception:
        assortativity = 0.0

    try:
        art_points = list(nx.articulation_points(G))
        bridge_fraction = len(art_points) / n
        n_articulation = len(art_points)
    except Exception:
        bridge_fraction = 0.0
        n_articulation = 0

    composite = (
        random_robustness * 0.25 +
        (1 - targeted_fragility) * 0.30 +
        avg_clustering * 0.20 +
        (1 - bridge_fraction) * 0.15 +
        (1 - abs(assortativity)) * 0.10
    )

    return {
        "random_robustness": round(random_robustness, 3),
        "targeted_fragility": round(targeted_fragility, 3),
        "avg_clustering": round(avg_clustering, 4),
        "degree_assortativity": round(assortativity, 4),
        "bridge_fraction": round(bridge_fraction, 3),
        "articulation_points": n_articulation,
        "composite": round(min(1.0, composite), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 6. PHASE TRANSITION DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def compute_phase_transitions(G: nx.Graph) -> dict:
    agents = _agents(G)
    n = len(agents) or 1

    pol_counts = Counter(a.politics.value for a in agents)
    largest_faction_size = max(pol_counts.values()) / n
    political_criticality = min(1.0, largest_faction_size / 0.25) if largest_faction_size < 0.5 else 1.0

    topic_criticality = {}
    for a in agents:
        for topic, opinion in a.opinion_state.items():
            topic_criticality.setdefault(topic, {"support": 0, "oppose": 0, "total": 0})
            topic_criticality[topic]["total"] += 1
            if opinion > 0.3:
                topic_criticality[topic]["support"] += 1
            elif opinion < -0.3:
                topic_criticality[topic]["oppose"] += 1

    topic_tipping = {}
    for topic, counts in topic_criticality.items():
        if counts["total"] == 0:
            continue
        max_side = max(counts["support"], counts["oppose"]) / counts["total"]
        balance = 1 - abs(counts["support"] - counts["oppose"]) / max(1, counts["total"])
        topic_tipping[topic] = round(min(1.0, max_side * 0.5 + balance * 0.5), 3)

    upward_pressure = sum(1 for a in agents if a.habitus.aspiration_gap > 0) / n
    downward_pressure = sum(1 for a in agents if a.habitus.aspiration_gap < 0) / n
    mobility_tension = abs(upward_pressure - downward_pressure) + min(upward_pressure, downward_pressure)

    density = nx.density(G)
    percolation_threshold = 1 / max(1, n)
    percolation_margin = (density - percolation_threshold) / max(0.001, density)

    composite = (
        (1 - percolation_margin) * 0.2 +
        political_criticality * 0.25 +
        mobility_tension * 0.25 +
        (sum(topic_tipping.values()) / max(1, len(topic_tipping)) if topic_tipping else 0) * 0.30
    )

    return {
        "political_criticality": round(political_criticality, 3),
        "largest_faction_share": round(largest_faction_size, 3),
        "topic_tipping_points": topic_tipping,
        "upward_mobility_pressure": round(upward_pressure, 3),
        "downward_mobility_pressure": round(downward_pressure, 3),
        "mobility_tension": round(mobility_tension, 3),
        "percolation_margin": round(percolation_margin, 3),
        "composite": round(min(1.0, max(0.0, composite)), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 7. ECHO CHAMBER FORMATION
# ══════════════════════════════════════════════════════════════════════════════

def compute_echo_chambers(G: nx.Graph) -> dict:
    agents = _agents(G)
    n = len(agents) or 1

    same_pol = 0
    near_pol = 0
    same_class = 0
    intra_clan = 0
    intra_district = 0
    total_edges = G.number_of_edges() or 1

    for u, v in G.edges():
        au = G.nodes[u]["agent"]
        av = G.nodes[v]["agent"]
        if au.politics == av.politics:
            same_pol += 1
        elif abs(au.politics.numeric - av.politics.numeric) <= 1:
            near_pol += 1
        if au.habitus.current_class == av.habitus.current_class:
            same_class += 1
        if au.clan == av.clan:
            intra_clan += 1
        if au.district == av.district:
            intra_district += 1

    political_homophily = (same_pol + near_pol * 0.5) / total_edges
    class_homophily = same_class / total_edges
    clan_insularity = intra_clan / total_edges
    district_segregation = intra_district / total_edges

    all_topics = set()
    for a in agents:
        all_topics.update(a.opinion_state.keys())

    topic_echo = {}
    for topic in all_topics:
        support = []
        oppose = []
        neutral = []
        for nid in G.nodes:
            op = G.nodes[nid]["agent"].opinion_state.get(topic, 0)
            if op > 0.2:
                support.append(nid)
            elif op < -0.2:
                oppose.append(nid)
            else:
                neutral.append(nid)
        comm_list = [s for s in [set(support), set(oppose), set(neutral)] if s]
        if len(comm_list) >= 2:
            try:
                mod = nx.community.modularity(G, comm_list)
                topic_echo[topic] = round(max(0, mod), 3)
            except Exception:
                topic_echo[topic] = 0.0
        else:
            topic_echo[topic] = 0.0

    avg_echo = sum(topic_echo.values()) / max(1, len(topic_echo)) if topic_echo else 0

    composite = (
        political_homophily * 0.25 +
        class_homophily * 0.15 +
        avg_echo * 0.25 +
        clan_insularity * 0.20 +
        district_segregation * 0.15
    )

    return {
        "political_homophily": round(political_homophily, 3),
        "class_homophily": round(class_homophily, 3),
        "clan_insularity": round(clan_insularity, 3),
        "district_segregation": round(district_segregation, 3),
        "topic_echo_chambers": topic_echo,
        "avg_echo_strength": round(avg_echo, 3),
        "composite": round(min(1.0, composite), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 8. POWER LAW EMERGENCE
# ══════════════════════════════════════════════════════════════════════════════

def _power_law_fit(values: list[float]) -> dict:
    sorted_v = sorted([v for v in values if v > 0], reverse=True)
    if len(sorted_v) < 10:
        return {"exponent": 0.0, "r_squared": 0.0, "is_power_law": False}

    log_ranks = [math.log(i + 1) for i in range(len(sorted_v))]
    log_vals = [math.log(v) for v in sorted_v]

    nn = len(log_ranks)
    sum_x = sum(log_ranks)
    sum_y = sum(log_vals)
    sum_xy = sum(log_ranks[i] * log_vals[i] for i in range(nn))
    sum_xx = sum(x * x for x in log_ranks)

    denom = nn * sum_xx - sum_x * sum_x
    if abs(denom) < 1e-10:
        return {"exponent": 0.0, "r_squared": 0.0, "is_power_law": False}

    slope = (nn * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / nn

    mean_y = sum_y / nn
    ss_tot = sum((y - mean_y) ** 2 for y in log_vals)
    ss_res = sum((log_vals[i] - (slope * log_ranks[i] + intercept)) ** 2 for i in range(nn))
    r_squared = 1 - ss_res / max(1e-10, ss_tot)

    return {
        "exponent": round(-slope, 3),
        "r_squared": round(max(0, r_squared), 3),
        "is_power_law": r_squared > 0.85 and slope < -0.3,
    }


def compute_power_law(G: nx.Graph) -> dict:
    agents = _agents(G)
    degrees = [G.degree(nid) for nid in G.nodes]
    economic = [a.capital.economic for a in agents]
    influence = [a.influence for a in agents]

    degree_fit = _power_law_fit([float(d) for d in degrees])
    economic_fit = _power_law_fit(economic)
    influence_fit = _power_law_fit(influence)

    pl_count = sum(1 for f in [degree_fit, economic_fit, influence_fit] if f["is_power_law"])

    sorted_econ = sorted(economic, reverse=True)
    n = len(sorted_econ)
    top5_share = sum(sorted_econ[:max(1, n // 20)]) / max(0.001, sum(sorted_econ))

    sorted_infl = sorted(influence, reverse=True)
    top5_influence = sum(sorted_infl[:max(1, n // 20)]) / max(0.001, sum(sorted_infl))

    composite = (
        (degree_fit["r_squared"] if degree_fit["is_power_law"] else 0) * 0.3 +
        (economic_fit["r_squared"] if economic_fit["is_power_law"] else 0) * 0.3 +
        (influence_fit["r_squared"] if influence_fit["is_power_law"] else 0) * 0.2 +
        top5_share * 0.1 +
        top5_influence * 0.1
    )

    return {
        "degree_distribution": degree_fit,
        "economic_distribution": economic_fit,
        "influence_distribution": influence_fit,
        "power_law_count": pl_count,
        "top5_economic_share": round(top5_share, 3),
        "top5_influence_share": round(top5_influence, 3),
        "composite": round(min(1.0, composite), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 9. INSTITUTIONAL TRUST DYNAMICS
# ══════════════════════════════════════════════════════════════════════════════

def compute_institutional_trust(G: nx.Graph) -> dict:
    agents = _agents(G)
    n = len(agents) or 1

    avg_trust = sum(a.habitus.institutional_trust for a in agents) / n

    trust_values = [a.habitus.institutional_trust for a in agents]
    trust_std = _safe_std(trust_values)

    cross_positive = 0
    total_positive = 0
    for u, v, d in G.edges(data=True):
        w = d.get("weight", 0)
        if w > 0:
            total_positive += 1
            if G.nodes[u]["agent"].clan != G.nodes[v]["agent"].clan:
                cross_positive += 1
    bridging_ratio = cross_positive / max(1, total_positive)

    class_trust = {}
    for a in agents:
        cls = a.habitus.current_class.rank
        class_trust.setdefault(cls, []).append(a.habitus.institutional_trust)
    class_avg_trust = {str(k): round(sum(v) / len(v), 3) for k, v in class_trust.items()}

    if len(class_trust) > 1:
        ranks = [a.habitus.current_class.rank for a in agents]
        trusts = [a.habitus.institutional_trust for a in agents]
        mean_r = sum(ranks) / n
        mean_t = sum(trusts) / n
        cov = sum((ranks[i] - mean_r) * (trusts[i] - mean_t) for i in range(n)) / n
        std_r = _safe_std(ranks)
        std_t = _safe_std(trusts)
        trust_class_corr = cov / max(0.001, std_r * std_t)
    else:
        trust_class_corr = 0.0

    avg_social_capital = sum(a.capital.social for a in agents) / n

    composite = (
        avg_trust * 0.30 +
        (1 - trust_std) * 0.15 +
        bridging_ratio * 0.25 +
        avg_social_capital * 0.15 +
        min(1.0, (1 + trust_class_corr) / 2) * 0.15
    )

    return {
        "avg_institutional_trust": round(avg_trust, 3),
        "trust_dispersion": round(trust_std, 3),
        "bridging_ratio": round(bridging_ratio, 3),
        "trust_class_correlation": round(trust_class_corr, 3),
        "class_trust_means": class_avg_trust,
        "avg_social_capital": round(avg_social_capital, 3),
        "composite": round(min(1.0, composite), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 10. CULTURAL CONVERGENCE / DIVERGENCE
# ══════════════════════════════════════════════════════════════════════════════

def compute_cultural_convergence(G: nx.Graph) -> dict:
    agents = _agents(G)
    n = len(agents) or 1

    clan_tastes = {}
    for a in agents:
        clan_tastes.setdefault(a.clan, []).append(a.habitus.cultural_taste)

    grand_mean = sum(a.habitus.cultural_taste for a in agents) / n

    within_clan_var = 0.0
    between_clan_var = 0.0
    for clan, tastes in clan_tastes.items():
        clan_mean = sum(tastes) / len(tastes)
        within_clan_var += sum((t - clan_mean) ** 2 for t in tastes)
        between_clan_var += len(tastes) * (clan_mean - grand_mean) ** 2

    within_clan_var /= max(1, n)
    between_clan_var /= max(1, n)
    total_var = within_clan_var + between_clan_var
    cultural_clustering = between_clan_var / max(0.001, total_var)

    jaccard_sum = 0.0
    edge_count = 0
    for u, v in G.edges():
        au = G.nodes[u]["agent"]
        av = G.nodes[v]["agent"]
        su = set(au.interests)
        sv = set(av.interests)
        union = su | sv
        if union:
            jaccard_sum += len(su & sv) / len(union)
            edge_count += 1
    interest_convergence = jaccard_sum / max(1, edge_count)

    from capital import habitus_affinity
    affinity_sum = 0.0
    affinity_count = 0
    edges = list(G.edges())
    sample = edges[:min(500, len(edges))]
    for u, v in sample:
        au = G.nodes[u]["agent"]
        av = G.nodes[v]["agent"]
        affinity_sum += habitus_affinity(au.habitus, av.habitus)
        affinity_count += 1
    avg_habitus_affinity = affinity_sum / max(1, affinity_count)

    district_tastes = {}
    for a in agents:
        district_tastes.setdefault(a.district, []).append(a.habitus.cultural_taste)
    district_means = {d: sum(t) / len(t) for d, t in district_tastes.items()}
    district_var = _safe_std(list(district_means.values())) ** 2

    young = [a.habitus.cultural_taste for a in agents if a.age < 35]
    old = [a.habitus.cultural_taste for a in agents if a.age >= 55]
    if young and old:
        generational_gap = abs(sum(young) / len(young) - sum(old) / len(old))
    else:
        generational_gap = 0.0

    composite = (
        cultural_clustering * 0.25 +
        interest_convergence * 0.20 +
        avg_habitus_affinity * 0.20 +
        min(1.0, district_var * 10) * 0.15 +
        min(1.0, generational_gap) * 0.20
    )

    return {
        "cultural_clustering": round(cultural_clustering, 3),
        "interest_convergence": round(interest_convergence, 3),
        "avg_habitus_affinity": round(avg_habitus_affinity, 3),
        "district_cultural_variance": round(district_var, 4),
        "district_taste_means": {d: round(m, 3) for d, m in district_means.items()},
        "generational_gap": round(generational_gap, 3),
        "composite": round(min(1.0, composite), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 11. INFORMATION-THEORETIC MEASURES
#     Mutual information, transfer entropy, synergy (Rosas et al. 2020).
#     Proper non-linear measures of emergent information processing.
# ══════════════════════════════════════════════════════════════════════════════

def compute_information_theoretic(G: nx.Graph) -> dict:
    agents = _agents(G)
    n = len(agents) or 1

    # -- MI(politics, clan): how much clan predicts politics --
    politics_list = [a.politics.value for a in agents]
    clan_list = [a.clan for a in agents]
    mi_pol_clan = _mutual_information(politics_list, clan_list)
    # Normalize by min(H(X), H(Y))
    h_pol = _entropy([c / n for c in Counter(politics_list).values()])
    h_clan = _entropy([c / n for c in Counter(clan_list).values()])
    nmi_pol_clan = mi_pol_clan / max(0.001, min(h_pol, h_clan))

    # -- MI(class, district): spatial class sorting --
    class_list = [a.habitus.current_class.value for a in agents]
    district_list = [a.district for a in agents]
    mi_class_district = _mutual_information(class_list, district_list)
    h_class = _entropy([c / n for c in Counter(class_list).values()])
    h_dist = _entropy([c / n for c in Counter(district_list).values()])
    nmi_class_district = mi_class_district / max(0.001, min(h_class, h_dist))

    # -- Transfer entropy approximation --
    # Use opinion correlation between connected agents as proxy for
    # directional information flow. Higher = more information transfer.
    all_topics = set()
    for a in agents:
        all_topics.update(a.opinion_state.keys())

    opinion_transfer = 0.0
    te_count = 0
    edges_sample = list(G.edges())[:min(800, G.number_of_edges())]
    for u, v in edges_sample:
        au = G.nodes[u]["agent"]
        av = G.nodes[v]["agent"]
        for topic in all_topics:
            ou = au.opinion_state.get(topic, 0)
            ov = av.opinion_state.get(topic, 0)
            if ou != 0 and ov != 0:
                # Directional influence: correlation weighted by edge weight
                w = abs(G.edges[u, v].get("weight", 0.5))
                opinion_transfer += abs(ou * ov) * w
                te_count += 1
    avg_transfer_entropy = opinion_transfer / max(1, te_count)

    # -- Synergy measure (Rosas et al. 2020 PID-inspired) --
    # Synergy: information about system state that requires knowing
    # multiple agents jointly, not available from any single agent.
    # Approximation: compare variance explained by individual attributes
    # vs. pair/group interactions.
    #
    # For each connected pair, compute: does their joint state predict
    # neighbors' opinions better than either alone?
    synergy_scores = []
    nodes_list = list(G.nodes)[:100]  # sample for performance
    for nid in nodes_list:
        agent = G.nodes[nid]["agent"]
        neighbors = list(G.neighbors(nid))
        if len(neighbors) < 2:
            continue
        # Individual prediction: agent's opinion predicts neighbor opinions
        for topic in agent.opinion_state:
            agent_op = agent.opinion_state[topic]
            neighbor_ops = [G.nodes[nb]["agent"].opinion_state.get(topic, 0)
                           for nb in neighbors]
            if not neighbor_ops:
                continue
            avg_nb = sum(neighbor_ops) / len(neighbor_ops)
            individual_error = (agent_op - avg_nb) ** 2
            # Pair prediction: average of agent + best neighbor
            if len(neighbors) >= 2:
                nb_ops = [(nb, G.nodes[nb]["agent"].opinion_state.get(topic, 0))
                          for nb in neighbors]
                nb_ops.sort(key=lambda x: abs(x[1] - avg_nb))
                pair_pred = (agent_op + nb_ops[0][1]) / 2
                pair_error = (pair_pred - avg_nb) ** 2
                if individual_error > 0:
                    synergy = max(0, 1 - pair_error / max(0.001, individual_error))
                    synergy_scores.append(synergy)

    avg_synergy = sum(synergy_scores) / max(1, len(synergy_scores)) if synergy_scores else 0

    # -- Integrated information proxy (Tononi phi) --
    # Simplified: ratio of whole-network clustering to partition clustering
    avg_clustering = nx.average_clustering(G)
    # Bipartition: split by median degree
    degrees = [(nid, G.degree(nid)) for nid in G.nodes]
    median_deg = sorted(d for _, d in degrees)[n // 2]
    partition_a = [nid for nid, d in degrees if d <= median_deg]
    partition_b = [nid for nid, d in degrees if d > median_deg]
    clust_a = nx.average_clustering(G.subgraph(partition_a)) if len(partition_a) > 2 else 0
    clust_b = nx.average_clustering(G.subgraph(partition_b)) if len(partition_b) > 2 else 0
    partition_avg = (clust_a + clust_b) / 2
    phi_proxy = avg_clustering - partition_avg  # positive = integrated
    phi_proxy = max(0, phi_proxy)

    composite = (
        min(1.0, nmi_pol_clan) * 0.15 +
        min(1.0, nmi_class_district) * 0.15 +
        min(1.0, avg_transfer_entropy) * 0.25 +
        avg_synergy * 0.25 +
        min(1.0, phi_proxy * 5) * 0.20
    )

    return {
        "nmi_politics_clan": round(nmi_pol_clan, 4),
        "nmi_class_district": round(nmi_class_district, 4),
        "avg_transfer_entropy": round(avg_transfer_entropy, 4),
        "avg_synergy": round(avg_synergy, 4),
        "phi_proxy": round(phi_proxy, 4),
        "composite": round(min(1.0, composite), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 12. NORM EMERGENCE
#     Axelrod (1986), Bicchieri (2006): norms crystallize from repeated
#     interaction. Agents converge on shared behavioral expectations.
# ══════════════════════════════════════════════════════════════════════════════

def compute_norm_emergence(G: nx.Graph) -> dict:
    agents = _agents(G)
    n = len(agents) or 1

    # -- Norm crystallization: how many agents have crystallized norms --
    agents_with_norms = sum(1 for a in agents if a.norms)
    norm_adoption_rate = agents_with_norms / n

    # -- Norm diversity: how many distinct norms exist --
    all_norm_topics = set()
    for a in agents:
        all_norm_topics.update(a.norms.keys())
    norm_topic_count = len(all_norm_topics)

    # -- Norm strength: average absolute norm value --
    norm_values = []
    for a in agents:
        norm_values.extend(abs(v) for v in a.norms.values())
    avg_norm_strength = sum(norm_values) / max(1, len(norm_values)) if norm_values else 0

    # -- Norm compliance: how well do agents' opinions match local norms --
    compliance_scores = []
    for nid in G.nodes:
        agent = G.nodes[nid]["agent"]
        if not agent.norms:
            continue
        for topic, norm_val in agent.norms.items():
            opinion = agent.opinion_state.get(topic, 0)
            compliance = 1 - min(1.0, abs(opinion - norm_val))
            compliance_scores.append(compliance)
    avg_compliance = sum(compliance_scores) / max(1, len(compliance_scores)) if compliance_scores else 0

    # -- Norm fragmentation: do different communities have conflicting norms? --
    clan_norms = {}
    for a in agents:
        for topic, val in a.norms.items():
            clan_norms.setdefault((a.clan, topic), []).append(val)
    clan_norm_means = {k: sum(v) / len(v) for k, v in clan_norms.items()}
    # Variance of clan norms on same topic
    topic_norm_vars = {}
    for (clan, topic), mean in clan_norm_means.items():
        topic_norm_vars.setdefault(topic, []).append(mean)
    norm_fragmentation = 0.0
    if topic_norm_vars:
        frag_vals = [_safe_std(v) for v in topic_norm_vars.values() if len(v) > 1]
        norm_fragmentation = sum(frag_vals) / max(1, len(frag_vals)) if frag_vals else 0

    composite = (
        norm_adoption_rate * 0.25 +
        avg_norm_strength * 0.20 +
        avg_compliance * 0.25 +
        min(1.0, norm_topic_count / 5) * 0.10 +
        (1 - min(1.0, norm_fragmentation * 2)) * 0.20
    )

    return {
        "norm_adoption_rate": round(norm_adoption_rate, 3),
        "norm_topic_count": norm_topic_count,
        "avg_norm_strength": round(avg_norm_strength, 3),
        "avg_compliance": round(avg_compliance, 3),
        "norm_fragmentation": round(norm_fragmentation, 3),
        "composite": round(min(1.0, composite), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 13. SEGREGATION DYNAMICS
#     Schelling (1971): spatial sorting from mild individual preferences
#     produces macro-level segregation. The canonical emergence example.
# ══════════════════════════════════════════════════════════════════════════════

def compute_segregation(G: nx.Graph) -> dict:
    agents = _agents(G)
    n = len(agents) or 1

    # -- Dissimilarity index (clan x district) --
    district_clan = {}
    clan_totals = Counter()
    district_totals = Counter()
    for a in agents:
        district_clan.setdefault(a.district, Counter())[a.clan] += 1
        clan_totals[a.clan] += 1
        district_totals[a.district] += 1

    # Duncan dissimilarity: compare largest clan vs rest
    if clan_totals:
        largest_clan = clan_totals.most_common(1)[0][0]
        lc_total = clan_totals[largest_clan]
        other_total = n - lc_total
        dissimilarity = 0.0
        for district, clans in district_clan.items():
            lc_in_d = clans.get(largest_clan, 0)
            other_in_d = district_totals[district] - lc_in_d
            dissimilarity += abs(lc_in_d / max(1, lc_total) - other_in_d / max(1, other_total))
        dissimilarity /= 2
    else:
        dissimilarity = 0.0

    # -- Isolation index: probability that a clan member shares district with same clan --
    isolation_sum = 0.0
    isolation_clans = 0
    for clan, total in clan_totals.items():
        if total < 5:
            continue
        prob = 0.0
        for district, clans in district_clan.items():
            clan_in_d = clans.get(clan, 0)
            d_total = district_totals[district]
            prob += (clan_in_d / max(1, total)) * (clan_in_d / max(1, d_total))
        isolation_sum += prob
        isolation_clans += 1
    isolation_index = isolation_sum / max(1, isolation_clans)

    # -- Class segregation: dissimilarity by class across districts --
    district_class = {}
    class_totals = Counter()
    for a in agents:
        district_class.setdefault(a.district, Counter())[a.habitus.current_class.value] += 1
        class_totals[a.habitus.current_class.value] += 1

    if class_totals:
        upper_classes = {"upper", "upper_middle"}
        upper_total = sum(class_totals[c] for c in upper_classes if c in class_totals)
        lower_total = n - upper_total
        class_dissimilarity = 0.0
        for district, classes in district_class.items():
            upper_in_d = sum(classes.get(c, 0) for c in upper_classes)
            lower_in_d = district_totals[district] - upper_in_d
            class_dissimilarity += abs(
                upper_in_d / max(1, upper_total) - lower_in_d / max(1, lower_total))
        class_dissimilarity /= 2
    else:
        class_dissimilarity = 0.0

    # -- Average Schelling satisfaction --
    avg_satisfaction = sum(a.satisfaction for a in agents) / n

    # -- Satisfaction disparity: std of satisfaction --
    sat_std = _safe_std([a.satisfaction for a in agents])

    composite = (
        dissimilarity * 0.25 +
        isolation_index * 0.20 +
        class_dissimilarity * 0.20 +
        (1 - avg_satisfaction) * 0.20 +
        sat_std * 0.15
    )

    return {
        "dissimilarity_index": round(dissimilarity, 3),
        "isolation_index": round(isolation_index, 3),
        "class_dissimilarity": round(class_dissimilarity, 3),
        "avg_satisfaction": round(avg_satisfaction, 3),
        "satisfaction_disparity": round(sat_std, 3),
        "composite": round(min(1.0, composite), 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# INTER-DIMENSION COUPLING MATRIX
# Reinforcing and dampening feedback loops between emergent dimensions.
# ══════════════════════════════════════════════════════════════════════════════

COUPLING_MATRIX = {
    "polarization":             {"echo_chambers": 0.15, "institutional_trust": -0.10,
                                 "contagion_susceptibility": 0.08, "segregation": 0.06},
    "inequality":               {"phase_transitions": 0.12, "polarization": 0.08,
                                 "institutional_trust": -0.08, "segregation": 0.10},
    "collective_intelligence":  {"network_resilience": 0.08, "institutional_trust": 0.06,
                                 "norm_emergence": 0.05},
    "contagion_susceptibility": {"phase_transitions": 0.10, "echo_chambers": 0.05,
                                 "norm_emergence": 0.08},
    "network_resilience":       {"collective_intelligence": 0.05, "contagion_susceptibility": -0.05},
    "phase_transitions":        {"polarization": 0.08, "institutional_trust": -0.06},
    "echo_chambers":            {"polarization": 0.12, "collective_intelligence": -0.10,
                                 "cultural_convergence": 0.06, "segregation": 0.08},
    "power_law":                {"inequality": 0.08, "network_resilience": -0.05},
    "institutional_trust":      {"network_resilience": 0.10, "contagion_susceptibility": -0.08,
                                 "collective_intelligence": 0.06, "norm_emergence": 0.10},
    "cultural_convergence":     {"echo_chambers": 0.06, "collective_intelligence": -0.04,
                                 "norm_emergence": 0.08},
    "information_theoretic":    {"collective_intelligence": 0.06, "echo_chambers": 0.04},
    "norm_emergence":           {"institutional_trust": 0.08, "echo_chambers": 0.05,
                                 "cultural_convergence": 0.06},
    "segregation":              {"echo_chambers": 0.10, "polarization": 0.06,
                                 "inequality": 0.05, "institutional_trust": -0.06},
}


def apply_coupling(raw_composites: dict[str, float]) -> dict[str, float]:
    """Apply inter-dimension coupling to raw composites."""
    adjusted = dict(raw_composites)
    for source, targets in COUPLING_MATRIX.items():
        source_val = raw_composites.get(source, 0)
        for target, strength in targets.items():
            if target in adjusted:
                adjusted[target] += source_val * strength
    # Clamp to [0, 1]
    return {k: round(max(0.0, min(1.0, v)), 3) for k, v in adjusted.items()}


# ══════════════════════════════════════════════════════════════════════════════
# DOWNWARD CAUSATION
# Macro-level emergence feeds back into micro-level agent behavior.
# ══════════════════════════════════════════════════════════════════════════════

def emergence_affect_agents(G: nx.Graph, composites: dict[str, float]):
    """Apply downward causation: emergent properties constrain/enable agents."""
    agents = _agents(G)

    polarization = composites.get("polarization", 0)
    inequality = composites.get("inequality", 0)
    echo_chambers = composites.get("echo_chambers", 0)
    trust = composites.get("institutional_trust", 0)
    contagion = composites.get("contagion_susceptibility", 0)
    segregation = composites.get("segregation", 0)

    for agent in agents:
        # -- Polarization reduces cross-group openness --
        if polarization > 0.3:
            openness_penalty = (polarization - 0.3) * 0.05
            agent.openness = max(0.05, agent.openness - openness_penalty)
            # Increases assertiveness (entrenched positions)
            agent.assertiveness = min(0.95, agent.assertiveness + openness_penalty * 0.5)

        # -- Inequality shifts class awareness and aspiration --
        if inequality > 0.4:
            ineq_effect = (inequality - 0.4) * 0.03
            agent.habitus.class_awareness = min(1.0, agent.habitus.class_awareness + ineq_effect)
            # Lower classes become more risk-averse under inequality
            if agent.habitus.current_class.rank <= 1:
                agent.habitus.risk_tolerance = max(0, agent.habitus.risk_tolerance - ineq_effect * 0.5)

        # -- Echo chambers reduce openness for agents in dense same-opinion clusters --
        if echo_chambers > 0.3:
            echo_penalty = (echo_chambers - 0.3) * 0.03
            agent.openness = max(0.05, agent.openness - echo_penalty)

        # -- Low institutional trust erodes individual trust --
        if trust < 0.4:
            trust_erosion = (0.4 - trust) * 0.02
            agent.habitus.institutional_trust = max(0, agent.habitus.institutional_trust - trust_erosion)
        elif trust > 0.6:
            # High system trust lifts individual trust
            trust_boost = (trust - 0.6) * 0.01
            agent.habitus.institutional_trust = min(1, agent.habitus.institutional_trust + trust_boost)

        # -- High contagion susceptibility lowers activation thresholds (implicit via openness) --
        if contagion > 0.5:
            contagion_effect = (contagion - 0.5) * 0.02
            agent.openness = min(0.95, agent.openness + contagion_effect)

        # -- Segregation reduces satisfaction for minority agents in districts --
        if segregation > 0.3:
            seg_effect = (segregation - 0.3) * 0.05
            agent.satisfaction = max(0, agent.satisfaction - seg_effect * 0.3)


# ══════════════════════════════════════════════════════════════════════════════
# ADAPTIVE NETWORK REWIRING
# Gross & Blasius (2008): co-evolutionary network dynamics.
# Agents drop/form ties based on opinions, homophily, triadic closure.
# ══════════════════════════════════════════════════════════════════════════════

def adaptive_rewire(G: nx.Graph, rng: random.Random, rate: float = 0.05):
    """
    Per-tick network rewiring. Rate controls fraction of agents who consider
    rewiring each tick. Mechanisms:
    1. Opinion-driven dissolution: drop ties to strong disagreers
    2. Homophily-driven formation: form ties to similar unconnected agents
    3. Triadic closure: friends of friends
    4. Weak tie decay: very low-weight edges dissolve
    """
    nodes = list(G.nodes)
    n = len(nodes)
    rewire_count = max(1, int(n * rate))
    candidates = rng.sample(nodes, min(rewire_count, n))

    edges_added = 0
    edges_removed = 0

    for nid in candidates:
        agent = G.nodes[nid]["agent"]
        neighbors = list(G.neighbors(nid))
        if not neighbors:
            continue

        # ── 1. Opinion-driven dissolution ──────────────────────────────
        # Drop a tie to someone with strongly opposing opinions
        if rng.random() < 0.3 and len(neighbors) > 3:
            worst_nb = None
            worst_score = 0
            for nb in neighbors:
                nb_agent = G.nodes[nb]["agent"]
                # Political distance
                pol_dist = abs(agent.politics.numeric - nb_agent.politics.numeric)
                # Opinion disagreement
                disagree = 0
                shared_topics = set(agent.opinion_state.keys()) & set(nb_agent.opinion_state.keys())
                for topic in shared_topics:
                    if agent.opinion_state[topic] * nb_agent.opinion_state[topic] < 0:
                        disagree += abs(agent.opinion_state[topic] - nb_agent.opinion_state[topic])
                score = pol_dist * 0.3 + disagree * 0.7
                edge_w = G.edges[nid, nb].get("weight", 0.5)
                # Only consider dissolving weak ties with high disagreement
                if score > worst_score and edge_w < 0.5:
                    worst_score = score
                    worst_nb = nb
            if worst_nb and worst_score > 1.5:
                G.remove_edge(nid, worst_nb)
                edges_removed += 1

        # ── 2. Homophily-driven formation ──────────────────────────────
        if rng.random() < 0.2:
            # Sample candidates (not already connected)
            neighbor_set = set(neighbors)
            sample_pool = rng.sample(nodes, min(15, n))
            best_match = None
            best_affinity = 0
            for cand in sample_pool:
                if cand == nid or cand in neighbor_set:
                    continue
                cand_agent = G.nodes[cand]["agent"]
                # Political similarity + interest overlap + class proximity
                pol_sim = 1 - abs(agent.politics.numeric - cand_agent.politics.numeric) / 6
                interests_shared = len(set(agent.interests) & set(cand_agent.interests))
                class_sim = 1 - abs(agent.habitus.current_class.rank -
                                    cand_agent.habitus.current_class.rank) / 4
                affinity = pol_sim * 0.4 + (interests_shared / 4) * 0.3 + class_sim * 0.3
                if affinity > best_affinity and affinity > 0.6:
                    best_affinity = affinity
                    best_match = cand
            if best_match:
                w = 0.2 + best_affinity * 0.3
                G.add_edge(nid, best_match, weight=round(w, 3), rel="friendship")
                edges_added += 1

        # ── 3. Triadic closure ─────────────────────────────────────────
        if rng.random() < 0.15 and neighbors:
            friend = rng.choice(neighbors)
            fof_list = [f for f in G.neighbors(friend)
                        if f != nid and not G.has_edge(nid, f)]
            if fof_list:
                fof = rng.choice(fof_list)
                w1 = G.edges[nid, friend].get("weight", 0.3)
                w2 = G.edges[friend, fof].get("weight", 0.3)
                if w1 > 0 and w2 > 0:
                    new_w = min(w1, w2) * 0.6
                    G.add_edge(nid, fof, weight=round(new_w, 3), rel="friendship")
                    edges_added += 1

        # ── 4. Weak tie decay ──────────────────────────────────────────
        if rng.random() < 0.1:
            for nb in neighbors:
                edge_w = G.edges[nid, nb].get("weight", 0.5)
                if 0 < edge_w < 0.1 and rng.random() < 0.3:
                    G.remove_edge(nid, nb)
                    edges_removed += 1
                    break  # max one decay per agent per tick

    # Recompute social capital for affected nodes
    for nid in G.nodes:
        agent = G.nodes[nid]["agent"]
        degree = G.degree(nid)
        agent.capital.social = min(1.0, 0.1 + math.sqrt(degree) / 8)
        agent.capital.clamp()

    return {"edges_added": edges_added, "edges_removed": edges_removed}


# ══════════════════════════════════════════════════════════════════════════════
# NORM EMERGENCE DYNAMICS
# Per-tick norm formation, crystallization, compliance, and sanctions.
# ══════════════════════════════════════════════════════════════════════════════

def evolve_norms(G: nx.Graph, rng: random.Random):
    """
    Norms form through:
    1. Local averaging: agents adopt the weighted average opinion of neighbors
       as a local norm on active topics
    2. Crystallization: when variance within a community drops below threshold,
       the norm solidifies (stronger compliance pressure)
    3. Sanctions: agents deviating from crystallized norms lose social capital
    """
    CRYSTALLIZATION_THRESHOLD = 0.25  # std below which a norm crystallizes
    COMPLIANCE_RATE = 0.05  # how fast agents drift toward norms
    SANCTION_RATE = 0.01  # social capital loss for deviance

    for nid in G.nodes:
        agent = G.nodes[nid]["agent"]
        neighbors = list(G.neighbors(nid))
        if not neighbors:
            continue

        # Seed implicit norms from agent interests (baseline behavioral norms)
        # Agents develop norms around topics they care about, even without events
        if not agent.norms and rng.random() < 0.1:
            for interest in agent.interests[:2]:
                # Political leaning seeds the norm direction
                agent.norms[interest] = agent.politics.numeric / 6  # normalize to ~[-0.5, 0.5]

        # Gather all active topics (own opinions + neighbor opinions + interests)
        active_topics = set(agent.opinion_state.keys())
        for nb in neighbors[:10]:
            active_topics.update(G.nodes[nb]["agent"].opinion_state.keys())
            active_topics.update(G.nodes[nb]["agent"].norms.keys())

        # Gather neighbor opinions/norms weighted by edge weight
        for topic in active_topics:
            weighted_sum = 0.0
            weight_total = 0.0
            for nb in neighbors:
                nb_agent = G.nodes[nb]["agent"]
                # Use opinion if available, fall back to norm, then 0
                nb_op = nb_agent.opinion_state.get(topic,
                        nb_agent.norms.get(topic, 0))
                edge_w = max(0, G.edges[nid, nb].get("weight", 0.5))
                weighted_sum += nb_op * edge_w
                weight_total += edge_w

            if weight_total > 0:
                local_norm = weighted_sum / weight_total
                # Blend toward local norm
                current_norm = agent.norms.get(topic, agent.opinion_state.get(topic, 0))
                agent.norms[topic] = current_norm * 0.7 + local_norm * 0.3

        # ── Compliance pressure: drift opinions toward norms ──────────
        for topic, norm_val in agent.norms.items():
            if topic in agent.opinion_state:
                op = agent.opinion_state[topic]
                deviance = norm_val - op
                agent.opinion_state[topic] += deviance * COMPLIANCE_RATE * agent.loyalty

        # ── Sanctions: deviance from strong norms costs social capital ─
        for topic, norm_val in agent.norms.items():
            op = agent.opinion_state.get(topic, 0)
            deviance = abs(op - norm_val)
            if deviance > 0.5:
                agent.capital.social = max(0, agent.capital.social - SANCTION_RATE * deviance)
                agent.capital.clamp()


# ══════════════════════════════════════════════════════════════════════════════
# SCHELLING SEGREGATION DYNAMICS
# Per-tick residential sorting based on neighborhood composition.
# ══════════════════════════════════════════════════════════════════════════════

def schelling_step(G: nx.Graph, rng: random.Random, move_rate: float = 0.03):
    """
    Schelling segregation step:
    1. Compute satisfaction for each agent (fraction of district-neighbors
       who share their clan or class)
    2. Dissatisfied agents (below threshold) attempt to move to a more
       satisfactory district
    """
    from model import DISTRICTS

    SATISFACTION_THRESHOLD = 0.35  # below this, agent wants to move

    # Build district membership
    district_agents: dict[str, list] = {}
    for nid in G.nodes:
        agent = G.nodes[nid]["agent"]
        district_agents.setdefault(agent.district, []).append(nid)

    # Compute satisfaction
    for nid in G.nodes:
        agent = G.nodes[nid]["agent"]
        same_group = 0
        total_neighbors = 0
        # Count district neighbors (graph neighbors in same district)
        for nb in G.neighbors(nid):
            nb_agent = G.nodes[nb]["agent"]
            if nb_agent.district == agent.district:
                total_neighbors += 1
                if nb_agent.clan == agent.clan or nb_agent.habitus.current_class == agent.habitus.current_class:
                    same_group += 1
        if total_neighbors > 0:
            agent.satisfaction = same_group / total_neighbors
        else:
            # Also count non-graph district co-residents
            d_members = district_agents.get(agent.district, [])
            for other_nid in d_members[:20]:  # sample
                if other_nid == nid:
                    continue
                other = G.nodes[other_nid]["agent"]
                total_neighbors += 1
                if other.clan == agent.clan or other.habitus.current_class == agent.habitus.current_class:
                    same_group += 1
            agent.satisfaction = same_group / max(1, total_neighbors)

    # Move dissatisfied agents
    movers = [nid for nid in G.nodes
              if G.nodes[nid]["agent"].satisfaction < SATISFACTION_THRESHOLD]
    n_movers = min(int(len(movers) * move_rate / max(0.01, 1 - SATISFACTION_THRESHOLD)), len(movers))
    if n_movers > 0:
        actual_movers = rng.sample(movers, min(n_movers, len(movers)))
    else:
        actual_movers = []

    moves = 0
    for nid in actual_movers:
        agent = G.nodes[nid]["agent"]
        # Find best district
        best_district = agent.district
        best_satisfaction = agent.satisfaction
        for district in DISTRICTS:
            if district == agent.district:
                continue
            d_members = district_agents.get(district, [])
            if not d_members:
                continue
            same = sum(1 for m in d_members[:30]
                       if (G.nodes[m]["agent"].clan == agent.clan or
                           G.nodes[m]["agent"].habitus.current_class == agent.habitus.current_class))
            sat = same / min(30, len(d_members))
            if sat > best_satisfaction:
                best_satisfaction = sat
                best_district = district

        if best_district != agent.district:
            old_district = agent.district
            agent.district = best_district
            # Update district_agents
            if nid in district_agents.get(old_district, []):
                district_agents[old_district].remove(nid)
            district_agents.setdefault(best_district, []).append(nid)
            moves += 1

    return {"moves": moves, "dissatisfied": len(movers)}


# ══════════════════════════════════════════════════════════════════════════════
# PER-AGENT EMERGENCE ATTRIBUTION
# Who catalyzes emergence? Who is constrained by it?
# ══════════════════════════════════════════════════════════════════════════════

def compute_agent_emergence_scores(G: nx.Graph) -> dict:
    """
    Compute per-agent scores:
    - catalyst: how much this agent contributes to emergent properties
    - constrained: how much macro patterns shape this agent
    """
    agents_list = list(G.nodes)
    n = len(agents_list) or 1

    scores = {}
    for nid in agents_list:
        agent = G.nodes[nid]["agent"]
        degree = G.degree(nid)

        # ── Catalyst score ─────────────────────────────────────────────
        # Betweenness-like: bridges between communities catalyze emergence
        # (approximate with degree * cross-group connections)
        cross_group = sum(1 for nb in G.neighbors(nid)
                          if G.nodes[nb]["agent"].clan != agent.clan)
        bridging = cross_group / max(1, degree)

        # Opinion extremity: extreme opinions drive polarization
        opinion_extremity = 0.0
        if agent.opinion_state:
            opinion_extremity = sum(abs(v) for v in agent.opinion_state.values()) / len(agent.opinion_state)

        # Norm influence: agents with many norms shape collective behavior
        norm_influence = len(agent.norms) / 10  # normalize

        # Influence * connectivity
        influence_connectivity = agent.influence * math.sqrt(degree) / 10

        catalyst = (
            bridging * 0.30 +
            opinion_extremity * 0.20 +
            min(1.0, norm_influence) * 0.20 +
            min(1.0, influence_connectivity) * 0.30
        )

        # ── Constrained score ──────────────────────────────────────────
        # How much is this agent shaped by macro patterns?
        norm_compliance = 0.0
        if agent.norms:
            deviances = []
            for topic, norm_val in agent.norms.items():
                op = agent.opinion_state.get(topic, 0)
                deviances.append(abs(op - norm_val))
            norm_compliance = 1 - (sum(deviances) / max(1, len(deviances)))

        # Satisfaction (Schelling constraint)
        satisfaction_constraint = 1 - agent.satisfaction

        # How similar is agent to neighbors (homophily pressure)
        neighbor_similarity = 0.0
        if degree > 0:
            same_pol = sum(1 for nb in G.neighbors(nid)
                          if G.nodes[nb]["agent"].politics == agent.politics)
            neighbor_similarity = same_pol / degree

        constrained = (
            max(0, norm_compliance) * 0.35 +
            max(0, satisfaction_constraint) * 0.25 +
            neighbor_similarity * 0.20 +
            (1 - agent.openness) * 0.20  # low openness = more constrained
        )

        agent.emergence_score = round(min(1.0, catalyst), 3)

        scores[nid] = {
            "catalyst": round(min(1.0, catalyst), 3),
            "constrained": round(min(1.0, constrained), 3),
            "bridging": round(bridging, 3),
            "opinion_extremity": round(opinion_extremity, 3),
        }

    return scores


# ══════════════════════════════════════════════════════════════════════════════
# CRITICAL SLOWING DOWN DETECTION
# Scheffer et al. (2009, 2012): early warning signals before regime shifts.
# ══════════════════════════════════════════════════════════════════════════════

def detect_critical_slowing_down(history: list[dict], window: int = 5) -> dict:
    """
    Detect early warning signals in emergence history.
    Returns per-dimension indicators:
    - autocorrelation_trend: rising lag-1 AC suggests approaching tipping point
    - variance_trend: rising variance suggests destabilization
    - flickering: rapid oscillations indicate bistability
    - warning_level: 0 (safe), 1 (watch), 2 (warning), 3 (critical)
    """
    if len(history) < window + 2:
        return {}

    warnings = {}
    recent = history[-min(len(history), window * 2):]

    for dim in (recent[0].get("composites", {}) or {}).keys():
        series = [h.get("composites", {}).get(dim, 0) for h in recent]
        if len(series) < window + 2:
            continue

        # Split into early and late windows
        mid = len(series) // 2
        early = series[:mid]
        late = series[mid:]

        # Lag-1 autocorrelation in each window
        ac_early = _lag1_autocorrelation(early)
        ac_late = _lag1_autocorrelation(late)
        ac_trend = ac_late - ac_early

        # Variance in each window
        var_early = _safe_std(early) ** 2
        var_late = _safe_std(late) ** 2
        var_trend = var_late - var_early

        # Flickering: count sign changes in difference series
        diffs = [series[i + 1] - series[i] for i in range(len(series) - 1)]
        sign_changes = sum(1 for i in range(len(diffs) - 1)
                          if diffs[i] * diffs[i + 1] < 0)
        flickering = sign_changes / max(1, len(diffs) - 1)

        # Warning level
        level = 0
        if ac_trend > 0.1:
            level += 1
        if var_trend > 0.005:
            level += 1
        if flickering > 0.5:
            level += 1

        warnings[dim] = {
            "autocorrelation_trend": round(ac_trend, 4),
            "variance_trend": round(var_trend, 4),
            "flickering": round(flickering, 3),
            "warning_level": min(3, level),
        }

    return warnings


# ══════════════════════════════════════════════════════════════════════════════
# DIMENSION REGISTRY AND METADATA
# ══════════════════════════════════════════════════════════════════════════════

EMERGENCE_DIMENSIONS = [
    ("polarization", compute_polarization),
    ("inequality", compute_inequality),
    ("collective_intelligence", compute_collective_intelligence),
    ("contagion_susceptibility", compute_contagion_susceptibility),
    ("network_resilience", compute_network_resilience),
    ("phase_transitions", compute_phase_transitions),
    ("echo_chambers", compute_echo_chambers),
    ("power_law", compute_power_law),
    ("institutional_trust", compute_institutional_trust),
    ("cultural_convergence", compute_cultural_convergence),
    ("information_theoretic", compute_information_theoretic),
    ("norm_emergence", compute_norm_emergence),
    ("segregation", compute_segregation),
]

DIMENSION_META = {
    "polarization": {
        "label": "Polarization",
        "description": "Esteban-Ray index of political/opinion clustering into distant factions",
        "higher_is": "more polarized",
        "research": "Esteban & Ray 1994, Axelrod 1997",
    },
    "inequality": {
        "label": "Inequality",
        "description": "Gini, Palma ratio, and Matthew effect across capital dimensions",
        "higher_is": "more unequal",
        "research": "Piketty 2014, Merton 1968 (Matthew effect)",
    },
    "collective_intelligence": {
        "label": "Collective Intelligence",
        "description": "Group problem-solving capacity from diversity, connectivity, and sensitivity",
        "higher_is": "smarter collective",
        "research": "Woolley et al. 2010 (MIT), Page 2007",
    },
    "contagion_susceptibility": {
        "label": "Contagion Risk",
        "description": "Vulnerability to information cascades and behavioral contagion",
        "higher_is": "more susceptible",
        "research": "Watts 2002, Christakis & Fowler 2009",
    },
    "network_resilience": {
        "label": "Network Resilience",
        "description": "Robustness to random failure vs. fragility to targeted hub removal",
        "higher_is": "more resilient",
        "research": "Barabasi 2002, Albert et al. 2000",
    },
    "phase_transitions": {
        "label": "Phase Transitions",
        "description": "Proximity to critical tipping points in opinion, politics, and mobility",
        "higher_is": "closer to tipping",
        "research": "Granovetter 1978, Centola 2018",
    },
    "echo_chambers": {
        "label": "Echo Chambers",
        "description": "Homophily-driven information silos in politics, class, and clan",
        "higher_is": "more siloed",
        "research": "Sunstein 2001, Pariser 2011",
    },
    "power_law": {
        "label": "Power Law Emergence",
        "description": "Whether influence/wealth/degree follow scale-free distributions",
        "higher_is": "stronger power law",
        "research": "Barabasi & Albert 1999, Clauset et al. 2009",
    },
    "institutional_trust": {
        "label": "Institutional Trust",
        "description": "Generalized trust from bridging capital, civic engagement, and repeated interaction",
        "higher_is": "higher trust",
        "research": "Putnam 2000, Fukuyama 1995",
    },
    "cultural_convergence": {
        "label": "Cultural Convergence",
        "description": "Within-group cultural homogenization and between-group divergence",
        "higher_is": "more convergent",
        "research": "Henrich 2015, Boyd & Richerson 1985",
    },
    "information_theoretic": {
        "label": "Information Integration",
        "description": "Mutual information, transfer entropy, and synergy across the network",
        "higher_is": "more integrated",
        "research": "Rosas et al. 2020 (PID), Tononi 2004 (phi)",
    },
    "norm_emergence": {
        "label": "Norm Emergence",
        "description": "Crystallization of shared behavioral expectations from repeated interaction",
        "higher_is": "stronger norms",
        "research": "Axelrod 1986, Bicchieri 2006",
    },
    "segregation": {
        "label": "Segregation",
        "description": "Spatial sorting from mild preferences producing macro-level separation",
        "higher_is": "more segregated",
        "research": "Schelling 1971, Fossett 2006",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# EMERGENCE TRACKER (COMPOSITE SNAPSHOT + HISTORY)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class EmergenceSnapshot:
    """Complete emergent properties measurement at a point in time."""
    year: int
    dimensions: dict[str, dict]
    composites: dict[str, float]
    coupled_composites: dict[str, float]
    early_warnings: dict[str, dict]
    agent_scores: dict  # per-agent emergence attribution

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "dimensions": self.dimensions,
            "composites": self.composites,
            "coupled_composites": self.coupled_composites,
            "early_warnings": self.early_warnings,
            "meta": DIMENSION_META,
            "coupling_matrix": COUPLING_MATRIX,
        }


@dataclass
class EmergenceTracker:
    """Tracks emergence metrics over time."""
    history: list[EmergenceSnapshot] = field(default_factory=list)

    def snapshot(self, G: nx.Graph, year: int = 0) -> EmergenceSnapshot:
        dimensions = {}
        composites = {}
        for name, func in EMERGENCE_DIMENSIONS:
            result = func(G)
            dimensions[name] = result
            composites[name] = result.get("composite", 0.0)

        # Apply inter-dimension coupling
        coupled = apply_coupling(composites)

        # Detect critical slowing down from history
        history_dicts = self.get_history()
        early_warnings = detect_critical_slowing_down(history_dicts)

        # Per-agent emergence attribution
        agent_scores = compute_agent_emergence_scores(G)

        snap = EmergenceSnapshot(
            year=year,
            dimensions=dimensions,
            composites=composites,
            coupled_composites=coupled,
            early_warnings=early_warnings,
            agent_scores=agent_scores,
        )
        self.history.append(snap)
        return snap

    def get_history(self) -> list[dict]:
        return [
            {"year": s.year, "composites": s.coupled_composites}
            for s in self.history
        ]

    def get_trends(self) -> dict:
        if len(self.history) < 2:
            return {name: 0.0 for name, _ in EMERGENCE_DIMENSIONS}
        recent = self.history[-min(5, len(self.history)):]
        trends = {}
        for name, _ in EMERGENCE_DIMENSIONS:
            values = [s.coupled_composites.get(name, 0) for s in recent]
            if len(values) >= 2:
                trends[name] = round((values[-1] - values[0]) / len(values), 4)
            else:
                trends[name] = 0.0
        return trends

    def to_dict(self) -> dict:
        if not self.history:
            return {"current": None, "history": [], "trends": {}, "meta": DIMENSION_META}
        current = self.history[-1]
        return {
            "current": current.to_dict(),
            "history": self.get_history(),
            "trends": self.get_trends(),
            "meta": DIMENSION_META,
        }


# ══════════════════════════════════════════════════════════════════════════════
# FULL PER-TICK EMERGENCE DYNAMICS
# Called once per simulation tick to drive all emergence feedback mechanisms.
# ══════════════════════════════════════════════════════════════════════════════

def advance_emergence_dynamics(G: nx.Graph, tracker: EmergenceTracker,
                                rng: random.Random) -> dict:
    """
    Run all per-tick emergence dynamics:
    1. Downward causation (emergence → agents)
    2. Adaptive network rewiring (co-evolution)
    3. Norm emergence (crystallization + compliance)
    4. Schelling segregation step
    Returns summary of changes.
    """
    # Use last snapshot composites for downward causation
    if tracker.history:
        composites = tracker.history[-1].coupled_composites
    else:
        composites = {}

    # 1. Downward causation
    emergence_affect_agents(G, composites)

    # 2. Adaptive rewiring
    rewire_result = adaptive_rewire(G, rng)

    # 3. Norm emergence
    evolve_norms(G, rng)

    # 4. Schelling step
    schelling_result = schelling_step(G, rng)

    return {
        "downward_causation": True,
        "rewiring": rewire_result,
        "norms_evolved": True,
        "schelling": schelling_result,
    }
