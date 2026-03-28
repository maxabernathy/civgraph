"""
CivGraph -- STS-inspired agency dynamics.

Operationalizes concepts from Science and Technology Studies (STS) and
social network agency theory into computable simulation dynamics.

Core concepts implemented:

  1. **Translation** (Callon 1986, Latour 1987)
     Four moments of translation: problematization (defining the problem),
     interessement (locking actors into roles), enrolment (actors accept),
     mobilization (enrolled actors represent others). In CivGraph, events
     undergo translation as they propagate — topic framing, sentiment,
     and intensity shift based on the translating agent's institutional
     position, capital profile, and interests.

  2. **Non-human actants** (Latour 1991, 2005)
     Technologies, media platforms, and institutions are not passive
     background but active agents. Each has an agency score — its capacity
     to shape network dynamics independently of human intention. AI is an
     actant that restructures task portfolios; social media is an actant
     that creates echo chambers; a professional board is an actant that
     concentrates power.

  3. **Obligatory passage points** (Callon 1986)
     Nodes that become unavoidable intermediaries — not just high
     betweenness centrality (Burt 1992) but incorporating institutional
     gatekeeping power, information asymmetry, and legitimacy.

  4. **Performativity** (Callon 1998, MacKenzie 2006)
     Economic and social categories don't just describe reality — they
     actively shape it. Class awareness → class-consistent behavior →
     reinforced stratification. Media categories → opinion alignment →
     polarization. The model measures how much agent behavior conforms
     to its own category predictions (self-fulfilling prophecy index).

  5. **Black-boxing** (Latour 1987)
     When complex arrangements stabilize and become invisible/taken-for-
     granted. Crystallized norms, established institutions, and mature
     technologies become black-boxed. Black-boxed elements resist change
     but can be "opened" by crises, scandals, or disruptions.

  6. **Centers of calculation** (Latour 1987)
     Institutions that accumulate, process, and redistribute information
     and power. They achieve power by being able to "see" across the
     network — aggregating data from multiple positions.

  7. **Heterogeneous engineering** (Law 1987, 2004)
     Network stability comes from successfully aligning heterogeneous
     elements: people, technologies, institutions, norms, capital.
     Fragility comes from misalignment across these dimensions.

  8. **Structural holes** (Burt 1992)
     Formalized from the existing bridge-agent detection. Agents who
     span structural holes control information flow and gain advantages
     from brokerage.

  9. **Network programmers and switchers** (Castells 2009)
     Programmers: agents who can reshape network rules (high institutional
     power + high symbolic capital). Switchers: agents who connect
     otherwise separate networks (high bridging + multiple institutional
     memberships across types).

References:
  - Callon (1986): Some elements of a sociology of translation
  - Latour (1987): Science in Action
  - Latour (2005): Reassembling the Social
  - Law (1987): Technology and heterogeneous engineering
  - Law (2004): After Method
  - Burt (1992): Structural Holes
  - Castells (2009): Communication Power
  - MacKenzie (2006): An Engine, Not a Camera
  - Callon (1998): Laws of the Markets
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import networkx as nx


# ══════════════════════════════════════════════════════════════════════════════
# 1. NON-HUMAN ACTANTS (Latour)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Actant:
    """A non-human entity with agency in the network."""
    name: str
    domain: str           # "technology", "media", "institution"
    agency: float         # 0-1, capacity to shape network dynamics
    reach: float          # 0-1, fraction of population affected
    stability: float      # 0-1, how black-boxed / taken-for-granted
    inscription: float    # 0-1, how much behavior it has encoded/scripted


def compute_nonhuman_actants(tech_waves: dict, media_landscape, institutions_stats: dict) -> list[Actant]:
    """Compute agency scores for non-human actants in the network.

    Latour (2005): agency is not a property of humans alone — it is
    distributed across heterogeneous assemblages of humans, technologies,
    institutions, and texts.
    """
    actants = []

    # Technology actants
    if tech_waves:
        for name, wave in tech_waves.items():
            adoption = wave.get("adoption", 0) if isinstance(wave, dict) else getattr(wave, "adoption", 0)
            # Agency = adoption × disruption capacity
            agency = adoption * 0.8
            # Higher adoption = more black-boxed
            stability = min(1.0, adoption * 1.1)
            # Inscription: how much behavior is encoded in the technology
            inscription = adoption * 0.7
            actants.append(Actant(
                name=name, domain="technology",
                agency=round(agency, 3), reach=round(adoption, 3),
                stability=round(stability, 3), inscription=round(inscription, 3),
            ))

    # Media actants
    if media_landscape:
        ml = media_landscape if isinstance(media_landscape, dict) else media_landscape.to_dict()
        for media_type, reach_key, trust_key in [
            ("print_media", "print_reach", "print_trust"),
            ("mass_media", "mass_reach", "mass_trust"),
            ("social_media", "social_reach", "social_trust"),
        ]:
            reach = ml.get(reach_key, 0.5)
            trust = ml.get(trust_key, 0.5)
            # Social media has high agency despite low trust (algorithmic power)
            if media_type == "social_media":
                agency = reach * 0.6 + ml.get("social_echo_chamber", 0.5) * 0.3 + ml.get("social_virality", 0.5) * 0.1
                inscription = ml.get("social_echo_chamber", 0.5) * 0.8
            else:
                agency = reach * trust * 0.7
                inscription = trust * 0.4
            stability = min(1.0, reach * 0.8 + 0.2)
            actants.append(Actant(
                name=media_type, domain="media",
                agency=round(agency, 3), reach=round(reach, 3),
                stability=round(stability, 3), inscription=round(inscription, 3),
            ))

    return actants


# ══════════════════════════════════════════════════════════════════════════════
# 2. TRANSLATION DYNAMICS (Callon 1986)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TranslationState:
    """Tracks how an event is translated as it propagates.

    Callon's four moments:
    - Problematization: the originator defines the problem
    - Interessement: intermediary agents lock others into roles
    - Enrolment: agents accept and commit
    - Mobilization: enrolled agents speak for others
    """
    original_topic: str
    original_sentiment: float
    # How much the event has been translated (reframed)
    topic_drift: float = 0.0         # how far framing has moved from original
    sentiment_drift: float = 0.0     # how sentiment has shifted
    interessement_score: float = 0.0 # how many intermediaries reshaped it
    enrolment_rate: float = 0.0      # fraction of reached agents who committed
    mobilization_rate: float = 0.0   # fraction of enrolled who spread further
    translation_chain_length: int = 0


def compute_translation(
    agent_interests: list[str],
    agent_occupation: str,
    agent_institutional_memberships: list[str],
    event_topic: str,
    event_sentiment: float,
    agent_politics_numeric: float,
    event_political_bias: float,
) -> dict:
    """Compute how an agent translates an event as it passes through them.

    Translation (Callon): actors don't passively relay information — they
    reframe it to align with their own interests, institutional position,
    and dispositional orientation.

    Returns: dict with translated_sentiment, framing_shift, interessement_strength
    """
    # Topic alignment: agents with related interests keep the framing closer
    topic_match = 1.0 if event_topic in agent_interests else 0.3

    # Institutional framing: agents in institutions related to the topic
    # add institutional weight to the translation
    inst_match = 0.0
    topic_inst_map = {
        "governance": ["political_org", "civic_association"],
        "finance": ["professional_board", "industry_body"],
        "arts": ["cultural_club"],
        "education": ["alumni_network", "civic_association"],
        "tech": ["industry_body", "alumni_network"],
        "real_estate": ["professional_board"],
        "healthcare": ["professional_board", "industry_body"],
        "religion": ["religious_community"],
        "unions": ["industry_body", "political_org"],
    }
    relevant_types = topic_inst_map.get(event_topic, [])
    for mem_type in agent_institutional_memberships:
        if mem_type in relevant_types:
            inst_match += 0.25
    inst_match = min(1.0, inst_match)

    # Sentiment translation: agents shift sentiment toward their political position
    political_distance = abs(agent_politics_numeric - event_political_bias) / 6
    sentiment_shift = (agent_politics_numeric - event_political_bias) / 6 * 0.15
    translated_sentiment = event_sentiment + sentiment_shift
    translated_sentiment = max(-1, min(1, translated_sentiment))

    # Interessement strength: how much this agent reshapes the event
    interessement = (1 - topic_match) * 0.4 + political_distance * 0.3 + inst_match * 0.3

    # Framing shift: how much the topic framing changes
    framing_shift = (1 - topic_match) * 0.3 + inst_match * 0.2

    return {
        "translated_sentiment": translated_sentiment,
        "sentiment_drift": abs(sentiment_shift),
        "framing_shift": framing_shift,
        "interessement_strength": round(interessement, 3),
        "topic_match": topic_match,
        "institutional_framing": inst_match,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. OBLIGATORY PASSAGE POINTS (Callon 1986)
# ══════════════════════════════════════════════════════════════════════════════

def compute_passage_points(G: nx.Graph, top_n: int = 20, bc_cache: dict | None = None) -> list[dict]:
    """Identify obligatory passage points in the network.

    An OPP (Callon 1986) is a node that other actors must pass through
    to achieve their goals. In network terms: high betweenness centrality
    × institutional gatekeeping power × information asymmetry.

    Goes beyond Burt's (1992) structural holes by incorporating
    institutional legitimacy and non-network power.
    """
    if G.number_of_nodes() < 5:
        return []

    # Betweenness centrality (Burt's structural holes foundation)
    bc = bc_cache or nx.betweenness_centrality(G, weight="weight", k=min(200, G.number_of_nodes()))

    opp_scores = []
    for nid in G.nodes:
        agent = G.nodes[nid]["agent"]
        betweenness = bc.get(nid, 0)

        # Institutional gatekeeping: board power + leadership positions
        inst_power = 0.0
        if agent.institutions:
            inst_power = agent.institutions.board_power * 0.5
            # Leadership multiplier
            for m in agent.institutions.memberships:
                if m.leadership_role:
                    inst_power += 0.15
            inst_power = min(1.0, inst_power)

        # Information asymmetry: degree diversity (connections to different clans/districts)
        neighbor_clans = set()
        neighbor_districts = set()
        for nb in G.neighbors(nid):
            na = G.nodes[nb]["agent"]
            neighbor_clans.add(na.clan)
            neighbor_districts.add(na.district)
        clan_diversity = len(neighbor_clans) / 20  # normalized by total clans
        district_diversity = len(neighbor_districts) / 10

        # Symbolic capital as legitimacy
        legitimacy = agent.capital.symbolic * 0.3 + agent.capital.social * 0.2

        # OPP score: weighted composite
        opp = (
            betweenness * 0.35 +
            inst_power * 0.25 +
            clan_diversity * 0.15 +
            district_diversity * 0.10 +
            legitimacy * 0.15
        )

        opp_scores.append({
            "agent_id": nid,
            "agent_name": agent.name,
            "opp_score": round(opp, 4),
            "betweenness": round(betweenness, 4),
            "institutional_power": round(inst_power, 3),
            "clan_diversity": round(clan_diversity, 3),
            "legitimacy": round(legitimacy, 3),
        })

    opp_scores.sort(key=lambda x: x["opp_score"], reverse=True)
    return opp_scores[:top_n]


# ══════════════════════════════════════════════════════════════════════════════
# 4. PERFORMATIVITY (Callon 1998, MacKenzie 2006)
# ══════════════════════════════════════════════════════════════════════════════

def compute_performativity(G: nx.Graph) -> dict:
    """Measure how much social categories become self-fulfilling.

    Callon (1998): economic models don't just describe markets — they
    perform them. Categories (class, politics) shape behavior, which
    reinforces the categories.

    MacKenzie (2006): financial models are "engines, not cameras."

    We measure: how much agent behavior conforms to category predictions.
    High performativity = categories are strongly self-reinforcing.
    """
    agents = [G.nodes[n]["agent"] for n in G.nodes]
    n = len(agents) or 1

    # ── Class performativity ───────────────────────────────────────
    # Do agents behave according to their class label?
    # Measure: correlation between class rank and actual behavior
    class_econ_alignment = 0.0
    class_cultural_alignment = 0.0
    class_social_alignment = 0.0

    for a in agents:
        rank = a.habitus.current_class.rank / 4  # 0-1
        # Economic capital should track class
        class_econ_alignment += 1 - abs(rank - a.capital.economic)
        # Cultural taste should track class
        taste_norm = (a.habitus.cultural_taste + 1) / 2  # -1..1 → 0..1
        class_cultural_alignment += 1 - abs(rank - taste_norm)
        # Social connections should track class (homophily)
        neighbor_ranks = []
        for nb in G.neighbors(a.id):
            na = G.nodes[nb]["agent"]
            neighbor_ranks.append(na.habitus.current_class.rank / 4)
        if neighbor_ranks:
            avg_nb_rank = sum(neighbor_ranks) / len(neighbor_ranks)
            class_social_alignment += 1 - abs(rank - avg_nb_rank)

    class_performativity = (
        class_econ_alignment / n * 0.4 +
        class_cultural_alignment / n * 0.3 +
        class_social_alignment / n * 0.3
    )

    # ── Political performativity ───────────────────────────────────
    # Do agents' opinions align with their political labels?
    pol_alignment = 0.0
    pol_count = 0
    for a in agents:
        pol_pos = a.politics.numeric / 3  # -1..1
        for topic, opinion in a.opinion_state.items():
            # Left agents should support left-coded topics, etc.
            if opinion != 0:
                pol_alignment += 1 - abs(pol_pos - opinion) / 2
                pol_count += 1
    political_performativity = pol_alignment / max(1, pol_count)

    # ── Media performativity ───────────────────────────────────────
    # Does media consumption predict opinion patterns?
    media_alignment = 0.0
    media_count = 0
    for a in agents:
        if not a.media or not a.opinion_state:
            continue
        # High social media → more extreme opinions (echo chamber prediction)
        avg_extremity = sum(abs(v) for v in a.opinion_state.values()) / max(1, len(a.opinion_state))
        social_prediction = a.media.social_exposure * 0.7
        media_alignment += 1 - abs(social_prediction - avg_extremity)
        media_count += 1
    media_performativity = media_alignment / max(1, media_count)

    # ── Overall performativity index ───────────────────────────────
    composite = (
        class_performativity * 0.40 +
        political_performativity * 0.35 +
        media_performativity * 0.25
    )

    return {
        "class_performativity": round(class_performativity, 3),
        "political_performativity": round(political_performativity, 3),
        "media_performativity": round(media_performativity, 3),
        "composite": round(composite, 3),
        "interpretation": (
            "high" if composite > 0.7 else
            "moderate" if composite > 0.4 else "low"
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. BLACK-BOXING (Latour 1987)
# ══════════════════════════════════════════════════════════════════════════════

def compute_black_boxing(G: nx.Graph, tech_waves: dict | None = None) -> dict:
    """Measure the degree of black-boxing across network elements.

    Latour (1987): a black box is a complex assemblage that has become
    so stable that its internal workings are invisible. Opening a black
    box requires controversy, crisis, or breakdown.

    We measure: norm crystallization, institutional stability, and
    technology maturity as indicators of black-boxing.
    """
    agents = [G.nodes[n]["agent"] for n in G.nodes]
    n = len(agents) or 1

    # ── Norm black-boxing ──────────────────────────────────────────
    # Crystallized norms are black-boxed: widely shared + stable
    all_norms: dict[str, list[float]] = {}
    for a in agents:
        for topic, val in a.norms.items():
            all_norms.setdefault(topic, []).append(val)

    norm_stability = 0.0
    norm_count = 0
    for topic, values in all_norms.items():
        if len(values) > n * 0.3:  # widespread
            variance = sum((v - sum(values) / len(values)) ** 2 for v in values) / len(values)
            stability = 1 - min(1, variance * 4)  # low variance = high stability = black-boxed
            norm_stability += stability
            norm_count += 1
    norm_black_box = norm_stability / max(1, norm_count) if norm_count > 0 else 0.0

    # ── Institutional black-boxing ─────────────────────────────────
    # Long-established institutions with stable membership
    inst_ages = []
    for a in agents:
        if a.institutions:
            for m in a.institutions.memberships:
                inst_ages.append(m.years_active)
    avg_inst_age = sum(inst_ages) / max(1, len(inst_ages))
    # Older institutions = more black-boxed
    inst_black_box = min(1.0, avg_inst_age / 15)

    # ── Technology black-boxing ────────────────────────────────────
    # Mature technologies are invisible infrastructure
    tech_black_box = 0.0
    tech_count = 0
    if tech_waves:
        for name, wave in tech_waves.items():
            adoption = wave.get("adoption", 0) if isinstance(wave, dict) else getattr(wave, "adoption", 0)
            # Technologies above 80% adoption are essentially black-boxed
            if adoption > 0.5:
                tech_black_box += min(1.0, (adoption - 0.5) * 2)
                tech_count += 1
    tech_black_box = tech_black_box / max(1, tech_count) if tech_count > 0 else 0.0

    # ── Composite ──────────────────────────────────────────────────
    composite = (
        norm_black_box * 0.35 +
        inst_black_box * 0.30 +
        tech_black_box * 0.35
    )

    return {
        "norm_black_boxing": round(norm_black_box, 3),
        "institutional_black_boxing": round(inst_black_box, 3),
        "technology_black_boxing": round(tech_black_box, 3),
        "composite": round(composite, 3),
        "vulnerability": round(1 - composite, 3),  # how easily disrupted
    }


# ══════════════════════════════════════════════════════════════════════════════
# 6. CENTERS OF CALCULATION (Latour 1987)
# ══════════════════════════════════════════════════════════════════════════════

def compute_centers_of_calculation(G: nx.Graph, top_n: int = 10) -> list[dict]:
    """Identify centers of calculation in the network.

    Latour (1987): centers of calculation are places where information
    from far-flung locations is gathered, processed, and used to exert
    control at a distance. In CivGraph: agents who sit at the
    intersection of multiple institutional memberships + high network
    position + information-processing capacity.
    """
    centers = []

    for nid in G.nodes:
        agent = G.nodes[nid]["agent"]

        # Information reach: how many unique sources this agent sees
        neighbor_count = G.degree(nid)
        clan_reach = len(set(G.nodes[nb]["agent"].clan for nb in G.neighbors(nid)))
        district_reach = len(set(G.nodes[nb]["agent"].district for nb in G.neighbors(nid)))

        # Institutional reach: membership across different institution types
        inst_type_diversity = 0
        total_inst_reach = 0
        if agent.institutions:
            inst_types = set(m.institution_type.value for m in agent.institutions.memberships)
            inst_type_diversity = len(inst_types)
            total_inst_reach = len(agent.institutions.memberships)

        # Processing capacity: education × cultural capital
        processing = agent.habitus.education_track.cultural_base * 0.5 + agent.capital.cultural * 0.5

        # Control capacity: symbolic capital + board power
        board_power = agent.institutions.board_power if agent.institutions else 0
        control = agent.capital.symbolic * 0.4 + board_power * 0.4 + agent.capital.economic * 0.2

        # Center of calculation score
        score = (
            math.sqrt(neighbor_count) / 8 * 0.20 +     # network reach
            clan_reach / 20 * 0.15 +                     # cross-clan visibility
            district_reach / 10 * 0.10 +                 # cross-district visibility
            inst_type_diversity / 8 * 0.20 +             # institutional diversity
            processing * 0.15 +                           # information processing
            control * 0.20                                # power to act on information
        )

        centers.append({
            "agent_id": nid,
            "agent_name": agent.name,
            "score": round(score, 4),
            "network_reach": neighbor_count,
            "clan_reach": clan_reach,
            "institutional_diversity": inst_type_diversity,
            "processing_capacity": round(processing, 3),
            "control_capacity": round(control, 3),
        })

    centers.sort(key=lambda x: x["score"], reverse=True)
    return centers[:top_n]


# ══════════════════════════════════════════════════════════════════════════════
# 7. HETEROGENEOUS ENGINEERING (Law 1987)
# ══════════════════════════════════════════════════════════════════════════════

def compute_heterogeneous_alignment(G: nx.Graph) -> dict:
    """Measure alignment across heterogeneous network elements.

    Law (1987): stable networks require alignment of heterogeneous
    elements — people, technologies, institutions, norms, capital.
    Misalignment creates fragility; alignment creates durability.
    """
    agents = [G.nodes[n]["agent"] for n in G.nodes]
    n = len(agents) or 1

    # ── Economic-institutional alignment ───────────────────────────
    # Are agents' economic positions consistent with their institutional
    # positions? (upper class → professional boards, lower class → civic/religious)
    econ_inst_alignment = 0.0
    for a in agents:
        if not a.institutions or not a.institutions.memberships:
            continue
        rank = a.habitus.current_class.rank
        for m in a.institutions.memberships:
            prof = m.institution_type.value
            # Expected alignment
            if prof in ("professional_board", "social_club") and rank >= 3:
                econ_inst_alignment += 0.3
            elif prof in ("civic_association", "religious_community") and rank <= 2:
                econ_inst_alignment += 0.2
            elif prof in ("industry_body", "alumni_network"):
                econ_inst_alignment += 0.15
            elif prof == "political_org":
                econ_inst_alignment += 0.1
    econ_inst = econ_inst_alignment / max(1, sum(
        len(a.institutions.memberships) for a in agents if a.institutions
    ))

    # ── Technology-skill alignment ─────────────────────────────────
    # Are agents' skills aligned with current technology demands?
    tech_skill_alignment = 0.0
    for a in agents:
        if a.institutions and a.economy:
            # Skill currency should match tech adaptation needs
            alignment = 1 - abs(a.institutions.skill_currency - a.economy.tech_adaptation)
            tech_skill_alignment += alignment
    tech_skill = tech_skill_alignment / n

    # ── Capital-network alignment ──────────────────────────────────
    # Is capital distribution consistent with network position?
    cap_net_alignment = 0.0
    for nid in G.nodes:
        agent = G.nodes[nid]["agent"]
        degree = G.degree(nid)
        # High degree should correlate with high social capital
        degree_norm = min(1.0, math.sqrt(degree) / 8)
        cap_net_alignment += 1 - abs(degree_norm - agent.capital.social)
    cap_net = cap_net_alignment / n

    # ── Norm-opinion alignment ─────────────────────────────────────
    # Do individual opinions align with crystallized norms?
    norm_opinion_alignment = 0.0
    norm_opinion_count = 0
    for a in agents:
        for topic, norm_val in a.norms.items():
            opinion_val = a.opinion_state.get(topic, 0)
            if norm_val != 0:
                alignment = 1 - abs(norm_val - opinion_val) / 2
                norm_opinion_alignment += alignment
                norm_opinion_count += 1
    norm_opinion = norm_opinion_alignment / max(1, norm_opinion_count)

    # ── Composite alignment (Law's heterogeneous engineering) ──────
    composite = (
        econ_inst * 0.25 +
        tech_skill * 0.25 +
        cap_net * 0.25 +
        norm_opinion * 0.25
    )

    return {
        "economic_institutional": round(econ_inst, 3),
        "technology_skill": round(tech_skill, 3),
        "capital_network": round(cap_net, 3),
        "norm_opinion": round(norm_opinion, 3),
        "composite": round(composite, 3),
        "fragility": round(1 - composite, 3),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 8. NETWORK PROGRAMMERS & SWITCHERS (Castells 2009)
# ══════════════════════════════════════════════════════════════════════════════

def compute_network_capital(G: nx.Graph, top_n: int = 15, bc_cache: dict | None = None) -> dict:
    """Identify network programmers and switchers.

    Castells (2009): power in network society operates through two
    mechanisms:
    - Programmers: those who can constitute and reprogram networks
      (set the rules, define membership, establish goals)
    - Switchers: those who connect different networks and control
      the switching points between them

    In CivGraph:
    - Programmers = high symbolic capital + institutional leadership +
      political influence (they set the agenda)
    - Switchers = high cross-clan/cross-type institutional membership +
      high betweenness (they connect otherwise separate worlds)
    """
    agents_data = []

    bc = bc_cache or nx.betweenness_centrality(G, weight="weight", k=min(200, G.number_of_nodes()))

    for nid in G.nodes:
        agent = G.nodes[nid]["agent"]

        # Programmer score
        leadership_count = 0
        if agent.institutions:
            leadership_count = sum(1 for m in agent.institutions.memberships if m.leadership_role)
        programmer = (
            agent.capital.symbolic * 0.30 +
            (agent.institutions.board_power if agent.institutions else 0) * 0.25 +
            leadership_count * 0.15 +
            agent.influence * 0.15 +
            (abs(agent.politics.numeric) / 3) * 0.15  # political conviction
        )

        # Switcher score
        neighbor_clans = len(set(G.nodes[nb]["agent"].clan for nb in G.neighbors(nid)))
        inst_types = set()
        if agent.institutions:
            inst_types = set(m.institution_type.value for m in agent.institutions.memberships)
        cross_type_memberships = len(inst_types)

        # Edge type diversity
        edge_types = set()
        for nb in G.neighbors(nid):
            edge_types.add(G.edges[nid, nb].get("rel", "unknown"))

        switcher = (
            bc.get(nid, 0) * 0.30 +
            neighbor_clans / 20 * 0.25 +
            cross_type_memberships / 8 * 0.25 +
            len(edge_types) / 9 * 0.20  # 9 possible edge types
        )

        agents_data.append({
            "agent_id": nid,
            "agent_name": agent.name,
            "programmer_score": round(programmer, 4),
            "switcher_score": round(switcher, 4),
            "combined": round(programmer * 0.5 + switcher * 0.5, 4),
            "leadership_count": leadership_count,
            "clan_reach": neighbor_clans,
            "inst_type_diversity": cross_type_memberships,
        })

    # Top programmers
    programmers = sorted(agents_data, key=lambda x: x["programmer_score"], reverse=True)[:top_n]
    # Top switchers
    switchers = sorted(agents_data, key=lambda x: x["switcher_score"], reverse=True)[:top_n]

    return {
        "programmers": programmers,
        "switchers": switchers,
    }


# ══════════════════════════════════════════════════════════════════════════════
# AGGREGATE STS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def compute_sts_snapshot(G: nx.Graph, tech_waves: dict | None = None,
                         media_landscape=None) -> dict:
    """Compute full STS analytics snapshot.

    Returns all STS-derived metrics in a single dict for the API.
    Betweenness centrality is computed once and shared across functions.
    """
    # Compute betweenness once (most expensive operation) and share
    _shared_bc = nx.betweenness_centrality(G, weight="weight", k=min(200, G.number_of_nodes()))

    actants = compute_nonhuman_actants(tech_waves or {}, media_landscape, {})
    opps = compute_passage_points(G, bc_cache=_shared_bc)
    performativity = compute_performativity(G)
    black_boxing = compute_black_boxing(G, tech_waves)
    centers = compute_centers_of_calculation(G)
    alignment = compute_heterogeneous_alignment(G)
    network_capital = compute_network_capital(G, bc_cache=_shared_bc)

    return {
        "actants": [
            {"name": a.name, "domain": a.domain, "agency": a.agency,
             "reach": a.reach, "stability": a.stability, "inscription": a.inscription}
            for a in actants
        ],
        "obligatory_passage_points": opps[:10],
        "performativity": performativity,
        "black_boxing": black_boxing,
        "centers_of_calculation": centers,
        "heterogeneous_alignment": alignment,
        "network_capital": network_capital,
    }
