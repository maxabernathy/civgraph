"""
CivGraph -- Institutional membership model: boards, associations, clubs.

Agents participate in institutions beyond family and workplace. These
create cross-cutting ties, concentrate power through interlocking
directorates, generate economic interests, and shape both social and
symbolic capital accumulation.

Institution types:

  1. **Professional boards** — corporate governance, industry bodies.
     High prestige, high economic benefit, low time.
     Access: upper/upper-middle class, high economic capital.

  2. **Civic associations** — community councils, volunteer orgs, NGOs.
     Moderate prestige, low economic benefit, moderate time.
     Access: broad, especially middle class with social capital.

  3. **Cultural clubs** — arts patronage, literary/music societies.
     Moderate prestige, low economic benefit, moderate time.
     Access: education-driven, cultural capital.

  4. **Social clubs** — networking, dining clubs, lodges, alumni.
     High prestige among members, moderate economic benefit.
     Access: class-stratified, referral-based.

  5. **Political organizations** — party committees, advocacy groups.
     Low-moderate prestige, low economic benefit, high time.
     Access: politically active agents.

  6. **Religious/community groups** — congregations, mutual aid.
     Low prestige, low economic benefit, high social benefit.
     Access: broad, especially lower/middle class.

  7. **Industry bodies** — trade unions, professional associations.
     Moderate prestige, moderate economic benefit.
     Access: occupation-driven.

  8. **Alumni networks** — university, school connections.
     Moderate prestige, moderate economic benefit.
     Access: education-track driven.

Plus: **skill currency** and **lifelong learning** deepening the
existing education system — skills decay without refreshment, and
institutional membership can provide continuing education.

References:
  - Mizruchi (1996): interlocking directorates
  - Putnam (2000): Bowling Alone (civic associations and social capital)
  - Useem (1984): The Inner Circle (corporate board networks)
  - Bourdieu (1984): clubs as capital accumulation sites
  - Granovetter (1973): weak ties through associational membership
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum


# ══════════════════════════════════════════════════════════════════════════════
# INSTITUTION TYPES
# ══════════════════════════════════════════════════════════════════════════════

class InstitutionType(str, Enum):
    PROFESSIONAL_BOARD = "professional_board"
    CIVIC_ASSOCIATION = "civic_association"
    CULTURAL_CLUB = "cultural_club"
    SOCIAL_CLUB = "social_club"
    POLITICAL_ORG = "political_org"
    RELIGIOUS_COMMUNITY = "religious_community"
    INDUSTRY_BODY = "industry_body"
    ALUMNI_NETWORK = "alumni_network"


@dataclass(frozen=True)
class InstitutionProfile:
    """Static profile of an institution type."""
    name: str
    prestige: float              # 0-1, symbolic capital gain per year
    economic_benefit: float      # 0-1, economic opportunities/board fees
    social_benefit: float        # 0-1, network expansion
    time_commitment: float       # 0-1, fraction of agent attention
    cultural_benefit: float      # 0-1, cultural capital gain
    # Access requirements (soft thresholds)
    min_class_rank: int          # 0-4 minimum class for typical access
    min_economic: float          # economic capital threshold
    min_cultural: float          # cultural capital threshold
    education_affinity: list[str]  # education tracks with natural affinity


INSTITUTION_PROFILES: dict[InstitutionType, InstitutionProfile] = {
    InstitutionType.PROFESSIONAL_BOARD: InstitutionProfile(
        name="Professional Board",
        prestige=0.85, economic_benefit=0.80, social_benefit=0.70,
        time_commitment=0.15, cultural_benefit=0.10,
        min_class_rank=3, min_economic=0.55, min_cultural=0.30,
        education_affinity=["elite", "academic"],
    ),
    InstitutionType.CIVIC_ASSOCIATION: InstitutionProfile(
        name="Civic Association",
        prestige=0.35, economic_benefit=0.10, social_benefit=0.65,
        time_commitment=0.20, cultural_benefit=0.15,
        min_class_rank=1, min_economic=0.20, min_cultural=0.15,
        education_affinity=["academic", "applied", "elite"],
    ),
    InstitutionType.CULTURAL_CLUB: InstitutionProfile(
        name="Cultural Club",
        prestige=0.50, economic_benefit=0.10, social_benefit=0.45,
        time_commitment=0.15, cultural_benefit=0.60,
        min_class_rank=2, min_economic=0.25, min_cultural=0.40,
        education_affinity=["academic", "elite"],
    ),
    InstitutionType.SOCIAL_CLUB: InstitutionProfile(
        name="Social Club",
        prestige=0.60, economic_benefit=0.40, social_benefit=0.75,
        time_commitment=0.10, cultural_benefit=0.20,
        min_class_rank=2, min_economic=0.35, min_cultural=0.20,
        education_affinity=["elite", "academic", "applied"],
    ),
    InstitutionType.POLITICAL_ORG: InstitutionProfile(
        name="Political Organization",
        prestige=0.30, economic_benefit=0.15, social_benefit=0.55,
        time_commitment=0.25, cultural_benefit=0.10,
        min_class_rank=0, min_economic=0.15, min_cultural=0.10,
        education_affinity=["academic", "applied", "vocational", "elite"],
    ),
    InstitutionType.RELIGIOUS_COMMUNITY: InstitutionProfile(
        name="Religious Community",
        prestige=0.20, economic_benefit=0.05, social_benefit=0.70,
        time_commitment=0.15, cultural_benefit=0.15,
        min_class_rank=0, min_economic=0.10, min_cultural=0.05,
        education_affinity=["vocational", "applied", "academic", "elite"],
    ),
    InstitutionType.INDUSTRY_BODY: InstitutionProfile(
        name="Industry Body",
        prestige=0.45, economic_benefit=0.50, social_benefit=0.55,
        time_commitment=0.10, cultural_benefit=0.05,
        min_class_rank=1, min_economic=0.25, min_cultural=0.15,
        education_affinity=["applied", "academic", "elite"],
    ),
    InstitutionType.ALUMNI_NETWORK: InstitutionProfile(
        name="Alumni Network",
        prestige=0.40, economic_benefit=0.35, social_benefit=0.60,
        time_commitment=0.05, cultural_benefit=0.25,
        min_class_rank=1, min_economic=0.15, min_cultural=0.25,
        education_affinity=["academic", "elite"],
    ),
}


# ── Named institution instances per type ───────────────────────────────────
# Each city has a handful of specific named institutions agents can join.

INSTITUTION_NAMES: dict[InstitutionType, list[str]] = {
    InstitutionType.PROFESSIONAL_BOARD: [
        "City Development Corp", "Port Authority Board", "Hospital Trust",
        "Transit Commission", "Housing Authority", "Commerce Chamber Board",
    ],
    InstitutionType.CIVIC_ASSOCIATION: [
        "Neighborhood Watch Alliance", "Citizens Advisory Panel",
        "Green Spaces Trust", "Youth Development Council",
        "Immigrant Integration Forum", "Disability Rights Coalition",
    ],
    InstitutionType.CULTURAL_CLUB: [
        "Arts Patronage Circle", "Literary Society", "Music Conservatory Friends",
        "Heritage Preservation Guild", "Film Society",
    ],
    InstitutionType.SOCIAL_CLUB: [
        "Metropolitan Club", "University Club", "Rotary Chapter",
        "Lions Club", "Professional Women's Network",
    ],
    InstitutionType.POLITICAL_ORG: [
        "Progressive Alliance", "Civic Democrats", "Labor Forum",
        "Conservative Circle", "Green Collective",
    ],
    InstitutionType.RELIGIOUS_COMMUNITY: [
        "St. Martin's Parish Council", "Islamic Cultural Center",
        "Jewish Community Board", "Interfaith Council",
    ],
    InstitutionType.INDUSTRY_BODY: [
        "Tech Industry Association", "Building Trades Council",
        "Healthcare Professionals Guild", "Finance Roundtable",
        "Hospitality Alliance",
    ],
    InstitutionType.ALUMNI_NETWORK: [
        "University Alumni Association", "Polytechnic Graduates Network",
        "Business School Circle", "Law School Alumni",
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# PER-AGENT INSTITUTIONAL PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Membership:
    """An agent's membership in a specific institution."""
    institution_type: InstitutionType
    institution_name: str
    years_active: int = 0
    leadership_role: bool = False   # board chair, committee head, etc.
    economic_interest: float = 0.0  # 0-1, how much this creates financial alignment

    def to_dict(self) -> dict:
        return {
            "type": self.institution_type.value,
            "name": self.institution_name,
            "years_active": self.years_active,
            "leadership": self.leadership_role,
            "economic_interest": round(self.economic_interest, 3),
        }


@dataclass
class InstitutionalProfile:
    """Per-agent institutional engagement."""
    memberships: list[Membership] = field(default_factory=list)
    skill_currency: float = 0.70      # 0-1, how up-to-date skills are
    lifelong_learning: float = 0.40   # 0-1, propensity to retrain/upskill
    civic_participation: float = 0.30 # 0-1, general civic engagement
    board_power: float = 0.0         # 0-1, derived from board positions
    total_time_commitment: float = 0.0  # sum of membership time

    def to_dict(self) -> dict:
        return {
            "memberships": [m.to_dict() for m in self.memberships],
            "membership_count": len(self.memberships),
            "skill_currency": round(self.skill_currency, 3),
            "lifelong_learning": round(self.lifelong_learning, 3),
            "civic_participation": round(self.civic_participation, 3),
            "board_power": round(self.board_power, 3),
            "total_time_commitment": round(self.total_time_commitment, 3),
        }


# ══════════════════════════════════════════════════════════════════════════════
# GENERATION
# ══════════════════════════════════════════════════════════════════════════════

# Occupation → institution affinity mapping
OCCUPATION_INSTITUTION_AFFINITY: dict[str, list[InstitutionType]] = {
    "mayor":              [InstitutionType.PROFESSIONAL_BOARD, InstitutionType.CIVIC_ASSOCIATION, InstitutionType.POLITICAL_ORG],
    "council_member":     [InstitutionType.POLITICAL_ORG, InstitutionType.CIVIC_ASSOCIATION],
    "business_owner":     [InstitutionType.PROFESSIONAL_BOARD, InstitutionType.SOCIAL_CLUB, InstitutionType.INDUSTRY_BODY],
    "developer":          [InstitutionType.INDUSTRY_BODY, InstitutionType.ALUMNI_NETWORK],
    "lawyer":             [InstitutionType.PROFESSIONAL_BOARD, InstitutionType.SOCIAL_CLUB, InstitutionType.INDUSTRY_BODY],
    "doctor":             [InstitutionType.PROFESSIONAL_BOARD, InstitutionType.INDUSTRY_BODY, InstitutionType.CIVIC_ASSOCIATION],
    "journalist":         [InstitutionType.CIVIC_ASSOCIATION, InstitutionType.CULTURAL_CLUB],
    "professor":          [InstitutionType.CULTURAL_CLUB, InstitutionType.ALUMNI_NETWORK, InstitutionType.CIVIC_ASSOCIATION],
    "banker":             [InstitutionType.PROFESSIONAL_BOARD, InstitutionType.SOCIAL_CLUB, InstitutionType.INDUSTRY_BODY],
    "police_chief":       [InstitutionType.CIVIC_ASSOCIATION, InstitutionType.PROFESSIONAL_BOARD],
    "union_leader":       [InstitutionType.INDUSTRY_BODY, InstitutionType.POLITICAL_ORG, InstitutionType.CIVIC_ASSOCIATION],
    "pastor":             [InstitutionType.RELIGIOUS_COMMUNITY, InstitutionType.CIVIC_ASSOCIATION],
    "nonprofit_director": [InstitutionType.CIVIC_ASSOCIATION, InstitutionType.PROFESSIONAL_BOARD],
    "lobbyist":           [InstitutionType.POLITICAL_ORG, InstitutionType.SOCIAL_CLUB, InstitutionType.INDUSTRY_BODY],
    "engineer":           [InstitutionType.INDUSTRY_BODY, InstitutionType.ALUMNI_NETWORK],
    "restaurateur":       [InstitutionType.INDUSTRY_BODY, InstitutionType.SOCIAL_CLUB],
    "artist":             [InstitutionType.CULTURAL_CLUB, InstitutionType.CIVIC_ASSOCIATION],
    "contractor":         [InstitutionType.INDUSTRY_BODY, InstitutionType.SOCIAL_CLUB],
    "realtor":            [InstitutionType.INDUSTRY_BODY, InstitutionType.SOCIAL_CLUB, InstitutionType.PROFESSIONAL_BOARD],
    "consultant":         [InstitutionType.PROFESSIONAL_BOARD, InstitutionType.SOCIAL_CLUB, InstitutionType.ALUMNI_NETWORK],
}


def generate_institutional_profile(
    occupation: str,
    education_track_value: str,
    class_rank: int,
    age: int,
    economic_capital: float,
    cultural_capital: float,
    social_capital: float,
    politics_numeric: float,
    interests: list[str],
    rng: random.Random | None = None,
) -> InstitutionalProfile:
    """Generate institutional memberships based on agent profile."""
    r = rng or random
    profile = InstitutionalProfile()

    # ── Skill currency: starts high for young, decays with age ─────
    if age < 30:
        profile.skill_currency = 0.85 + r.gauss(0, 0.05)
    elif age < 45:
        profile.skill_currency = 0.75 + r.gauss(0, 0.06)
    elif age < 60:
        profile.skill_currency = 0.60 + r.gauss(0, 0.08)
    else:
        profile.skill_currency = 0.45 + r.gauss(0, 0.10)
    # Education helps maintain currency
    edu_boost = {"vocational": 0.0, "applied": 0.05, "academic": 0.10, "elite": 0.15}.get(
        education_track_value, 0.0
    )
    profile.skill_currency += edu_boost
    profile.skill_currency = max(0.1, min(1.0, profile.skill_currency))

    # ── Lifelong learning propensity ───────────────────────────────
    edu_learn = {"vocational": 0.20, "applied": 0.35, "academic": 0.55, "elite": 0.70}.get(
        education_track_value, 0.30
    )
    # Younger agents more likely to retrain
    age_factor = max(0.1, 1.0 - (age - 25) / 60)
    profile.lifelong_learning = edu_learn * 0.5 + age_factor * 0.3 + class_rank * 0.03 + r.gauss(0, 0.06)
    profile.lifelong_learning = max(0.05, min(1.0, profile.lifelong_learning))

    # ── Determine number of memberships ────────────────────────────
    # Higher class + social capital + age → more memberships
    membership_propensity = (
        class_rank * 0.12 +
        social_capital * 0.20 +
        economic_capital * 0.10 +
        min(0.15, (age - 25) / 100) +
        r.gauss(0, 0.08)
    )
    # Education phase agents rarely join boards
    if age < 25:
        membership_propensity *= 0.3

    # Expected count: 0-4 memberships
    expected = max(0, membership_propensity * 4)
    n_memberships = min(4, int(expected) + (1 if r.random() < (expected % 1) else 0))

    # ── Select institution types ───────────────────────────────────
    # Occupation affinity
    affinity_types = OCCUPATION_INSTITUTION_AFFINITY.get(occupation, [])

    # Additional types from interests
    interest_types = []
    if "arts" in interests or "education" in interests:
        interest_types.append(InstitutionType.CULTURAL_CLUB)
    if "religion" in interests:
        interest_types.append(InstitutionType.RELIGIOUS_COMMUNITY)
    if "unions" in interests:
        interest_types.append(InstitutionType.INDUSTRY_BODY)
    if "governance" in interests:
        interest_types.append(InstitutionType.CIVIC_ASSOCIATION)
    if abs(politics_numeric) >= 2:
        interest_types.append(InstitutionType.POLITICAL_ORG)

    # Merge and weight candidates
    candidate_pool = list(set(affinity_types + interest_types))
    if not candidate_pool:
        candidate_pool = [InstitutionType.CIVIC_ASSOCIATION, InstitutionType.INDUSTRY_BODY]

    # Add random discovery
    all_types = list(InstitutionType)
    if r.random() < 0.2:
        candidate_pool.append(r.choice(all_types))

    chosen_types: list[InstitutionType] = []
    used_names: set[str] = set()

    for _ in range(n_memberships):
        if not candidate_pool:
            break

        inst_type = r.choice(candidate_pool)
        prof = INSTITUTION_PROFILES[inst_type]

        # Soft access check
        access_score = 0.0
        if class_rank >= prof.min_class_rank:
            access_score += 0.3
        if economic_capital >= prof.min_economic:
            access_score += 0.2
        if cultural_capital >= prof.min_cultural:
            access_score += 0.2
        if education_track_value in prof.education_affinity:
            access_score += 0.3

        # Roll against access
        if r.random() > access_score + 0.2:
            continue

        # Pick a specific named institution
        names = INSTITUTION_NAMES.get(inst_type, ["General " + prof.name])
        available = [n for n in names if n not in used_names]
        if not available:
            continue
        name = r.choice(available)
        used_names.add(name)

        # Years active: scales with age
        max_years = max(1, age - 25)
        years = r.randint(0, min(max_years, 15))

        # Leadership: more likely with seniority and influence
        leadership = (
            years > 5 and
            class_rank >= 2 and
            r.random() < 0.15 + economic_capital * 0.15 + social_capital * 0.10
        )

        # Economic interest from board positions
        econ_interest = 0.0
        if inst_type in (InstitutionType.PROFESSIONAL_BOARD, InstitutionType.INDUSTRY_BODY):
            econ_interest = prof.economic_benefit * 0.5 + (0.2 if leadership else 0)
            econ_interest += r.gauss(0, 0.05)
        elif inst_type == InstitutionType.SOCIAL_CLUB:
            econ_interest = prof.economic_benefit * 0.3
        econ_interest = max(0, min(1.0, econ_interest))

        profile.memberships.append(Membership(
            institution_type=inst_type,
            institution_name=name,
            years_active=years,
            leadership_role=leadership,
            economic_interest=econ_interest,
        ))

        chosen_types.append(inst_type)
        # Don't join two of the same type usually
        candidate_pool = [t for t in candidate_pool if t != inst_type]

    # ── Civic participation: driven by memberships ─────────────────
    civic = len(profile.memberships) * 0.12
    civic += sum(1 for m in profile.memberships
                 if m.institution_type in (InstitutionType.CIVIC_ASSOCIATION,
                                           InstitutionType.POLITICAL_ORG,
                                           InstitutionType.RELIGIOUS_COMMUNITY)) * 0.10
    profile.civic_participation = max(0, min(1.0, civic + r.gauss(0, 0.05)))

    # ── Compute derived fields ─────────────────────────────────────
    _recompute_derived(profile)

    return profile


def _recompute_derived(profile: InstitutionalProfile):
    """Recompute board_power and total_time_commitment."""
    profile.total_time_commitment = 0.0
    profile.board_power = 0.0

    for m in profile.memberships:
        prof = INSTITUTION_PROFILES[m.institution_type]
        profile.total_time_commitment += prof.time_commitment

        if m.institution_type == InstitutionType.PROFESSIONAL_BOARD:
            power = 0.3 + (0.3 if m.leadership_role else 0) + min(0.2, m.years_active * 0.02)
            profile.board_power += power

    profile.board_power = min(1.0, profile.board_power)
    profile.total_time_commitment = min(0.8, profile.total_time_commitment)


# ══════════════════════════════════════════════════════════════════════════════
# INSTITUTIONAL EVOLUTION (per tick)
# ══════════════════════════════════════════════════════════════════════════════

def evolve_institutional_profile(
    profile: InstitutionalProfile,
    age: int,
    class_rank: int,
    education_track_value: str,
    rng: random.Random,
):
    """Advance institutional memberships by one year."""

    # ── Skill currency decay ───────────────────────────────────────
    # Skills decay ~3% per year without refreshing
    decay = 0.03
    # Lifelong learning offsets decay
    learning_offset = profile.lifelong_learning * 0.025
    # Membership in educational institutions helps
    edu_memberships = sum(1 for m in profile.memberships
                         if m.institution_type in (InstitutionType.ALUMNI_NETWORK,
                                                    InstitutionType.INDUSTRY_BODY))
    membership_offset = edu_memberships * 0.008

    profile.skill_currency += learning_offset + membership_offset - decay
    profile.skill_currency += rng.gauss(0, 0.01)
    profile.skill_currency = max(0.1, min(1.0, profile.skill_currency))

    # ── Advance membership years ───────────────────────────────────
    for m in profile.memberships:
        m.years_active += 1
        # Chance of gaining leadership with seniority
        if not m.leadership_role and m.years_active > 5 and rng.random() < 0.05:
            m.leadership_role = True
            m.economic_interest = min(1.0, m.economic_interest + 0.10)

    # ── Membership churn: small chance of joining/leaving ──────────
    # Leave: burnout, life changes (2% chance per membership per year)
    profile.memberships = [
        m for m in profile.memberships
        if rng.random() > 0.02
    ]

    # Join: 5% chance of new membership per year (if under 4)
    if len(profile.memberships) < 4 and rng.random() < 0.05:
        all_types = list(InstitutionType)
        new_type = rng.choice(all_types)
        names = INSTITUTION_NAMES.get(new_type, ["General"])
        existing_names = {m.institution_name for m in profile.memberships}
        available = [n for n in names if n not in existing_names]
        if available:
            profile.memberships.append(Membership(
                institution_type=new_type,
                institution_name=rng.choice(available),
                years_active=0,
                leadership_role=False,
                economic_interest=0.0,
            ))

    # ── Recompute derived ──────────────────────────────────────────
    _recompute_derived(profile)


# ══════════════════════════════════════════════════════════════════════════════
# INSTITUTIONS → CAPITAL & ECONOMY COUPLING
# ══════════════════════════════════════════════════════════════════════════════

def institutions_affect_capital(profile: InstitutionalProfile, capital):
    """Institutional memberships generate capital gains."""
    for m in profile.memberships:
        prof = INSTITUTION_PROFILES[m.institution_type]
        seniority_mult = min(2.0, 1.0 + m.years_active * 0.05)
        leader_mult = 1.5 if m.leadership_role else 1.0

        # Economic benefit (board fees, business opportunities)
        capital.economic += prof.economic_benefit * 0.008 * seniority_mult * leader_mult
        # Social benefit (network expansion)
        capital.social += prof.social_benefit * 0.005 * seniority_mult
        # Symbolic benefit (prestige, recognition)
        capital.symbolic += prof.prestige * 0.006 * seniority_mult * leader_mult
        # Cultural benefit
        capital.cultural += prof.cultural_benefit * 0.004

    # Skill currency affects economic capital
    if profile.skill_currency < 0.4:
        capital.economic -= (0.4 - profile.skill_currency) * 0.01

    capital.clamp()


def institutions_affect_economy(profile: InstitutionalProfile, agent_economy):
    """Institutional engagement affects economic performance."""
    if agent_economy is None:
        return

    # Skill currency directly affects productivity
    agent_economy.productivity *= (0.7 + profile.skill_currency * 0.3)

    # Board economic interests boost income
    total_econ_interest = sum(m.economic_interest for m in profile.memberships)
    agent_economy.income += total_econ_interest * 0.03
    agent_economy.income = max(0.05, min(1.0, agent_economy.income))

    # Time commitment reduces available work time slightly
    if profile.total_time_commitment > 0.3:
        agent_economy.productivity *= (1 - (profile.total_time_commitment - 0.3) * 0.15)

    # Lifelong learning helps tech adaptation
    agent_economy.tech_adaptation += profile.lifelong_learning * 0.02
    agent_economy.tech_adaptation = min(1.0, agent_economy.tech_adaptation)


# ══════════════════════════════════════════════════════════════════════════════
# INSTITUTIONS → NETWORK TIES
# ══════════════════════════════════════════════════════════════════════════════

def create_institutional_ties(G, agents: list, rng: random.Random) -> int:
    """Create graph edges from shared institutional memberships.

    Interlocking directorates (Mizruchi 1996): agents who share board
    memberships form strong ties with aligned economic interests.

    Returns number of edges added.
    """
    import networkx as nx

    # Build membership index: institution_name → list of agent_ids
    inst_members: dict[str, list[str]] = {}
    for agent in agents:
        if not agent.institutions:
            continue
        for m in agent.institutions.memberships:
            inst_members.setdefault(m.institution_name, []).append(agent.id)

    edges_added = 0
    for inst_name, member_ids in inst_members.items():
        if len(member_ids) < 2:
            continue

        # Small groups (boards, clubs <= 8): fully connect
        # Medium groups (9-20): each connects to 2-3 co-members
        # Large groups (20+): each connects to 1-2 co-members
        if len(member_ids) <= 8:
            pairs = [(member_ids[i], member_ids[j])
                     for i in range(len(member_ids))
                     for j in range(i + 1, len(member_ids))]
        else:
            n_ties = 3 if len(member_ids) <= 20 else 2
            pairs = []
            seen = set()
            for aid in member_ids:
                targets = rng.sample([x for x in member_ids if x != aid],
                                     min(n_ties, len(member_ids) - 1))
                for bid in targets:
                    key = (min(aid, bid), max(aid, bid))
                    if key not in seen:
                        seen.add(key)
                        pairs.append((aid, bid))

        for aid, bid in pairs:
            if aid == bid:
                continue
            if G.has_edge(aid, bid):
                old_w = G.edges[aid, bid].get("weight", 0.3)
                G.edges[aid, bid]["weight"] = min(1.0, old_w + 0.1)
            else:
                w = 0.35 + rng.random() * 0.25
                G.add_edge(aid, bid, weight=round(w, 3), rel="institutional")
                edges_added += 1

    return edges_added


# ══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT INDICATORS
# ══════════════════════════════════════════════════════════════════════════════

INSTITUTION_BASELINES = {
    "education_quality": 0.68,          # 0-1
    "vocational_training_access": 0.55, # 0-1
    "civic_participation_index": 0.45,  # 0-1
    "associational_density": 0.50,      # 0-1 (Putnam's metric)
}

INSTITUTION_INDICATOR_META = {
    "education_quality":         ("Education Quality",    0.0, 1.0, "norm", True),
    "vocational_training_access":("Vocational Training",  0.0, 1.0, "norm", True),
    "civic_participation_index": ("Civic Participation",  0.0, 1.0, "norm", True),
    "associational_density":     ("Assoc. Density",       0.0, 1.0, "norm", True),
}


def evolve_institution_indicators(indicators: dict, rng: random.Random):
    """Evolve city-level institution indicators by one year."""
    ind = indicators

    # Education quality: tracks public spending, democratic quality
    pub_spend = ind.get("public_spending", 0.48)
    dem_qual = ind.get("democratic_quality", 0.78)
    ind["education_quality"] += (pub_spend - 0.45) * 0.02 + (dem_qual - 0.7) * 0.01
    ind["education_quality"] += rng.gauss(0, 0.005)

    # Vocational training: tracks unemployment (demand-driven) and public spending
    unemp = ind.get("unemployment", 0.065)
    ind["vocational_training_access"] += (unemp - 0.06) * 0.05 + (pub_spend - 0.45) * 0.01
    ind["vocational_training_access"] += rng.gauss(0, 0.005)

    # Civic participation: tracks social cohesion, democratic quality, media pluralism
    cohesion = ind.get("social_cohesion", 0.62)
    media_plur = ind.get("media_pluralism", 0.65)
    ind["civic_participation_index"] += (cohesion - 0.5) * 0.02 + (media_plur - 0.5) * 0.01
    ind["civic_participation_index"] += rng.gauss(0, 0.005)

    # Associational density: slow-moving, tracks civic participation
    civic = ind.get("civic_participation_index", 0.45)
    ind["associational_density"] += (civic - 0.4) * 0.01 + rng.gauss(0, 0.003)

    # Clamp
    for k in INSTITUTION_BASELINES:
        if k in ind:
            ind[k] = max(0.0, min(1.0, ind[k]))


def compute_institution_stats(profiles: list[InstitutionalProfile]) -> dict:
    """Aggregate institutional statistics."""
    n = len(profiles) or 1
    total_memberships = sum(len(p.memberships) for p in profiles)
    avg_memberships = total_memberships / n
    board_members = sum(1 for p in profiles
                       if any(m.institution_type == InstitutionType.PROFESSIONAL_BOARD
                              for m in p.memberships)) / n
    leaders = sum(1 for p in profiles
                  if any(m.leadership_role for m in p.memberships)) / n
    avg_skill = sum(p.skill_currency for p in profiles) / n
    avg_learning = sum(p.lifelong_learning for p in profiles) / n
    avg_civic = sum(p.civic_participation for p in profiles) / n
    avg_board_power = sum(p.board_power for p in profiles) / n

    # Type distribution
    type_counts: dict[str, int] = {}
    for p in profiles:
        for m in p.memberships:
            type_counts[m.institution_type.value] = type_counts.get(m.institution_type.value, 0) + 1

    return {
        "avg_memberships": round(avg_memberships, 2),
        "total_memberships": total_memberships,
        "board_member_fraction": round(board_members, 3),
        "leadership_fraction": round(leaders, 3),
        "avg_skill_currency": round(avg_skill, 3),
        "avg_lifelong_learning": round(avg_learning, 3),
        "avg_civic_participation": round(avg_civic, 3),
        "avg_board_power": round(avg_board_power, 3),
        "type_distribution": type_counts,
    }
