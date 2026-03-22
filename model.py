"""
CivGraph — Agent-based modeling on a social graph.

Core model: 500 individuals in a mid-scale city, each with clan ties,
interests, political leanings, and influence relationships.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import networkx as nx


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
    influence: float          # 0-1
    openness: float           # 0-1, how easily swayed
    assertiveness: float      # 0-1, how strongly they push views
    loyalty: float            # 0-1, clan loyalty
    resources: float          # 0-1, economic/social capital
    opinion_state: dict[str, float] = field(default_factory=dict)
    # opinion_state: topic -> sentiment (-1 to 1)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "clan": self.clan,
            "district": self.district,
            "occupation": self.occupation,
            "interests": self.interests,
            "politics": self.politics.value,
            "influence": round(self.influence, 3),
            "openness": round(self.openness, 3),
            "assertiveness": round(self.assertiveness, 3),
            "loyalty": round(self.loyalty, 3),
            "resources": round(self.resources, 3),
            "opinion_state": {k: round(v, 3) for k, v in self.opinion_state.items()},
        }


# ── Relationship types ──────────────────────────────────────────────────────

class RelType(str, Enum):
    CLAN = "clan"
    PROFESSIONAL = "professional"
    POLITICAL = "political"
    DISTRICT = "district"
    FRIENDSHIP = "friendship"
    RIVALRY = "rivalry"


# ── City Generator ───────────────────────────────────────────────────────────

FIRST_NAMES = [
    "James", "Maria", "Chen", "Aisha", "Dmitri", "Yuki", "Carlos", "Ingrid",
    "David", "Fatima", "Liam", "Priya", "Omar", "Sofia", "Kai", "Elena",
    "Tomás", "Amara", "Henrik", "Mei", "Ravi", "Clara", "André", "Hana",
    "Erik", "Zara", "Leo", "Nadia", "Finn", "Isla", "Marco", "Lena",
    "Sven", "Rosa", "Amir", "Vera", "Hugo", "Anya", "Samir", "Freya",
    "Dante", "Mila", "Oscar", "Layla", "Ivan", "Sara", "Noah", "Dina",
    "Axel", "Leah",
]


def generate_city(n: int = 500, seed: int | None = None) -> nx.Graph:
    """Build a social graph of *n* influential people in a mid-scale city."""
    if seed is not None:
        random.seed(seed)

    G = nx.Graph()

    # ── assign clans with power-law sizes ────────────────────────────────
    clan_weights = [random.paretovariate(1.5) for _ in CLAN_NAMES]
    total = sum(clan_weights)
    clan_sizes = [max(5, int(w / total * n)) for w in clan_weights]
    # adjust to hit exactly n
    diff = n - sum(clan_sizes)
    for i in range(abs(diff)):
        idx = i % len(clan_sizes)
        clan_sizes[idx] += 1 if diff > 0 else -1

    agents: list[Agent] = []
    idx = 0
    for ci, clan in enumerate(CLAN_NAMES):
        clan_district = random.choice(DISTRICTS)  # clan home base
        for j in range(clan_sizes[ci]):
            # district: 60% chance home base, 40% elsewhere
            district = clan_district if random.random() < 0.6 else random.choice(DISTRICTS)
            pol_center = random.gauss(0, 1.5)
            pol_center = max(-3, min(3, pol_center))

            # clan members share political tendency (with noise)
            if j == 0:
                clan_pol = pol_center
            pol = max(-3, min(3, clan_pol + random.gauss(0, 0.8)))

            n_interests = random.randint(1, 4)
            interests = random.sample(INTEREST_POOL, n_interests)

            # influence follows power law within clan
            raw_inf = random.paretovariate(2.0)
            influence = min(1.0, raw_inf / 5.0)

            first = random.choice(FIRST_NAMES)
            agent = Agent(
                id=str(uuid.uuid4())[:8],
                name=f"{first} {clan}",
                clan=clan,
                district=district,
                occupation=random.choice(OCCUPATIONS),
                interests=interests,
                politics=PoliticalLeaning.from_numeric(pol),
                influence=influence,
                openness=random.betavariate(2, 5),       # most people moderately open
                assertiveness=random.betavariate(2, 3),
                loyalty=random.betavariate(3, 2),         # skewed toward loyal
                resources=random.betavariate(2, 5) * influence + random.random() * 0.3,
            )
            agents.append(agent)
            G.add_node(agent.id, agent=agent)
            idx += 1

    # ── edges ────────────────────────────────────────────────────────────
    agent_map: dict[str, Agent] = {a.id: a for a in agents}

    # 1) Clan bonds — everyone in same clan knows each other (small-world)
    by_clan: dict[str, list[Agent]] = {}
    for a in agents:
        by_clan.setdefault(a.clan, []).append(a)

    for clan, members in by_clan.items():
        # ring lattice within clan + random shortcuts
        for i, a in enumerate(members):
            # connect to 2 nearest neighbors on ring
            for d in (1, 2):
                b = members[(i + d) % len(members)]
                if a.id != b.id:
                    w = 0.5 + 0.5 * min(a.loyalty, b.loyalty)
                    G.add_edge(a.id, b.id, weight=round(w, 3),
                               rel=RelType.CLAN.value)
            # random clan shortcut (30%)
            if random.random() < 0.3:
                b = random.choice(members)
                if a.id != b.id and not G.has_edge(a.id, b.id):
                    G.add_edge(a.id, b.id, weight=round(0.3 + random.random() * 0.4, 3),
                               rel=RelType.CLAN.value)

    # 2) District neighbors
    by_district: dict[str, list[Agent]] = {}
    for a in agents:
        by_district.setdefault(a.district, []).append(a)

    for district, members in by_district.items():
        for a in members:
            n_neighbors = random.randint(1, 3)
            targets = random.sample(members, min(n_neighbors, len(members)))
            for b in targets:
                if a.id != b.id and not G.has_edge(a.id, b.id):
                    w = 0.2 + random.random() * 0.3
                    G.add_edge(a.id, b.id, weight=round(w, 3),
                               rel=RelType.DISTRICT.value)

    # 3) Professional ties — same occupation
    by_occ: dict[str, list[Agent]] = {}
    for a in agents:
        by_occ.setdefault(a.occupation, []).append(a)

    for occ, members in by_occ.items():
        for a in members:
            if random.random() < 0.4:
                b = random.choice(members)
                if a.id != b.id and not G.has_edge(a.id, b.id):
                    w = 0.3 + random.random() * 0.3
                    G.add_edge(a.id, b.id, weight=round(w, 3),
                               rel=RelType.PROFESSIONAL.value)

    # 4) Political alliances — similar politics
    for a in agents:
        if random.random() < 0.15:
            candidates = [b for b in agents
                          if b.id != a.id
                          and abs(a.politics.numeric - b.politics.numeric) <= 1
                          and not G.has_edge(a.id, b.id)]
            if candidates:
                b = random.choice(candidates)
                w = 0.3 + random.random() * 0.4
                G.add_edge(a.id, b.id, weight=round(w, 3),
                           rel=RelType.POLITICAL.value)

    # 5) Shared-interest friendships
    for a in agents:
        if random.random() < 0.2:
            candidates = [b for b in agents
                          if b.id != a.id
                          and set(a.interests) & set(b.interests)
                          and not G.has_edge(a.id, b.id)]
            if candidates:
                b = random.choice(candidates)
                overlap = len(set(a.interests) & set(b.interests))
                w = 0.2 + 0.15 * overlap
                G.add_edge(a.id, b.id, weight=round(w, 3),
                           rel=RelType.FRIENDSHIP.value)

    # 6) Rivalries — cross-clan, similar influence, different politics
    for a in agents:
        if random.random() < 0.05:
            candidates = [b for b in agents
                          if b.clan != a.clan
                          and abs(a.influence - b.influence) < 0.15
                          and abs(a.politics.numeric - b.politics.numeric) >= 3
                          and not G.has_edge(a.id, b.id)]
            if candidates:
                b = random.choice(candidates)
                G.add_edge(a.id, b.id, weight=round(-0.3 - random.random() * 0.5, 3),
                           rel=RelType.RIVALRY.value)

    # 7) Hub connectors — top influencers connect across clans
    top = sorted(agents, key=lambda a: a.influence, reverse=True)[:30]
    for i, a in enumerate(top):
        for b in top[i + 1:]:
            if random.random() < 0.25 and not G.has_edge(a.id, b.id):
                w = 0.4 + random.random() * 0.4
                G.add_edge(a.id, b.id, weight=round(w, 3),
                           rel=RelType.PROFESSIONAL.value)

    return G


# ── Graph queries ────────────────────────────────────────────────────────────

def get_agent(G: nx.Graph, node_id: str) -> Agent:
    return G.nodes[node_id]["agent"]


def graph_stats(G: nx.Graph) -> dict:
    agents = [G.nodes[n]["agent"] for n in G.nodes]
    clans = {}
    districts = {}
    politics = {}
    for a in agents:
        clans[a.clan] = clans.get(a.clan, 0) + 1
        districts[a.district] = districts.get(a.district, 0) + 1
        politics[a.politics.value] = politics.get(a.politics.value, 0) + 1

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": round(nx.density(G), 4),
        "components": nx.number_connected_components(G),
        "avg_clustering": round(nx.average_clustering(G), 4),
        "clans": clans,
        "districts": districts,
        "politics": politics,
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
            "highlighted": n in (highlight or set()),
            "degree": G.degree(n),
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
