"""
CivGraph — Bourdieusian capital model.

Four forms of capital (economic, cultural, social, symbolic),
habitus as internalized disposition, lifecycle curves, capital
conversion, and intergenerational transmission.

Calibrated to Western European context (FR/DE/NL averages).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum


# ── Western European calibration ─────────────────────────────────────────────

EU_CONFIG = {
    "welfare_floor": 0.15,
    "ige_economic": 0.35,
    "ige_cultural": 0.50,
    "gini_target": 0.32,
    "university_rate": 0.45,
    "inheritance_transfer_rate": 0.65,
    "class_distribution": {
        "upper": 0.05,
        "upper_middle": 0.15,
        "middle": 0.40,
        "lower_middle": 0.25,
        "lower": 0.15,
    },
    "education_class_correlation": {
        "upper":        {"elite": 0.35, "academic": 0.45, "applied": 0.15, "vocational": 0.05},
        "upper_middle": {"elite": 0.15, "academic": 0.45, "applied": 0.30, "vocational": 0.10},
        "middle":       {"elite": 0.05, "academic": 0.30, "applied": 0.40, "vocational": 0.25},
        "lower_middle": {"elite": 0.02, "academic": 0.18, "applied": 0.35, "vocational": 0.45},
        "lower":        {"elite": 0.01, "academic": 0.09, "applied": 0.30, "vocational": 0.60},
    },
    # Capital conversion friction rates (source -> target -> efficiency)
    "conversion_rates": {
        "economic": {"cultural": 0.40, "social": 0.30, "symbolic": 0.20},
        "cultural": {"economic": 0.50, "social": 0.40, "symbolic": 0.50},
        "social":   {"economic": 0.40, "cultural": 0.30, "symbolic": 0.30},
        "symbolic": {"economic": 0.30, "cultural": 0.20, "social": 0.50},
    },
}


# ── Enums ────────────────────────────────────────────────────────────────────

class SocialClass(str, Enum):
    LOWER = "lower"
    LOWER_MIDDLE = "lower_middle"
    MIDDLE = "middle"
    UPPER_MIDDLE = "upper_middle"
    UPPER = "upper"

    @property
    def rank(self) -> int:
        return ["lower", "lower_middle", "middle", "upper_middle", "upper"].index(self.value)

    @classmethod
    def from_rank(cls, r: int) -> "SocialClass":
        return [cls.LOWER, cls.LOWER_MIDDLE, cls.MIDDLE, cls.UPPER_MIDDLE, cls.UPPER][
            max(0, min(4, r))
        ]


class EducationTrack(str, Enum):
    VOCATIONAL = "vocational"
    APPLIED = "applied"
    ACADEMIC = "academic"
    ELITE = "elite"

    @property
    def cultural_base(self) -> float:
        return {"vocational": 0.20, "applied": 0.35, "academic": 0.55, "elite": 0.78}[self.value]

    @property
    def economic_multiplier(self) -> float:
        return {"vocational": 0.85, "applied": 1.0, "academic": 1.15, "elite": 1.45}[self.value]


class LifePhase(str, Enum):
    EDUCATION = "education"
    EARLY_CAREER = "early_career"
    MID_CAREER = "mid_career"
    ESTABLISHED = "established"
    ELDER = "elder"


def life_phase_from_age(age: int) -> LifePhase:
    if age < 25:
        return LifePhase.EDUCATION
    if age < 35:
        return LifePhase.EARLY_CAREER
    if age < 55:
        return LifePhase.MID_CAREER
    if age < 70:
        return LifePhase.ESTABLISHED
    return LifePhase.ELDER


# ── Capital ──────────────────────────────────────────────────────────────────

@dataclass
class Capital:
    economic: float
    cultural: float
    social: float
    symbolic: float

    @property
    def total_volume(self) -> float:
        return (self.economic + self.cultural + self.social + self.symbolic) / 4

    @property
    def composition(self) -> tuple[float, float]:
        """(economic-vs-cultural, social-vs-symbolic). Positive = first dominates."""
        return (self.economic - self.cultural, self.social - self.symbolic)

    def clamp(self) -> "Capital":
        self.economic = max(EU_CONFIG["welfare_floor"], min(1.0, self.economic))
        self.cultural = max(0.0, min(1.0, self.cultural))
        self.social = max(0.0, min(1.0, self.social))
        self.symbolic = max(0.0, min(1.0, self.symbolic))
        return self

    def to_dict(self) -> dict:
        return {
            "economic": round(self.economic, 3),
            "cultural": round(self.cultural, 3),
            "social": round(self.social, 3),
            "symbolic": round(self.symbolic, 3),
            "total_volume": round(self.total_volume, 3),
        }


# ── Habitus ──────────────────────────────────────────────────────────────────

@dataclass
class Habitus:
    origin_class: SocialClass
    current_class: SocialClass
    education_track: EducationTrack
    cultural_taste: float       # -1 (popular) to 1 (legitimate/highbrow)
    risk_tolerance: float       # 0-1
    institutional_trust: float  # 0-1
    class_awareness: float      # 0-1
    aspiration_gap: float       # current_class.rank - origin_class.rank (signed)

    def to_dict(self) -> dict:
        return {
            "origin_class": self.origin_class.value,
            "current_class": self.current_class.value,
            "education_track": self.education_track.value,
            "cultural_taste": round(self.cultural_taste, 3),
            "risk_tolerance": round(self.risk_tolerance, 3),
            "institutional_trust": round(self.institutional_trust, 3),
            "class_awareness": round(self.class_awareness, 3),
            "aspiration_gap": round(self.aspiration_gap, 3),
        }


# ── Lifecycle curves ─────────────────────────────────────────────────────────
# Multipliers applied to base capital at each life phase.

LIFECYCLE_CURVES = {
    #                      economic  cultural  social  symbolic
    LifePhase.EDUCATION:     (0.15,    0.55,    0.30,   0.05),
    LifePhase.EARLY_CAREER:  (0.50,    0.75,    0.50,   0.15),
    LifePhase.MID_CAREER:    (1.00,    0.90,    0.80,   0.50),
    LifePhase.ESTABLISHED:   (0.85,    1.00,    1.00,   1.00),
    LifePhase.ELDER:         (0.70,    0.95,    0.75,   0.90),
}


def apply_lifecycle(base: Capital, phase: LifePhase) -> Capital:
    """Scale base capital by lifecycle phase multipliers."""
    m = LIFECYCLE_CURVES[phase]
    return Capital(
        economic=base.economic * m[0],
        cultural=base.cultural * m[1],
        social=base.social * m[2],
        symbolic=base.symbolic * m[3],
    ).clamp()


# ── Generation functions ─────────────────────────────────────────────────────

def pick_education(social_class: SocialClass, rng: random.Random | None = None) -> EducationTrack:
    """Weighted random education track based on class of origin."""
    r = rng or random
    probs = EU_CONFIG["education_class_correlation"][social_class.value]
    roll = r.random()
    cumulative = 0.0
    for track_name, p in probs.items():
        cumulative += p
        if roll <= cumulative:
            return EducationTrack(track_name)
    return EducationTrack.VOCATIONAL


def pick_class(center_rank: float, rng: random.Random | None = None) -> SocialClass:
    """Draw a social class near a center rank (0-4) with noise."""
    r = rng or random
    drawn = center_rank + r.gauss(0, 0.8)
    return SocialClass.from_rank(round(drawn))


def generate_age(rng: random.Random | None = None) -> int:
    """Age distribution: truncated normal centered at 42, sigma 12."""
    r = rng or random
    age = int(r.gauss(42, 12))
    return max(18, min(75, age))


def generate_habitus(
    origin_class: SocialClass,
    education_track: EducationTrack,
    age: int,
    rng: random.Random | None = None,
) -> Habitus:
    r = rng or random

    # Cultural taste correlates with origin class (r ~ 0.6) + noise
    class_taste_base = (origin_class.rank / 4) * 2 - 1  # maps 0-4 to -1..1
    cultural_taste = class_taste_base * 0.6 + r.gauss(0, 0.3)
    cultural_taste += (education_track.cultural_base - 0.4) * 0.5
    cultural_taste = max(-1, min(1, cultural_taste))

    # Risk tolerance: U-shaped (high at extremes, low in middle class)
    class_center = abs(origin_class.rank - 2) / 2  # 0 at middle, 1 at extremes
    risk_tolerance = 0.3 + class_center * 0.3 + r.gauss(0, 0.12)
    risk_tolerance = max(0, min(1, risk_tolerance))

    # Institutional trust: peaks in upper-middle class
    trust_base = 1.0 - abs(origin_class.rank - 3) / 3
    institutional_trust = trust_base * 0.7 + r.gauss(0, 0.15)
    institutional_trust = max(0, min(1, institutional_trust))

    # Class awareness: higher at extremes
    class_awareness = 0.3 + class_center * 0.4 + r.gauss(0, 0.1)
    class_awareness = max(0, min(1, class_awareness))

    # Current class: starts at origin, with some drift by age
    drift = r.gauss(0, 0.4) + education_track.cultural_base * 0.3
    current_rank = origin_class.rank + drift
    if age > 35:
        current_rank += r.gauss(0, 0.3)
    current_class = SocialClass.from_rank(round(current_rank))

    aspiration_gap = current_class.rank - origin_class.rank

    return Habitus(
        origin_class=origin_class,
        current_class=current_class,
        education_track=education_track,
        cultural_taste=cultural_taste,
        risk_tolerance=risk_tolerance,
        institutional_trust=institutional_trust,
        class_awareness=class_awareness,
        aspiration_gap=aspiration_gap,
    )


def generate_capital(
    social_class: SocialClass,
    education_track: EducationTrack,
    age: int,
    rng: random.Random | None = None,
) -> Capital:
    """Generate initial capital volumes calibrated to Western European norms."""
    r = rng or random
    phase = life_phase_from_age(age)

    # Economic: Beta distribution parameterized by class
    ec_params = {
        SocialClass.LOWER: (2, 8),
        SocialClass.LOWER_MIDDLE: (2.5, 5),
        SocialClass.MIDDLE: (3.5, 3.5),
        SocialClass.UPPER_MIDDLE: (5, 2.5),
        SocialClass.UPPER: (7, 2),
    }
    a, b = ec_params[social_class]
    economic = r.betavariate(a, b) * education_track.economic_multiplier

    # Cultural: education track base + class influence + noise
    cultural = education_track.cultural_base + social_class.rank * 0.06 + r.gauss(0, 0.08)

    # Social: moderate base, increases with class (networks)
    social = 0.2 + social_class.rank * 0.08 + r.gauss(0, 0.1)

    # Symbolic: low base, strongly class-dependent, peaks later in life
    symbolic = social_class.rank * 0.12 + r.gauss(0, 0.06)

    base = Capital(
        economic=max(EU_CONFIG["welfare_floor"], economic),
        cultural=max(0, cultural),
        social=max(0, social),
        symbolic=max(0, symbolic),
    )

    return apply_lifecycle(base, phase)


# ── Habitus affinity ─────────────────────────────────────────────────────────

def habitus_affinity(h1: Habitus, h2: Habitus) -> float:
    """0-1 score: how naturally two agents gravitate toward each other."""
    score = 0.0
    # Same origin class
    if h1.origin_class == h2.origin_class:
        score += 0.30
    elif abs(h1.origin_class.rank - h2.origin_class.rank) == 1:
        score += 0.12
    # Similar cultural taste
    taste_dist = abs(h1.cultural_taste - h2.cultural_taste)
    if taste_dist < 0.3:
        score += 0.25 * (1 - taste_dist / 0.3)
    # Same education track
    if h1.education_track == h2.education_track:
        score += 0.20
    # Similar institutional trust
    trust_dist = abs(h1.institutional_trust - h2.institutional_trust)
    if trust_dist < 0.3:
        score += 0.15 * (1 - trust_dist / 0.3)
    # Adjacent current class
    if abs(h1.current_class.rank - h2.current_class.rank) <= 1:
        score += 0.10
    return min(1.0, score)


# ── Capital field relevance ──────────────────────────────────────────────────

TOPIC_CAPITAL_WEIGHTS = {
    "real_estate":    {"economic": 0.8, "cultural": 0.1, "social": 0.3, "symbolic": 0.2},
    "tech":           {"economic": 0.5, "cultural": 0.6, "social": 0.3, "symbolic": 0.3},
    "healthcare":     {"economic": 0.4, "cultural": 0.5, "social": 0.4, "symbolic": 0.5},
    "education":      {"economic": 0.2, "cultural": 0.9, "social": 0.3, "symbolic": 0.5},
    "arts":           {"economic": 0.2, "cultural": 0.9, "social": 0.4, "symbolic": 0.6},
    "finance":        {"economic": 0.9, "cultural": 0.2, "social": 0.5, "symbolic": 0.3},
    "manufacturing":  {"economic": 0.7, "cultural": 0.2, "social": 0.4, "symbolic": 0.2},
    "media":          {"economic": 0.4, "cultural": 0.7, "social": 0.6, "symbolic": 0.7},
    "law":            {"economic": 0.5, "cultural": 0.6, "social": 0.5, "symbolic": 0.7},
    "energy":         {"economic": 0.8, "cultural": 0.2, "social": 0.3, "symbolic": 0.3},
    "agriculture":    {"economic": 0.6, "cultural": 0.2, "social": 0.3, "symbolic": 0.2},
    "hospitality":    {"economic": 0.5, "cultural": 0.4, "social": 0.6, "symbolic": 0.2},
    "transport":      {"economic": 0.6, "cultural": 0.1, "social": 0.3, "symbolic": 0.2},
    "security":       {"economic": 0.4, "cultural": 0.2, "social": 0.5, "symbolic": 0.6},
    "environment":    {"economic": 0.3, "cultural": 0.6, "social": 0.5, "symbolic": 0.4},
    "sports":         {"economic": 0.5, "cultural": 0.3, "social": 0.6, "symbolic": 0.7},
    "retail":         {"economic": 0.7, "cultural": 0.2, "social": 0.3, "symbolic": 0.1},
    "philanthropy":   {"economic": 0.6, "cultural": 0.4, "social": 0.7, "symbolic": 0.8},
    "religion":       {"economic": 0.2, "cultural": 0.5, "social": 0.7, "symbolic": 0.8},
    "unions":         {"economic": 0.5, "cultural": 0.3, "social": 0.8, "symbolic": 0.4},
    "governance":     {"economic": 0.4, "cultural": 0.4, "social": 0.6, "symbolic": 0.8},
    "trust":          {"economic": 0.2, "cultural": 0.3, "social": 0.8, "symbolic": 0.7},
    "power":          {"economic": 0.5, "cultural": 0.3, "social": 0.6, "symbolic": 0.9},
}


def capital_field_relevance(capital: Capital, topic: str) -> float:
    """How relevant an agent's capital profile is to a topic (0-1)."""
    weights = TOPIC_CAPITAL_WEIGHTS.get(topic, {"economic": 0.25, "cultural": 0.25,
                                                 "social": 0.25, "symbolic": 0.25})
    score = (
        capital.economic * weights.get("economic", 0.25) +
        capital.cultural * weights.get("cultural", 0.25) +
        capital.social * weights.get("social", 0.25) +
        capital.symbolic * weights.get("symbolic", 0.25)
    )
    return min(1.0, score)


# ── Habitus reaction modifier ────────────────────────────────────────────────

def habitus_reaction_modifier(habitus: Habitus, topic: str, sentiment: float) -> float:
    """Modify event reaction based on habitus dispositions. Returns multiplier around 1.0."""
    mod = 1.0

    # Institutional trust affects reaction to governance/policy
    if topic in ("governance", "law", "security", "power"):
        mod *= 0.7 + 0.6 * habitus.institutional_trust

    # Risk tolerance dampens negative reactions to crises
    if sentiment < -0.2 and topic in ("finance", "real_estate", "manufacturing", "energy"):
        mod *= 0.6 + 0.8 * habitus.risk_tolerance

    # Cultural taste amplifies reaction to cultural topics
    if topic in ("arts", "education", "media", "religion"):
        mod *= 0.7 + 0.5 * abs(habitus.cultural_taste)

    # Class awareness amplifies reaction to inequality-related events
    if topic in ("unions", "governance", "philanthropy"):
        mod *= 0.8 + 0.4 * habitus.class_awareness

    return max(0.3, min(2.0, mod))


# ── Capital conversion ───────────────────────────────────────────────────────

_VALID_CAPITAL_TYPES = {"economic", "cultural", "social", "symbolic"}

def convert_capital(capital: Capital, source: str, target: str, amount: float) -> Capital:
    """Convert capital from one type to another with friction.
    Returns a new Capital with the conversion applied."""
    if source not in _VALID_CAPITAL_TYPES or target not in _VALID_CAPITAL_TYPES:
        raise ValueError(f"Invalid capital type: source={source}, target={target}")
    rates = EU_CONFIG["conversion_rates"]
    efficiency = rates.get(source, {}).get(target, 0.2)

    src_val = getattr(capital, source)
    actual = min(amount, src_val * 0.5)  # can't convert more than half
    gained = actual * efficiency

    new = Capital(
        economic=capital.economic,
        cultural=capital.cultural,
        social=capital.social,
        symbolic=capital.symbolic,
    )
    setattr(new, source, getattr(new, source) - actual)
    setattr(new, target, getattr(new, target) + gained)
    return new.clamp()


# ── Intergenerational transmission ───────────────────────────────────────────

def transmit_economic(parent_economic: float, rng: random.Random | None = None) -> float:
    """Economic capital inheritance (after taxes)."""
    r = rng or random
    rate = EU_CONFIG["inheritance_transfer_rate"]
    base = parent_economic * rate * EU_CONFIG["ige_economic"]
    noise = r.gauss(0, 0.05)
    return max(EU_CONFIG["welfare_floor"], base + noise)


def transmit_cultural(parent_capital: Capital, parent_habitus: Habitus,
                      rng: random.Random | None = None) -> float:
    """Cultural capital: stickier than economic (Bourdieu's key insight)."""
    r = rng or random
    base = (
        parent_capital.cultural * EU_CONFIG["ige_cultural"] * 0.7 +
        abs(parent_habitus.cultural_taste) * 0.2 +
        r.gauss(0, 0.06)
    )
    return max(0, min(1, base))


def transmit_symbolic(parent_symbolic: float, clan_avg_symbolic: float,
                      rng: random.Random | None = None) -> float:
    """Symbolic capital: partly individual, partly clan name."""
    r = rng or random
    base = parent_symbolic * 0.30 + clan_avg_symbolic * 0.20 + r.gauss(0, 0.04)
    return max(0, min(1, base))


def inherit_habitus(parent_habitus: Habitus, child_class: SocialClass,
                    child_education: EducationTrack,
                    rng: random.Random | None = None) -> Habitus:
    """Habitus reproduction: child's dispositions shaped by parent's."""
    r = rng or random

    cultural_taste = parent_habitus.cultural_taste * 0.6 + r.gauss(0, 0.25)
    cultural_taste = max(-1, min(1, cultural_taste))

    institutional_trust = parent_habitus.institutional_trust * 0.5 + r.gauss(0, 0.2)
    institutional_trust = max(0, min(1, institutional_trust))

    risk_tolerance = parent_habitus.risk_tolerance * 0.4 + r.gauss(0, 0.15)
    risk_tolerance = max(0, min(1, risk_tolerance))

    class_awareness = parent_habitus.class_awareness * 0.5 + r.gauss(0, 0.15)
    class_awareness = max(0, min(1, class_awareness))

    return Habitus(
        origin_class=parent_habitus.current_class,
        current_class=child_class,
        education_track=child_education,
        cultural_taste=cultural_taste,
        risk_tolerance=risk_tolerance,
        institutional_trust=institutional_trust,
        class_awareness=class_awareness,
        aspiration_gap=child_class.rank - parent_habitus.current_class.rank,
    )


# ── Derived influence from capital ───────────────────────────────────────────

def capital_to_influence(capital: Capital) -> float:
    """Derive the backward-compatible influence score from capital."""
    return min(1.0,
        capital.symbolic * 0.40 +
        capital.social * 0.30 +
        capital.economic * 0.20 +
        capital.cultural * 0.10
    )
