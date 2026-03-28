"""
CivGraph — Event system and influence propagation engine.

Events ripple through the social graph. Each agent reacts based on their
own traits, relationships, and position. Influence propagates via weighted
edges with decay.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx

from model import Agent, PoliticalLeaning, RelType, get_agent
from capital import capital_field_relevance, habitus_reaction_modifier, habitus_affinity
from media import media_event_amplifier


# ── Event types ──────────────────────────────────────────────────────────────

EVENT_TEMPLATES = {
    "election": {
        "desc": "A city-wide election is called",
        "topics": ["governance", "power"],
        "political_weight": 1.0,
        "clan_weight": 0.5,
    },
    "scandal": {
        "desc": "A corruption scandal breaks",
        "topics": ["trust", "governance"],
        "political_weight": 0.7,
        "clan_weight": 0.8,
    },
    "development": {
        "desc": "A major real estate development is proposed",
        "topics": ["real_estate", "environment", "finance"],
        "political_weight": 0.4,
        "clan_weight": 0.3,
    },
    "crisis": {
        "desc": "An economic crisis hits the city",
        "topics": ["finance", "unions", "manufacturing"],
        "political_weight": 0.6,
        "clan_weight": 0.4,
    },
    "protest": {
        "desc": "A mass protest erupts",
        "topics": ["governance", "unions", "security"],
        "political_weight": 0.9,
        "clan_weight": 0.6,
    },
    "festival": {
        "desc": "A cultural festival brings people together",
        "topics": ["arts", "hospitality", "religion"],
        "political_weight": 0.1,
        "clan_weight": 0.2,
    },
    "tech_boom": {
        "desc": "A tech company announces a major expansion",
        "topics": ["tech", "real_estate", "education"],
        "political_weight": 0.3,
        "clan_weight": 0.2,
    },
    "policy_change": {
        "desc": "The council passes a controversial policy",
        "topics": ["governance", "law"],
        "political_weight": 0.8,
        "clan_weight": 0.5,
    },
    "education_reform": {
        "desc": "A major education reform is proposed",
        "topics": ["education", "governance"],
        "political_weight": 0.7,
        "clan_weight": 0.3,
    },
    "housing_crisis": {
        "desc": "Housing prices surge, displacing lower-income residents",
        "topics": ["real_estate", "finance"],
        "political_weight": 0.6,
        "clan_weight": 0.4,
    },
    "cultural_event": {
        "desc": "A prestigious cultural institution opens",
        "topics": ["arts", "education"],
        "political_weight": 0.2,
        "clan_weight": 0.2,
    },
    "welfare_reform": {
        "desc": "Changes to the social safety net are debated",
        "topics": ["governance", "finance"],
        "political_weight": 0.9,
        "clan_weight": 0.3,
    },
    "custom": {
        "desc": "A custom event",
        "topics": [],
        "political_weight": 0.5,
        "clan_weight": 0.5,
    },
}


@dataclass
class EventResult:
    agent_id: str
    agent_name: str
    old_opinion: float
    new_opinion: float
    delta: float
    stance: str  # "support", "oppose", "neutral"
    activated: bool  # did they spread it further


@dataclass
class PropagationStep:
    step: int
    results: list[EventResult]
    frontier_size: int


@dataclass
class Event:
    id: str
    event_type: str
    title: str
    description: str
    origin_agent: str  # who triggers / is at center
    topic: str
    sentiment: float   # -1 (negative) to 1 (positive)
    intensity: float   # 0-1
    political_bias: float  # -3 to 3, which political side benefits
    target_district: str | None = None
    target_clan: str | None = None
    propagation_log: list[PropagationStep] = field(default_factory=list)
    affected_agents: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "origin_agent": self.origin_agent,
            "topic": self.topic,
            "sentiment": self.sentiment,
            "intensity": self.intensity,
            "political_bias": self.political_bias,
            "target_district": self.target_district,
            "target_clan": self.target_clan,
            "steps": len(self.propagation_log),
            "total_affected": len(self.affected_agents),
            "propagation": [
                {
                    "step": s.step,
                    "frontier_size": s.frontier_size,
                    "results": [
                        {
                            "agent_id": r.agent_id,
                            "agent_name": r.agent_name,
                            "old_opinion": round(r.old_opinion, 3),
                            "new_opinion": round(r.new_opinion, 3),
                            "delta": round(r.delta, 3),
                            "stance": r.stance,
                            "activated": r.activated,
                        }
                        for r in s.results
                    ],
                }
                for s in self.propagation_log
            ],
        }


# ── Influence engine ─────────────────────────────────────────────────────────

def _reaction_strength(agent: Agent, event: Event, edge_data: dict | None,
                       source_agent: Agent | None = None) -> float:
    """How strongly an agent reacts to an event. Can be negative (oppose)."""
    score = 0.0

    # 1) Base reaction — everyone reacts at least a little
    score += 0.25

    # 2) Topic relevance
    if event.topic in agent.interests:
        score += 0.4

    # 3) Political alignment with event bias
    pol_dist = agent.politics.numeric - event.political_bias
    pol_factor = math.exp(-0.2 * pol_dist * pol_dist)  # gaussian
    alignment = 1 if pol_dist * event.sentiment >= 0 else -1
    score += 0.35 * pol_factor * alignment

    # 4) Clan affinity
    if event.target_clan and agent.clan == event.target_clan:
        score += 0.3 * event.sentiment

    # 5) District proximity
    if event.target_district and agent.district == event.target_district:
        score += 0.2

    # 6) Capital field relevance — agents with relevant capital react stronger
    field_rel = capital_field_relevance(agent.capital, event.topic)
    score += 0.2 * field_rel

    # 7) Personality: assertive people react more
    score *= (0.6 + 0.4 * agent.assertiveness)

    # 8) Habitus disposition filter
    hab_mod = habitus_reaction_modifier(agent.habitus, event.topic, event.sentiment)
    score *= (0.7 + 0.3 * (hab_mod - 1.0) + 0.3)

    # 9) Edge weight from whoever told them (trust channel)
    if edge_data:
        weight = edge_data.get("weight", 0.5)
        if weight < 0:  # rivalry — flip sentiment
            score *= -0.6
        else:
            score *= (0.6 + 0.4 * weight)
        # Habitus affinity boost: similar dispositions amplify trust
        if source_agent:
            hab_aff = habitus_affinity(source_agent.habitus, agent.habitus)
            score *= (1.0 + hab_aff * 0.2)

    return max(-1.0, min(1.0, score))


def propagate_event(G: nx.Graph, event: Event, max_steps: int = 6,
                    activation_threshold: float = 0.03) -> Event:
    """
    Propagate an event through the network from the origin agent.
    Uses a BFS-like cascade with decay.
    """
    origin = event.origin_agent
    visited: set[str] = set()
    frontier: set[str] = {origin}
    event.affected_agents = set()

    # Set origin agent's opinion
    origin_agent = get_agent(G, origin)
    origin_agent.opinion_state[event.topic] = event.sentiment
    event.affected_agents.add(origin)

    decay = 0.85  # each hop reduces intensity

    for step in range(max_steps):
        if not frontier:
            break

        next_frontier: set[str] = set()
        step_results: list[EventResult] = []
        current_intensity = event.intensity * (decay ** step)

        for node_id in frontier:
            visited.add(node_id)
            source_agent = get_agent(G, node_id)

            for neighbor_id in G.neighbors(node_id):
                if neighbor_id in visited:
                    continue

                agent = get_agent(G, neighbor_id)
                edge_data = G.edges[node_id, neighbor_id]

                # compute reaction (with habitus-aware source context)
                reaction = _reaction_strength(agent, event, edge_data, source_agent)
                effective_delta = reaction * current_intensity

                # openness modulates how much they actually shift
                # capital field relevance boosts openness for relevant topics
                field_match = capital_field_relevance(agent.capital, event.topic)
                effective_delta *= (agent.openness + field_match * 0.15)

                # Media amplification: agents exposed to media receive amplified events
                if agent.media and hasattr(G, '_media_landscape') and G._media_landscape:
                    amp = media_event_amplifier(G._media_landscape, agent.media, event.intensity)
                    effective_delta *= amp

                # loyalty: if event targets their clan negatively, resist
                if event.target_clan == agent.clan and event.sentiment < 0:
                    effective_delta *= (1 - agent.loyalty * 0.7)

                old_opinion = agent.opinion_state.get(event.topic, 0.0)
                new_opinion = max(-1.0, min(1.0, old_opinion + effective_delta))
                agent.opinion_state[event.topic] = new_opinion

                # Social capital lowers activation threshold (well-connected spread more)
                personal_threshold = activation_threshold * (1 - agent.capital.social * 0.3)
                activated = abs(effective_delta) >= personal_threshold
                if activated:
                    next_frontier.add(neighbor_id)
                    event.affected_agents.add(neighbor_id)

                stance = "neutral"
                if new_opinion > 0.15:
                    stance = "support"
                elif new_opinion < -0.15:
                    stance = "oppose"

                step_results.append(EventResult(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    old_opinion=old_opinion,
                    new_opinion=new_opinion,
                    delta=effective_delta,
                    stance=stance,
                    activated=activated,
                ))

        event.propagation_log.append(PropagationStep(
            step=step,
            results=step_results,
            frontier_size=len(next_frontier),
        ))

        frontier = next_frontier - visited

    return event


def create_event(
    G: nx.Graph,
    event_type: str,
    title: str,
    origin_agent_id: str,
    topic: str,
    sentiment: float = 0.5,
    intensity: float = 0.7,
    political_bias: float = 0.0,
    target_district: str | None = None,
    target_clan: str | None = None,
    description: str = "",
    max_steps: int = 6,
) -> Event:
    """Create and propagate an event through the network."""
    template = EVENT_TEMPLATES.get(event_type, EVENT_TEMPLATES["custom"])

    event = Event(
        id=str(uuid.uuid4())[:8],
        event_type=event_type,
        title=title,
        description=description or template["desc"],
        origin_agent=origin_agent_id,
        topic=topic,
        sentiment=max(-1, min(1, sentiment)),
        intensity=max(0, min(1, intensity)),
        political_bias=max(-3, min(3, political_bias)),
        target_district=target_district,
        target_clan=target_clan,
    )

    return propagate_event(G, event, max_steps=max_steps)


# ── Analysis helpers ─────────────────────────────────────────────────────────

def opinion_summary(G: nx.Graph, topic: str) -> dict:
    """Aggregate opinion on a topic across the network."""
    opinions = []
    by_clan: dict[str, list[float]] = {}
    by_district: dict[str, list[float]] = {}
    by_politics: dict[str, list[float]] = {}

    for n in G.nodes:
        a: Agent = G.nodes[n]["agent"]
        op = a.opinion_state.get(topic, 0.0)
        opinions.append(op)
        by_clan.setdefault(a.clan, []).append(op)
        by_district.setdefault(a.district, []).append(op)
        by_politics.setdefault(a.politics.value, []).append(op)

    def avg(lst):
        return round(sum(lst) / len(lst), 3) if lst else 0

    return {
        "topic": topic,
        "mean": avg(opinions),
        "support": sum(1 for o in opinions if o > 0.15),
        "oppose": sum(1 for o in opinions if o < -0.15),
        "neutral": sum(1 for o in opinions if -0.15 <= o <= 0.15),
        "by_clan": {k: avg(v) for k, v in by_clan.items()},
        "by_district": {k: avg(v) for k, v in by_district.items()},
        "by_politics": {k: avg(v) for k, v in by_politics.items()},
    }


def find_bridges(G: nx.Graph) -> list[dict]:
    """Find bridge agents who connect otherwise disconnected communities."""
    bc = nx.betweenness_centrality(G, weight="weight")
    top = sorted(bc.items(), key=lambda x: x[1], reverse=True)[:20]
    return [
        {
            "agent": get_agent(G, nid).to_dict(),
            "betweenness": round(score, 4),
        }
        for nid, score in top
    ]


def find_coalitions(G: nx.Graph, topic: str) -> list[dict]:
    """Detect emergent coalitions around a topic using opinion alignment."""
    # Build subgraph of agents with opinions
    opinionated = [n for n in G.nodes
                   if abs(G.nodes[n]["agent"].opinion_state.get(topic, 0)) > 0.1]
    if not opinionated:
        return []

    sub = G.subgraph(opinionated).copy()

    # Remove edges where agents disagree
    to_remove = []
    for u, v in sub.edges():
        ou = sub.nodes[u]["agent"].opinion_state.get(topic, 0)
        ov = sub.nodes[v]["agent"].opinion_state.get(topic, 0)
        if ou * ov < 0:  # opposite signs
            to_remove.append((u, v))
    sub.remove_edges_from(to_remove)

    coalitions = []
    for i, comp in enumerate(nx.connected_components(sub)):
        members = [get_agent(G, n) for n in comp]
        avg_opinion = sum(m.opinion_state.get(topic, 0) for m in members) / len(members)
        coalitions.append({
            "id": i,
            "size": len(members),
            "stance": "support" if avg_opinion > 0 else "oppose",
            "avg_opinion": round(avg_opinion, 3),
            "clans": list(set(m.clan for m in members)),
            "top_members": sorted(
                [{"id": m.id, "name": m.name, "influence": round(m.influence, 3)}
                 for m in members],
                key=lambda x: x["influence"], reverse=True
            )[:5],
        })

    return sorted(coalitions, key=lambda c: c["size"], reverse=True)
