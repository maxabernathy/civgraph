"""
CivGraph — Agent-based modeling on a social graph.

Core model: 500 individuals in a mid-scale city, each with clan ties,
interests, political leanings, Bourdieusian capital, habitus, and
lifecycle-dependent influence relationships.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import networkx as nx

from capital import (
    Capital, Habitus, SocialClass, EducationTrack, LifePhase,
    EU_CONFIG, life_phase_from_age, generate_age, generate_capital,
    generate_habitus, pick_education, pick_class, habitus_affinity,
    capital_to_influence, transmit_economic, transmit_cultural,
    transmit_symbolic, inherit_habitus,
)


# ── Constants ────────────────────────────────────────────────────────────────

CLAN_NAMES = [
    "Harmon", "Voss", "Delacroix", "Okafor", "Petrov", "Nakamura", "Reyes",
    "Lindqvist", "Ashworth", "Mbeki", "Kaplan", "Ferreira", "Xu", "Moreau",
    "Strand", "Bassi", "Kowalski", "Al-Rashid", "Brennan", "Takahashi",
]

INTEREST_POOL = [
    "real_estate", "tech", "healthcare", "education", "arts", "finance",
    "manufacturing", "media", "law", "energy", "agriculture", "hospitality",
    "transport", "security", "environment", "sports", "retail", "philanthropy",
    "religion", "unions",
]

OCCUPATIONS = [
    "mayor", "council_member", "business_owner", "developer", "lawyer",
    "doctor", "journalist", "professor", "banker", "police_chief",
    "union_leader", "pastor", "nonprofit_director", "lobbyist", "engineer",
    "restaurateur", "artist", "contractor", "realtor", "consultant",
]

DISTRICTS = [
    "Downtown", "Northside", "Riverside", "Old Quarter", "Tech Park",
    "Eastgate", "Harbor", "University Hill", "Midtown", "Southfield",
]

# Each clan has a "class center" — some clans trend upper, some lower
CLAN_CLASS_CENTERS = {
    "Delacroix": 3.8, "Ashworth": 3.5, "Kaplan": 3.3, "Moreau": 3.2,
    "Harmon": 2.8, "Nakamura": 2.7, "Lindqvist": 2.6, "Strand": 2.5,
    "Voss": 2.3, "Xu": 2.3, "Takahashi": 2.2, "Bassi": 2.1,
    "Brennan": 2.0, "Ferreira": 1.9, "Okafor": 1.8, "Al-Rashid": 1.7,
    "Petrov": 1.6, "Reyes": 1.4, "Mbeki": 1.3, "Kowalski": 1.1,
}


class PoliticalLeaning(str, Enum):
    FAR_LEFT = "far_left"
    LEFT = "left"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    RIGHT = "right"
    FAR_RIGHT = "far_right"

    @property
    def numeric(self) -> float:
        mapping = {
            "far_left": -3, "left": -2, "center_left": -1,
            "center": 0, "center_right": 1, "right": 2, "far_right": 3,
        }
        return mapping[self.value]

    @classmethod
    def from_numeric(cls, v: float) -> "PoliticalLeaning":
        rounded = max(-3, min(3, round(v)))
        rev = {-3: cls.FAR_LEFT, -2: cls.LEFT, -1: cls.CENTER_LEFT,
               0: cls.CENTER, 1: cls.CENTER_RIGHT, 2: cls.RIGHT, 3: cls.FAR_RIGHT}
        return rev[rounded]


# ── Agent ────────────────────────────────────────────────────────────────────

@dataclass
class Agent:
    id: str
    name: str
    clan: str
    district: str
    occupation: str
    interests: list[str]
    politics: PoliticalLeaning
    age: int
    life_phase: LifePhase
    capital: Capital
    habitus: Habitus
    openness: float
    assertiveness: float
    loyalty: float
    generation: int = 0
    parent_id: str | None = None
    opinion_state: dict[str, float] = field(default_factory=dict)
    norms: dict[str, float] = field(default_factory=dict)
    satisfaction: float = 1.0
    emergence_score: float = 0.0

    @property
    def influence(self) -> float:
        return capital_to_influence(self.capital)

    @property
    def resources(self) -> float:
        return self.capital.economic

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "clan": self.clan,
            "district": self.district,
            "occupation": self.occupation,
            "interests": self.interests,
            "politics": self.politics.value,
            "age": self.age,
            "life_phase": self.life_phase.value,
            "influence": round(self.influence, 3),
            "openness": round(self.openness, 3),
            "assertiveness": round(self.assertiveness, 3),
            "loyalty": round(self.loyalty, 3),
            "resources": round(self.resources, 3),
            "capital": self.capital.to_dict(),
            "habitus": self.habitus.to_dict(),
            "generation": self.generation,
            "parent_id": self.parent_id,
            "opinion_state": {k: round(v, 3) for k, v in self.opinion_state.items()},
            "norms": {k: round(v, 3) for k, v in self.norms.items()},
            "satisfaction": round(self.satisfaction, 3),
            "emergence_score": round(self.emergence_score, 3),
        }


# ── Relationship types ──────────────────────────────────────────────────────

class RelType(str, Enum):
    CLAN = "clan"
    PROFESSIONAL = "professional"
    POLITICAL = "political"
    DISTRICT = "district"
    FRIENDSHIP = "friendship"
    RIVALRY = "rivalry"
    HABITUS = "habitus"


# ── City Generator ───────────────────────────────────────────────────────────

FIRST_NAMES = [
    "James", "Maria", "Chen", "Aisha", "Dmitri", "Yuki", "Carlos", "Ingrid",
    "David", "Fatima", "Liam", "Priya", "Omar", "Sofia", "Kai", "Elena",
    "Tomas", "Amara", "Henrik", "Mei", "Ravi", "Clara", "Andre", "Hana",
    "Erik", "Zara", "Leo", "Nadia", "Finn", "Isla", "Marco", "Lena",
    "Sven", "Rosa", "Amir", "Vera", "Hugo", "Anya", "Samir", "Freya",
    "Dante", "Mila", "Oscar", "Layla", "Ivan", "Sara", "Noah", "Dina",
    "Axel", "Leah",
]


def generate_city(n: int = 500, seed: int | None = None) -> nx.Graph:
    """Build a social graph of *n* influential people in a mid-scale city."""
    rng = random.Random(seed)
    # Also seed the module-level random for libraries that use it
    if seed is not None:
        random.seed(seed)

    G = nx.Graph()

    # ── assign clans with power-law sizes ────────────────────────────────
    clan_weights = [rng.paretovariate(1.5) for _ in CLAN_NAMES]
    total = sum(clan_weights)
    clan_sizes = [max(5, int(w / total * n)) for w in clan_weights]
    diff = n - sum(clan_sizes)
    for i in range(abs(diff)):
        idx = i % len(clan_sizes)
        clan_sizes[idx] += 1 if diff > 0 else (-1 if clan_sizes[idx] > 5 else 0)

    agents: list[Agent] = []
    clan_pol_cache: dict[str, float] = {}

    for ci, clan in enumerate(CLAN_NAMES):
        clan_district = rng.choice(DISTRICTS)
        clan_class_center = CLAN_CLASS_CENTERS.get(clan, 2.0)

        # Clan political tendency (set once per clan)
        clan_pol = max(-3, min(3, rng.gauss(0, 1.5)))
        clan_pol_cache[clan] = clan_pol

        for j in range(clan_sizes[ci]):
            # District
            district = clan_district if rng.random() < 0.6 else rng.choice(DISTRICTS)

            # Politics (clan-correlated + noise)
            pol = max(-3, min(3, clan_pol + rng.gauss(0, 0.8)))

            # Interests
            n_interests = rng.randint(1, 4)
            interests = rng.sample(INTEREST_POOL, n_interests)

            # Age and lifecycle
            age = generate_age(rng)
            life_phase = life_phase_from_age(age)

            # Social class (clan-correlated)
            origin_class = pick_class(clan_class_center, rng)
            education_track = pick_education(origin_class, rng)

            # Habitus
            habitus = generate_habitus(origin_class, education_track, age, rng)

            # Capital
            capital = generate_capital(origin_class, education_track, age, rng)

            # Personality traits
            openness = rng.betavariate(2, 5)
            assertiveness = rng.betavariate(2, 3)
            loyalty = rng.betavariate(3, 2)

            first = rng.choice(FIRST_NAMES)
            agent = Agent(
                id=str(uuid.uuid4())[:12],
                name=f"{first} {clan}",
                clan=clan,
                district=district,
                occupation=rng.choice(OCCUPATIONS),
                interests=interests,
                politics=PoliticalLeaning.from_numeric(pol),
                age=age,
                life_phase=life_phase,
                capital=capital,
                habitus=habitus,
                openness=openness,
                assertiveness=assertiveness,
                loyalty=loyalty,
            )
            agents.append(agent)
            G.add_node(agent.id, agent=agent)

    # ── Assign parent-child within clans ─────────────────────────────────
    by_clan: dict[str, list[Agent]] = {}
    for a in agents:
        by_clan.setdefault(a.clan, []).append(a)

    for clan, members in by_clan.items():
        elders = [m for m in members if m.age >= 45]
        young = [m for m in members if m.age < 30]
        for child in young:
            if elders and rng.random() < 0.7:
                parent = rng.choice(elders)
                child.parent_id = parent.id
                child.generation = parent.generation + 1
                # Intergenerational transmission
                child.capital.economic = max(
                    child.capital.economic,
                    transmit_economic(parent.capital.economic, rng)
                )
                child.capital.cultural = max(
                    child.capital.cultural,
                    transmit_cultural(parent.capital, parent.habitus, rng)
                )
                clan_avg_sym = sum(m.capital.symbolic for m in members) / len(members)
                child.capital.symbolic = max(
                    child.capital.symbolic,
                    transmit_symbolic(parent.capital.symbolic, clan_avg_sym, rng)
                )
                child.habitus = inherit_habitus(
                    parent.habitus, child.habitus.current_class,
                    child.habitus.education_track, rng
                )
                child.capital.clamp()

    # ── edges ────────────────────────────────────────────────────────────
    # 1) Clan bonds (small-world ring + shortcuts)
    for clan, members in by_clan.items():
        for i, a in enumerate(members):
            for d in (1, 2):
                b = members[(i + d) % len(members)]
                if a.id != b.id:
                    w = 0.5 + 0.5 * min(a.loyalty, b.loyalty)
                    G.add_edge(a.id, b.id, weight=round(w, 3), rel=RelType.CLAN.value)
            if rng.random() < 0.3:
                b = rng.choice(members)
                if a.id != b.id and not G.has_edge(a.id, b.id):
                    G.add_edge(a.id, b.id, weight=round(0.3 + rng.random() * 0.4, 3),
                               rel=RelType.CLAN.value)

    # 2) District neighbors
    by_district: dict[str, list[Agent]] = {}
    for a in agents:
        by_district.setdefault(a.district, []).append(a)
    for district, members in by_district.items():
        for a in members:
            n_neighbors = rng.randint(1, 3)
            targets = rng.sample(members, min(n_neighbors, len(members)))
            for b in targets:
                if a.id != b.id and not G.has_edge(a.id, b.id):
                    w = 0.2 + rng.random() * 0.3
                    G.add_edge(a.id, b.id, weight=round(w, 3), rel=RelType.DISTRICT.value)

    # 3) Professional ties
    by_occ: dict[str, list[Agent]] = {}
    for a in agents:
        by_occ.setdefault(a.occupation, []).append(a)
    for occ, members in by_occ.items():
        for a in members:
            if rng.random() < 0.4:
                b = rng.choice(members)
                if a.id != b.id and not G.has_edge(a.id, b.id):
                    w = 0.3 + rng.random() * 0.3
                    G.add_edge(a.id, b.id, weight=round(w, 3), rel=RelType.PROFESSIONAL.value)

    # 4) Political alliances
    for a in agents:
        if rng.random() < 0.15:
            candidates = [b for b in agents
                          if b.id != a.id
                          and abs(a.politics.numeric - b.politics.numeric) <= 1
                          and not G.has_edge(a.id, b.id)]
            if candidates:
                b = rng.choice(candidates)
                w = 0.3 + rng.random() * 0.4
                G.add_edge(a.id, b.id, weight=round(w, 3), rel=RelType.POLITICAL.value)

    # 5) Shared-interest friendships
    for a in agents:
        if rng.random() < 0.2:
            candidates = [b for b in agents
                          if b.id != a.id
                          and set(a.interests) & set(b.interests)
                          and not G.has_edge(a.id, b.id)]
            if candidates:
                b = rng.choice(candidates)
                overlap = len(set(a.interests) & set(b.interests))
                w = 0.2 + 0.15 * overlap
                G.add_edge(a.id, b.id, weight=round(w, 3), rel=RelType.FRIENDSHIP.value)

    # 6) Rivalries
    for a in agents:
        if rng.random() < 0.05:
            candidates = [b for b in agents
                          if b.clan != a.clan
                          and abs(a.influence - b.influence) < 0.15
                          and abs(a.politics.numeric - b.politics.numeric) >= 3
                          and not G.has_edge(a.id, b.id)]
            if candidates:
                b = rng.choice(candidates)
                G.add_edge(a.id, b.id, weight=round(-0.3 - rng.random() * 0.5, 3),
                           rel=RelType.RIVALRY.value)

    # 7) Hub connectors
    top = sorted(agents, key=lambda a: a.influence, reverse=True)[:30]
    for i, a in enumerate(top):
        for b in top[i + 1:]:
            if rng.random() < 0.25 and not G.has_edge(a.id, b.id):
                w = 0.4 + rng.random() * 0.4
                G.add_edge(a.id, b.id, weight=round(w, 3), rel=RelType.PROFESSIONAL.value)

    # 8) Habitus affinity ties — cross-clan bonds between similar dispositions
    for i, a in enumerate(agents):
        if rng.random() < 0.12:
            best_aff = 0
            best_b = None
            # Sample 20 random candidates (avoid full O(n^2))
            sample = rng.sample(agents, min(20, len(agents)))
            for b in sample:
                if b.id == a.id or b.clan == a.clan or G.has_edge(a.id, b.id):
                    continue
                aff = habitus_affinity(a.habitus, b.habitus)
                if aff > best_aff and aff > 0.55:
                    best_aff = aff
                    best_b = b
            if best_b:
                w = 0.3 + best_aff * 0.4
                G.add_edge(a.id, best_b.id, weight=round(w, 3), rel=RelType.HABITUS.value)

    # ── Recompute social capital from actual graph degree ────────────────
    for n_id in G.nodes:
        agent = G.nodes[n_id]["agent"]
        degree = G.degree(n_id)
        agent.capital.social = min(1.0, 0.1 + math.sqrt(degree) / 8)
        agent.capital.clamp()

    return G


# ── Graph queries ────────────────────────────────────────────────────────────

def get_agent(G: nx.Graph, node_id: str) -> Agent:
    return G.nodes[node_id]["agent"]


def graph_stats(G: nx.Graph) -> dict:
    agents = [G.nodes[n]["agent"] for n in G.nodes]
    clans = {}
    districts = {}
    politics = {}
    classes = {}
    phases = {}
    for a in agents:
        clans[a.clan] = clans.get(a.clan, 0) + 1
        districts[a.district] = districts.get(a.district, 0) + 1
        politics[a.politics.value] = politics.get(a.politics.value, 0) + 1
        classes[a.habitus.current_class.value] = classes.get(a.habitus.current_class.value, 0) + 1
        phases[a.life_phase.value] = phases.get(a.life_phase.value, 0) + 1

    # Capital averages
    n_agents = len(agents) or 1
    avg_capital = {
        "economic": round(sum(a.capital.economic for a in agents) / n_agents, 3),
        "cultural": round(sum(a.capital.cultural for a in agents) / n_agents, 3),
        "social": round(sum(a.capital.social for a in agents) / n_agents, 3),
        "symbolic": round(sum(a.capital.symbolic for a in agents) / n_agents, 3),
    }

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": round(nx.density(G), 4),
        "components": nx.number_connected_components(G),
        "avg_clustering": round(nx.average_clustering(G), 4),
        "clans": clans,
        "districts": districts,
        "politics": politics,
        "classes": classes,
        "life_phases": phases,
        "avg_capital": avg_capital,
    }


def export_for_d3(G: nx.Graph, highlight: set[str] | None = None) -> dict:
    """Export graph in D3-compatible format."""
    nodes = []
    for n in G.nodes:
        a: Agent = G.nodes[n]["agent"]
        nodes.append({
            "id": a.id,
            "name": a.name,
            "clan": a.clan,
            "district": a.district,
            "occupation": a.occupation,
            "politics": a.politics.value,
            "influence": a.influence,
            "interests": a.interests,
            "resources": a.resources,
            "age": a.age,
            "life_phase": a.life_phase.value,
            "social_class": a.habitus.current_class.value,
            "education_track": a.habitus.education_track.value,
            "capital_volume": round(a.capital.total_volume, 3),
            "capital": a.capital.to_dict(),
            "highlighted": n in (highlight or set()),
            "degree": G.degree(n),
            "satisfaction": round(a.satisfaction, 3),
            "emergence_score": round(a.emergence_score, 3),
            "norm_count": len(a.norms),
        })

    links = []
    for u, v, d in G.edges(data=True):
        links.append({
            "source": u,
            "target": v,
            "weight": d.get("weight", 0.5),
            "rel": d.get("rel", "unknown"),
        })

    return {"nodes": nodes, "links": links}
