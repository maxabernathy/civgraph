"""
CivGraph -- Health system model.

Social determinants of health (Marmot 2005, WHO CSDH 2008): health
outcomes are shaped by the conditions in which people are born, grow,
live, work, and age — not just by individual biology or healthcare.

Per-agent health is a function of:
  - Class gradient: upper classes enjoy systematically better health
  - Economic capital: affords nutrition, housing quality, private care
  - Education: health literacy, preventive behaviour
  - Social capital: strong networks buffer stress (Berkman & Syme 1979)
  - Age: baseline deterioration + chronic condition risk
  - Work: displacement stress, precarity → mental health impact
  - Environment: city-level healthcare access, pollution, services

Calibrated to Western European health patterns (~2020s).

References:
  - Marmot (2005): Status Syndrome
  - Wilkinson & Pickett (2009): The Spirit Level
  - Berkman & Syme (1979): Social networks and mortality
  - Case & Deaton (2015): Deaths of despair
  - WHO CSDH (2008): Closing the gap in a generation
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════════════════
# AGENT HEALTH STATE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentHealth:
    """Per-agent health profile."""
    physical_health: float = 0.75       # 0-1 overall physical health
    mental_health: float = 0.70         # 0-1 psychological wellbeing
    healthcare_access: float = 0.60     # 0-1 ability to access care
    chronic_condition: bool = False     # has a chronic illness
    health_literacy: float = 0.50      # 0-1 ability to manage own health
    work_capacity: float = 1.0         # 0-1 derived ability to work
    stress_level: float = 0.30         # 0-1 accumulated stress
    disability: float = 0.0           # 0-1 degree of disability

    def to_dict(self) -> dict:
        return {
            "physical_health": round(self.physical_health, 3),
            "mental_health": round(self.mental_health, 3),
            "healthcare_access": round(self.healthcare_access, 3),
            "chronic_condition": self.chronic_condition,
            "health_literacy": round(self.health_literacy, 3),
            "work_capacity": round(self.work_capacity, 3),
            "stress_level": round(self.stress_level, 3),
            "disability": round(self.disability, 3),
        }

    @property
    def composite(self) -> float:
        """Overall health score 0-1."""
        return (
            self.physical_health * 0.40 +
            self.mental_health * 0.30 +
            (1 - self.stress_level) * 0.15 +
            (1 - self.disability) * 0.15
        )


# ── Age-based chronic condition probabilities ──────────────────────────────
# Per-year probability of developing a chronic condition, by age band.
# Based on EU-SILC chronic morbidity data.

CHRONIC_PROB_BY_AGE = {
    # (min_age, max_age): annual probability
    (18, 30): 0.005,
    (30, 45): 0.012,
    (45, 55): 0.025,
    (55, 65): 0.040,
    (65, 75): 0.060,
    (75, 100): 0.080,
}


def _chronic_probability(age: int) -> float:
    for (lo, hi), prob in CHRONIC_PROB_BY_AGE.items():
        if lo <= age < hi:
            return prob
    return 0.06


# ══════════════════════════════════════════════════════════════════════════════
# GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def generate_agent_health(
    age: int,
    class_rank: int,
    education_track_value: str,
    economic_capital: float,
    social_capital: float,
    rng: random.Random | None = None,
) -> AgentHealth:
    """Initialize health from demographics.

    Social gradient: each step up the class ladder buys ~2-3 years of
    healthy life expectancy (Marmot 2005).
    """
    r = rng or random

    # ── Physical health: class gradient + age decline ──────────────
    # Base from class (upper = 0.90, lower = 0.60)
    class_base = 0.60 + class_rank * 0.075
    # Age decline: gentle until 50, then steeper
    if age < 50:
        age_penalty = (age - 18) * 0.003
    else:
        age_penalty = (50 - 18) * 0.003 + (age - 50) * 0.008
    physical = class_base - age_penalty + r.gauss(0, 0.06)
    physical = max(0.10, min(1.0, physical))

    # ── Chronic condition ──────────────────────────────────────────
    # Lower class = higher risk (× 1.5 for lower, × 0.7 for upper)
    class_modifier = 1.5 - class_rank * 0.2
    chronic = r.random() < _chronic_probability(age) * class_modifier * (age / 45)

    if chronic:
        physical *= 0.75  # chronic condition reduces baseline

    # ── Mental health ──────────────────────────────────────────────
    # Social capital is protective (Berkman & Syme 1979)
    social_protection = social_capital * 0.15
    # Economic security reduces anxiety
    economic_protection = economic_capital * 0.10
    mental = 0.55 + social_protection + economic_protection + r.gauss(0, 0.08)
    mental = max(0.10, min(1.0, mental))

    # ── Healthcare access: class + economics ───────────────────────
    # Western European universal healthcare baseline, but class still matters
    access_base = 0.55  # universal floor
    access = access_base + class_rank * 0.06 + economic_capital * 0.15 + r.gauss(0, 0.05)
    access = max(0.20, min(1.0, access))

    # ── Health literacy: education-driven ──────────────────────────
    edu_lit = {"vocational": 0.30, "applied": 0.45, "academic": 0.65, "elite": 0.80}.get(
        education_track_value, 0.40
    )
    health_literacy = edu_lit * 0.7 + class_rank * 0.04 + r.gauss(0, 0.06)
    health_literacy = max(0.05, min(1.0, health_literacy))

    # ── Stress: inversely related to class + economic security ─────
    stress = 0.50 - class_rank * 0.06 - economic_capital * 0.10 + r.gauss(0, 0.08)
    stress = max(0.05, min(0.90, stress))

    # ── Disability ─────────────────────────────────────────────────
    disability = 0.0
    if chronic and age > 55:
        disability = r.betavariate(1.5, 8) * 0.5
    elif age > 70:
        disability = r.betavariate(1.5, 10) * 0.3

    # ── Work capacity: derived ─────────────────────────────────────
    work_capacity = physical * 0.5 + mental * 0.3 + (1 - disability) * 0.2
    if chronic:
        work_capacity *= 0.85

    return AgentHealth(
        physical_health=round(physical, 3),
        mental_health=round(mental, 3),
        healthcare_access=round(access, 3),
        chronic_condition=chronic,
        health_literacy=round(health_literacy, 3),
        work_capacity=round(max(0.1, min(1.0, work_capacity)), 3),
        stress_level=round(stress, 3),
        disability=round(disability, 3),
    )


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH EVOLUTION (per tick / year)
# ══════════════════════════════════════════════════════════════════════════════

def evolve_agent_health(
    health: AgentHealth,
    age: int,
    class_rank: int,
    economic_capital: float,
    social_capital: float,
    displacement_risk: float,
    satisfaction: float,
    env_health_indicators: dict,
    rng: random.Random,
):
    """Advance one agent's health by one year."""

    # ── Age-related decline ────────────────────────────────────────
    if age > 50:
        health.physical_health -= 0.008 + rng.gauss(0, 0.003)
    elif age > 35:
        health.physical_health -= 0.003 + rng.gauss(0, 0.002)

    # ── Chronic condition onset ────────────────────────────────────
    if not health.chronic_condition:
        class_mod = 1.5 - class_rank * 0.2
        if rng.random() < _chronic_probability(age) * class_mod:
            health.chronic_condition = True
            health.physical_health *= 0.80

    # ── Chronic condition management ───────────────────────────────
    if health.chronic_condition:
        # Good healthcare access + literacy → managed condition
        management = health.healthcare_access * 0.4 + health.health_literacy * 0.3
        health.physical_health += management * 0.02 - 0.01  # net decline moderated

    # ── Healthcare access effect ───────────────────────────────────
    env_access = env_health_indicators.get("healthcare_access", 0.65)
    health.healthcare_access = (
        health.healthcare_access * 0.8 +
        (0.55 + class_rank * 0.06 + economic_capital * 0.15) * 0.1 +
        env_access * 0.1
    )

    # ── Mental health dynamics ─────────────────────────────────────
    # Stress from displacement/job insecurity (Case & Deaton 2015)
    displacement_stress = displacement_risk * 0.15
    # Low satisfaction erodes mental health
    satisfaction_effect = (satisfaction - 0.5) * 0.08
    # Social support buffers (Berkman & Syme)
    social_buffer = social_capital * 0.06
    # Economic security
    economic_buffer = economic_capital * 0.04

    health.stress_level += displacement_stress - social_buffer - economic_buffer
    health.stress_level += rng.gauss(0, 0.02)
    health.stress_level = max(0.05, min(0.95, health.stress_level))

    health.mental_health += satisfaction_effect + social_buffer - displacement_stress * 0.5
    health.mental_health += rng.gauss(0, 0.02)

    # Environmental mental health support
    env_mental = env_health_indicators.get("mental_health_index", 0.60)
    health.mental_health += (env_mental - 0.5) * 0.03

    # ── Disability progression ─────────────────────────────────────
    if health.chronic_condition and age > 55:
        health.disability += 0.005 + rng.gauss(0, 0.003)
    if age > 70:
        health.disability += 0.003 + rng.gauss(0, 0.002)
    # Healthcare access slows disability
    if health.healthcare_access > 0.6:
        health.disability -= (health.healthcare_access - 0.6) * 0.005

    # ── Recompute work capacity ────────────────────────────────────
    health.work_capacity = (
        health.physical_health * 0.5 +
        health.mental_health * 0.3 +
        (1 - health.disability) * 0.2
    )
    if health.chronic_condition:
        health.work_capacity *= 0.85

    # ── Clamp all values ───────────────────────────────────────────
    health.physical_health = max(0.05, min(1.0, health.physical_health))
    health.mental_health = max(0.05, min(1.0, health.mental_health))
    health.healthcare_access = max(0.15, min(1.0, health.healthcare_access))
    health.work_capacity = max(0.10, min(1.0, health.work_capacity))
    health.disability = max(0.0, min(1.0, health.disability))


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH → ECONOMY COUPLING
# ══════════════════════════════════════════════════════════════════════════════

def health_affect_economy(health: AgentHealth, agent_economy):
    """Health constrains economic productivity."""
    if agent_economy is None:
        return
    # Work capacity directly scales productivity
    agent_economy.productivity *= health.work_capacity
    # Chronic conditions reduce income
    if health.chronic_condition:
        agent_economy.income *= (0.85 + health.healthcare_access * 0.10)
    # High stress reduces effective output
    if health.stress_level > 0.5:
        agent_economy.income *= (1 - (health.stress_level - 0.5) * 0.15)
    agent_economy.income = max(0.05, min(1.0, agent_economy.income))


def health_affect_capital(health: AgentHealth, capital):
    """Health status affects capital accumulation."""
    # Poor health drains economic capital (medical costs, lost work)
    if health.physical_health < 0.4:
        capital.economic -= (0.4 - health.physical_health) * 0.03
    # Good mental health supports social capital
    if health.mental_health > 0.6:
        capital.social += (health.mental_health - 0.6) * 0.01
    elif health.mental_health < 0.3:
        capital.social -= (0.3 - health.mental_health) * 0.02
    capital.clamp()


# ══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT HEALTH INDICATORS
# ══════════════════════════════════════════════════════════════════════════════

HEALTH_BASELINES = {
    "healthcare_access": 0.65,     # 0-1, universal care baseline
    "life_expectancy_index": 0.78, # 0-1, normalized
    "mental_health_index": 0.60,   # 0-1
    "health_inequality": 0.35,     # 0-1 (0 = equal, 1 = extreme gradient)
}

HEALTH_INDICATOR_META = {
    "healthcare_access":    ("Healthcare Access",   0.0, 1.0, "norm", True),
    "life_expectancy_index":("Life Expectancy",     0.0, 1.0, "norm", True),
    "mental_health_index":  ("Mental Health",       0.0, 1.0, "norm", True),
    "health_inequality":    ("Health Inequality",   0.0, 1.0, "norm", False),
}


def evolve_health_indicators(indicators: dict, rng: random.Random):
    """Evolve city-level health indicators by one year."""
    ind = indicators

    # Healthcare access: tracks public spending and GDP
    gdp = ind.get("gdp_growth", 0.018)
    pub_spend = ind.get("public_spending", 0.48)
    ind["healthcare_access"] += (pub_spend - 0.45) * 0.02 + gdp * 0.3
    ind["healthcare_access"] += rng.gauss(0, 0.005)

    # Life expectancy: slow improvement, eroded by inequality and poor mental health
    ind["life_expectancy_index"] += 0.002  # secular improvement
    ind["life_expectancy_index"] -= ind.get("health_inequality", 0.35) * 0.005
    ind["life_expectancy_index"] += rng.gauss(0, 0.003)

    # Mental health: tracks social cohesion, unemployment, rent burden
    cohesion = ind.get("social_cohesion", 0.62)
    unemp = ind.get("unemployment", 0.065)
    rent = ind.get("rent_burden", 0.32)
    ind["mental_health_index"] += (cohesion - 0.5) * 0.03
    ind["mental_health_index"] -= (unemp - 0.06) * 0.15
    ind["mental_health_index"] -= (rent - 0.30) * 0.05
    ind["mental_health_index"] += rng.gauss(0, 0.008)

    # Health inequality: tracks economic inequality, moderated by healthcare access
    gini_proxy = 1 - ind.get("business_confidence", 0.6)  # rough proxy
    ind["health_inequality"] += (gini_proxy - 0.4) * 0.02
    ind["health_inequality"] -= (ind["healthcare_access"] - 0.5) * 0.02
    ind["health_inequality"] += rng.gauss(0, 0.005)

    # Clamp
    for k in HEALTH_BASELINES:
        if k in ind:
            meta = HEALTH_INDICATOR_META.get(k)
            if meta:
                ind[k] = max(meta[1], min(meta[2], ind[k]))


def compute_health_stats(agents_health: list[AgentHealth]) -> dict:
    """Aggregate health statistics."""
    n = len(agents_health) or 1
    avg_physical = sum(h.physical_health for h in agents_health) / n
    avg_mental = sum(h.mental_health for h in agents_health) / n
    avg_work = sum(h.work_capacity for h in agents_health) / n
    avg_stress = sum(h.stress_level for h in agents_health) / n
    chronic_rate = sum(1 for h in agents_health if h.chronic_condition) / n
    disability_rate = sum(1 for h in agents_health if h.disability > 0.1) / n

    return {
        "avg_physical_health": round(avg_physical, 3),
        "avg_mental_health": round(avg_mental, 3),
        "avg_work_capacity": round(avg_work, 3),
        "avg_stress": round(avg_stress, 3),
        "chronic_condition_rate": round(chronic_rate, 3),
        "disability_rate": round(disability_rate, 3),
    }
