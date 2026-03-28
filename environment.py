"""
CivGraph — Macro-environment model.

Time-varying indicators for economy, housing, migration, culture,
and governance. Bidirectionally coupled with agent capital/habitus.
Calibrated to Western European mid-scale city baselines.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import networkx as nx


# ── Baseline values (Western European mid-scale city, ~2020s) ────────────────

BASELINES = {
    # Economy
    "gdp_growth":           0.018,   # 1.8% annual
    "unemployment":         0.065,   # 6.5%
    "inflation":            0.025,   # 2.5%
    "business_confidence":  0.60,    # 0-1

    # Housing
    "price_index":          1.00,    # relative baseline
    "vacancy_rate":         0.06,    # 6%
    "rent_burden":          0.32,    # 32% of income
    "construction_rate":    0.45,    # 0-1 normalized

    # Migration
    "net_migration":        0.005,   # 0.5% net annual inflow
    "diversity_index":      0.55,    # 0-1
    "integration_score":    0.60,    # 0-1

    # Culture
    "cultural_spending":    0.55,    # 0-1 (per capita, normalized)
    "social_cohesion":      0.62,    # 0-1
    "media_pluralism":      0.65,    # 0-1

    # Governance
    "public_spending":      0.48,    # 48% of GDP
    "corruption_index":     0.18,    # 0-1, 0 = clean
    "policy_stability":     0.70,    # 0-1
    "democratic_quality":   0.78,    # 0-1

    # Health
    "healthcare_access":    0.65,    # 0-1
    "life_expectancy_index":0.78,    # 0-1
    "mental_health_index":  0.60,    # 0-1
    "health_inequality":    0.35,    # 0-1 (0=equal)

    # Institutions & Education
    "education_quality":    0.68,    # 0-1
    "vocational_training_access": 0.55, # 0-1
    "civic_participation_index":  0.45, # 0-1
    "associational_density":      0.50, # 0-1
}

INDICATOR_DOMAINS = {
    "economy":       ["gdp_growth", "unemployment", "inflation", "business_confidence"],
    "housing":       ["price_index", "vacancy_rate", "rent_burden", "construction_rate"],
    "migration":     ["net_migration", "diversity_index", "integration_score"],
    "culture":       ["cultural_spending", "social_cohesion", "media_pluralism"],
    "governance":    ["public_spending", "corruption_index", "policy_stability", "democratic_quality"],
    "health":        ["healthcare_access", "life_expectancy_index", "mental_health_index", "health_inequality"],
    "institutions":  ["education_quality", "vocational_training_access", "civic_participation_index", "associational_density"],
}

# Display metadata: (label, min, max, format, higher_is_better)
INDICATOR_META = {
    "gdp_growth":          ("GDP Growth",          -0.05, 0.08,  "pct",   True),
    "unemployment":        ("Unemployment",         0.02, 0.25,  "pct",   False),
    "inflation":           ("Inflation",           -0.01, 0.12,  "pct",   None),
    "business_confidence": ("Business Confidence",  0.0,  1.0,   "norm",  True),
    "price_index":         ("Housing Price Index",  0.5,  2.5,   "index", None),
    "vacancy_rate":        ("Vacancy Rate",         0.0,  0.20,  "pct",   None),
    "rent_burden":         ("Rent Burden",          0.15, 0.60,  "pct",   False),
    "construction_rate":   ("Construction",         0.0,  1.0,   "norm",  True),
    "net_migration":       ("Net Migration",       -0.03, 0.06,  "pct",   None),
    "diversity_index":     ("Diversity",            0.0,  1.0,   "norm",  None),
    "integration_score":   ("Integration",          0.0,  1.0,   "norm",  True),
    "cultural_spending":   ("Cultural Spending",    0.0,  1.0,   "norm",  True),
    "social_cohesion":     ("Social Cohesion",      0.0,  1.0,   "norm",  True),
    "media_pluralism":     ("Media Pluralism",      0.0,  1.0,   "norm",  True),
    "public_spending":     ("Public Spending",      0.25, 0.65,  "pct",   None),
    "corruption_index":    ("Corruption",           0.0,  1.0,   "norm",  False),
    "policy_stability":    ("Policy Stability",     0.0,  1.0,   "norm",  True),
    "democratic_quality":  ("Democratic Quality",   0.0,  1.0,   "norm",  True),
    # Health
    "healthcare_access":   ("Healthcare Access",    0.0,  1.0,   "norm",  True),
    "life_expectancy_index":("Life Expectancy",     0.0,  1.0,   "norm",  True),
    "mental_health_index": ("Mental Health",        0.0,  1.0,   "norm",  True),
    "health_inequality":   ("Health Inequality",    0.0,  1.0,   "norm",  False),
    # Institutions
    "education_quality":   ("Education Quality",    0.0,  1.0,   "norm",  True),
    "vocational_training_access":("Vocational Training",0.0,1.0, "norm",  True),
    "civic_participation_index":("Civic Participation",0.0,1.0,  "norm",  True),
    "associational_density":("Assoc. Density",      0.0,  1.0,   "norm",  True),
}


# ── Environment state ────────────────────────────────────────────────────────

@dataclass
class Environment:
    """Macro-level indicators that evolve over time and couple with agents."""
    year: int = 0
    indicators: dict[str, float] = field(default_factory=lambda: dict(BASELINES))
    history: list[dict] = field(default_factory=list)
    shocks: list[dict] = field(default_factory=list)

    def snapshot(self) -> dict:
        return {"year": self.year, **{k: round(v, 4) for k, v in self.indicators.items()}}

    def record(self):
        self.history.append(self.snapshot())

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "indicators": {k: round(v, 4) for k, v in self.indicators.items()},
            "domains": {
                domain: {k: round(self.indicators[k], 4) for k in keys}
                for domain, keys in INDICATOR_DOMAINS.items()
            },
            "history_length": len(self.history),
        }

    def get_history(self) -> list[dict]:
        return self.history


def create_environment(seed: int | None = None) -> Environment:
    """Initialize environment with baseline + small random perturbation."""
    rng = random.Random(seed)
    env = Environment()
    for k, base in BASELINES.items():
        meta = INDICATOR_META[k]
        lo, hi = meta[1], meta[2]
        noise = rng.gauss(0, (hi - lo) * 0.03)
        env.indicators[k] = max(lo, min(hi, base + noise))
    env.record()
    return env


# ── Endogenous dynamics (indicator self-evolution) ───────────────────────────

def _evolve_indicators(env: Environment, rng: random.Random):
    """One year of indicator drift with internal coupling."""
    ind = env.indicators

    # Economy
    gdp_momentum = (ind["business_confidence"] - 0.5) * 0.01
    ind["gdp_growth"] += gdp_momentum + rng.gauss(0, 0.005)
    ind["gdp_growth"] = max(-0.05, min(0.08, ind["gdp_growth"]))

    # Unemployment inversely tracks GDP (Okun's law, ~2:1 ratio)
    ind["unemployment"] += -ind["gdp_growth"] * 1.8 + rng.gauss(0, 0.005)
    ind["unemployment"] = max(0.02, min(0.25, ind["unemployment"]))

    # Inflation: Phillips curve (loose) + supply noise
    ind["inflation"] += (0.07 - ind["unemployment"]) * 0.08 + rng.gauss(0, 0.003)
    ind["inflation"] = max(-0.01, min(0.12, ind["inflation"]))

    # Business confidence: mean-reverts, reacts to GDP & unemployment
    conf_target = 0.5 + ind["gdp_growth"] * 5 - (ind["unemployment"] - 0.06) * 2
    ind["business_confidence"] += (conf_target - ind["business_confidence"]) * 0.3 + rng.gauss(0, 0.02)
    ind["business_confidence"] = max(0, min(1, ind["business_confidence"]))

    # Housing
    # Prices rise with GDP, fall with vacancy
    ind["price_index"] *= 1 + ind["gdp_growth"] * 0.8 - (ind["vacancy_rate"] - 0.05) * 0.5
    ind["price_index"] += rng.gauss(0, 0.02)
    ind["price_index"] = max(0.5, min(2.5, ind["price_index"]))

    # Vacancy: construction adds, migration absorbs
    ind["vacancy_rate"] += ind["construction_rate"] * 0.008 - ind["net_migration"] * 0.3
    ind["vacancy_rate"] += rng.gauss(0, 0.003)
    ind["vacancy_rate"] = max(0, min(0.20, ind["vacancy_rate"]))

    # Rent burden tracks price index and wages (inverse of GDP)
    ind["rent_burden"] = 0.20 + (ind["price_index"] - 0.8) * 0.15 - ind["gdp_growth"] * 1.5
    ind["rent_burden"] += rng.gauss(0, 0.01)
    ind["rent_burden"] = max(0.15, min(0.60, ind["rent_burden"]))

    # Construction: responds to prices (high price = more building), dampened by policy
    ind["construction_rate"] += (ind["price_index"] - 1.2) * 0.05 + rng.gauss(0, 0.02)
    ind["construction_rate"] = max(0, min(1, ind["construction_rate"]))

    # Migration
    # Net migration attracted by low unemployment, repelled by high housing costs
    ind["net_migration"] += (0.07 - ind["unemployment"]) * 0.01 - (ind["rent_burden"] - 0.30) * 0.02
    ind["net_migration"] += rng.gauss(0, 0.002)
    ind["net_migration"] = max(-0.03, min(0.06, ind["net_migration"]))

    # Diversity: ratchets up with migration (slowly, doesn't easily decrease)
    if ind["net_migration"] > 0:
        ind["diversity_index"] += ind["net_migration"] * 0.3
    ind["diversity_index"] += rng.gauss(0, 0.005)
    ind["diversity_index"] = max(0, min(1, ind["diversity_index"]))

    # Integration: improves with cohesion, degrades with rapid migration
    ind["integration_score"] += ind["social_cohesion"] * 0.02 - max(0, ind["net_migration"] - 0.01) * 0.8
    ind["integration_score"] += rng.gauss(0, 0.01)
    ind["integration_score"] = max(0, min(1, ind["integration_score"]))

    # Culture
    # Cultural spending: tracks GDP and public spending
    ind["cultural_spending"] += ind["gdp_growth"] * 0.5 + (ind["public_spending"] - 0.45) * 0.05
    ind["cultural_spending"] += rng.gauss(0, 0.01)
    ind["cultural_spending"] = max(0, min(1, ind["cultural_spending"]))

    # Social cohesion: eroded by inequality (unemployment, rent burden), boosted by integration
    ind["social_cohesion"] += ind["integration_score"] * 0.02 - ind["unemployment"] * 0.08 - (ind["rent_burden"] - 0.30) * 0.06
    ind["social_cohesion"] += rng.gauss(0, 0.01)
    ind["social_cohesion"] = max(0, min(1, ind["social_cohesion"]))

    # Media pluralism: slow drift
    ind["media_pluralism"] += rng.gauss(0, 0.008)
    ind["media_pluralism"] = max(0, min(1, ind["media_pluralism"]))

    # Governance
    ind["public_spending"] += rng.gauss(0, 0.005)
    ind["public_spending"] = max(0.25, min(0.65, ind["public_spending"]))

    # Corruption: mean-reverts slowly, worsens under low democratic quality
    ind["corruption_index"] += (0.15 - ind["corruption_index"]) * 0.05 + (0.7 - ind["democratic_quality"]) * 0.02
    ind["corruption_index"] += rng.gauss(0, 0.008)
    ind["corruption_index"] = max(0, min(1, ind["corruption_index"]))

    # Policy stability: eroded by events (handled in event coupling)
    ind["policy_stability"] += (0.70 - ind["policy_stability"]) * 0.1 + rng.gauss(0, 0.01)
    ind["policy_stability"] = max(0, min(1, ind["policy_stability"]))

    # Democratic quality: slow, tracks cohesion and media pluralism
    ind["democratic_quality"] += (ind["social_cohesion"] - 0.5) * 0.02 + (ind["media_pluralism"] - 0.5) * 0.01
    ind["democratic_quality"] += rng.gauss(0, 0.005)
    ind["democratic_quality"] = max(0, min(1, ind["democratic_quality"]))


# ── Environment → Agent coupling ─────────────────────────────────────────────

def environment_affect_agents(env: Environment, G: nx.Graph):
    """Apply macro-environment effects to individual agents' capital."""
    ind = env.indicators

    for node_id in G.nodes:
        agent = G.nodes[node_id]["agent"]
        cap = agent.capital
        hab = agent.habitus
        cls_rank = hab.current_class.rank  # 0=lower, 4=upper

        # ── Economic capital effects ─────────────────────────────────
        # GDP growth benefits everyone, proportional to existing capital
        gdp_effect = ind["gdp_growth"] * (0.3 + cap.economic * 0.7) * 0.5
        cap.economic += gdp_effect

        # Unemployment hits lower classes harder
        if ind["unemployment"] > 0.08:
            unemp_penalty = (ind["unemployment"] - 0.08) * (1 - cls_rank * 0.2) * 0.3
            cap.economic -= unemp_penalty

        # Inflation erodes savings, more for lower classes (less hedged)
        if ind["inflation"] > 0.03:
            infl_penalty = (ind["inflation"] - 0.03) * (1 - cls_rank * 0.15) * 0.2
            cap.economic -= infl_penalty

        # Rent burden: direct economic drain, inversely proportional to wealth
        if ind["rent_burden"] > 0.35:
            rent_hit = (ind["rent_burden"] - 0.35) * (1 - cap.economic * 0.5) * 0.15
            cap.economic -= rent_hit

        # Welfare floor
        from capital import EU_CONFIG
        cap.economic = max(EU_CONFIG["welfare_floor"], cap.economic)

        # ── Cultural capital effects ─────────────────────────────────
        # Cultural spending boosts cultural capital accumulation
        if ind["cultural_spending"] > 0.5:
            cult_boost = (ind["cultural_spending"] - 0.5) * 0.03
            # More benefit to those already culturally inclined
            cap.cultural += cult_boost * (0.5 + cap.cultural * 0.5)

        # Media pluralism promotes cultural capital for engaged agents
        if ind["media_pluralism"] > 0.6 and "media" in agent.interests:
            cap.cultural += (ind["media_pluralism"] - 0.6) * 0.02

        # ── Social capital effects ───────────────────────────────────
        # Social cohesion boosts everyone's social capital slightly
        cohesion_effect = (ind["social_cohesion"] - 0.5) * 0.02
        cap.social += cohesion_effect

        # Integration score helps cross-clan connected agents
        if ind["integration_score"] > 0.6:
            cap.social += (ind["integration_score"] - 0.6) * 0.01

        # ── Symbolic capital effects ─────────────────────────────────
        # Democratic quality: legitimizes existing symbolic capital
        if ind["democratic_quality"] > 0.7:
            cap.symbolic *= 1 + (ind["democratic_quality"] - 0.7) * 0.05
        # Corruption devalues legitimate symbolic capital
        if ind["corruption_index"] > 0.25:
            cap.symbolic *= 1 - (ind["corruption_index"] - 0.25) * 0.08

        # ── Habitus drift ────────────────────────────────────────────
        # Institutional trust tracks the environment's democratic quality
        hab.institutional_trust += (ind["democratic_quality"] - hab.institutional_trust) * 0.03

        cap.clamp()


# ── Agent → Environment feedback ─────────────────────────────────────────────

def agents_affect_environment(env: Environment, G: nx.Graph):
    """Aggregate agent states feed back into macro indicators."""
    agents = [G.nodes[n]["agent"] for n in G.nodes]
    n = len(agents) or 1
    ind = env.indicators

    # Average economic capital → business confidence
    avg_ec = sum(a.capital.economic for a in agents) / n
    ind["business_confidence"] += (avg_ec - 0.45) * 0.05

    # Average symbolic capital → democratic quality
    avg_sy = sum(a.capital.symbolic for a in agents) / n
    ind["democratic_quality"] += (avg_sy - 0.3) * 0.02

    # Average social cohesion ← opinion dispersion (many opposing opinions = low cohesion)
    all_opinions = []
    for a in agents:
        all_opinions.extend(a.opinion_state.values())
    if all_opinions:
        opinion_variance = sum(o * o for o in all_opinions) / len(all_opinions)
        ind["social_cohesion"] -= opinion_variance * 0.02

    # Clamp everything
    for k in ind:
        meta = INDICATOR_META.get(k)
        if meta:
            ind[k] = max(meta[1], min(meta[2], ind[k]))


# ── Event → Environment coupling ─────────────────────────────────────────────

EVENT_ENV_EFFECTS = {
    "election":         {"policy_stability": -0.05, "democratic_quality": 0.02},
    "scandal":          {"corruption_index": 0.05, "policy_stability": -0.08, "social_cohesion": -0.03},
    "development":      {"price_index": 0.05, "construction_rate": 0.08, "vacancy_rate": -0.01},
    "crisis":           {"gdp_growth": -0.015, "unemployment": 0.03, "business_confidence": -0.10},
    "protest":          {"social_cohesion": -0.05, "policy_stability": -0.06, "democratic_quality": 0.01},
    "festival":         {"social_cohesion": 0.03, "cultural_spending": 0.02},
    "tech_boom":        {"gdp_growth": 0.008, "business_confidence": 0.06, "price_index": 0.03},
    "policy_change":    {"policy_stability": -0.04},
    "education_reform": {"cultural_spending": 0.04, "policy_stability": -0.03},
    "housing_crisis":   {"price_index": 0.12, "rent_burden": 0.05, "social_cohesion": -0.04, "net_migration": -0.005},
    "cultural_event":   {"cultural_spending": 0.05, "social_cohesion": 0.02},
    "welfare_reform":   {"public_spending": 0.02, "policy_stability": -0.05, "social_cohesion": -0.02},
}


def event_affects_environment(env: Environment, event_type: str, intensity: float):
    """An event shifts environment indicators proportional to intensity."""
    effects = EVENT_ENV_EFFECTS.get(event_type, {})
    for key, delta in effects.items():
        scaled = delta * intensity
        env.indicators[key] = env.indicators.get(key, 0) + scaled
        meta = INDICATOR_META.get(key)
        if meta:
            env.indicators[key] = max(meta[1], min(meta[2], env.indicators[key]))


# ── Full tick ────────────────────────────────────────────────────────────────

def advance_environment(env: Environment, G: nx.Graph, years: int = 1,
                        seed: int | None = None) -> dict:
    """Advance the environment by N years with full agent coupling."""
    from economy import advance_economy_tick, economy_affect_capital, economy_from_environment, TECH_WAVES, compute_disruption
    from media import (
        evolve_media_landscape, media_affect_agent_opinion,
        media_affect_environment, environment_affect_media,
        update_algorithmic_bubble, compute_media_stats,
    )

    rng = random.Random(seed) if seed else random.Random()
    summaries = []

    # Access or create media landscape (stored on env)
    if not hasattr(env, "media_landscape"):
        from media import create_media_landscape
        env.media_landscape = create_media_landscape(seed)
    ml = env.media_landscape

    for _ in range(years):
        env.year += 1
        _evolve_indicators(env, rng)

        # ── Economy tick: advance tech, recompute disruption ───────
        agents = [G.nodes[n]["agent"] for n in G.nodes]
        agent_econs = [a.economy for a in agents if a.economy]
        econ_summary = advance_economy_tick(agent_econs)

        # Economy → capital coupling (with transaction recording)
        from transactions import LEDGER, TxType
        LEDGER.clear()

        for a in agents:
            if a.economy:
                old_income = a.economy.income
                old_disp = a.economy.displacement_risk
                economy_from_environment(a.economy, env.indicators)
                economy_affect_capital(a.capital, a.economy)
                # Record displacement transactions
                if abs(a.economy.displacement_risk - old_disp) > 0.005:
                    LEDGER.record(TxType.TASK_DISPLACEMENT, "AI/ML + Robotics", "",
                        a.name, a.id, a.economy.displacement_risk - old_disp,
                        f"displacement {old_disp:.1%} → {a.economy.displacement_risk:.1%} ({a.occupation})")

        # Tech disruption feeds into unemployment
        avg_disp = econ_summary.get("avg_displacement_risk", 0)
        env.indicators["unemployment"] += avg_disp * 0.03
        env.indicators["unemployment"] = max(0.02, min(0.25, env.indicators["unemployment"]))
        # AI boosts GDP growth
        from economy import TECH_WAVES as TW
        ai_adoption = TW.get("ai_ml")
        if ai_adoption:
            env.indicators["gdp_growth"] += ai_adoption.adoption * 0.005
            env.indicators["gdp_growth"] = max(-0.05, min(0.08, env.indicators["gdp_growth"]))

        # ── Media tick: evolve landscape, affect agents ────────────
        evolve_media_landscape(ml, rng)
        media_affect_environment(ml, env.indicators)
        environment_affect_media(ml, env.indicators)

        # Media → agent opinion effects
        for node_id in G.nodes:
            agent = G.nodes[node_id]["agent"]
            if agent.media and agent.opinion_state:
                # Gather neighbor opinions for social media filtering
                neighbor_ops: dict[str, list[float]] = {}
                for nid in G.neighbors(node_id):
                    na = G.nodes[nid]["agent"]
                    for t, o in na.opinion_state.items():
                        neighbor_ops.setdefault(t, []).append(o)

                deltas = media_affect_agent_opinion(
                    agent.opinion_state, agent.media, ml,
                    agent.politics.numeric, agent.openness,
                    neighbor_ops, rng,
                )
                for topic, d in deltas.items():
                    if abs(d) > 0.005:
                        media_src = "social media" if agent.media.social_exposure > 0.4 else "mass media" if agent.media.mass_exposure > 0.4 else "print media"
                        LEDGER.record(TxType.MEDIA_EFFECT, media_src, "",
                            agent.name, agent.id, d,
                            f"topic: {topic} | opinion {agent.opinion_state[topic]:.2f} → {max(-1,min(1,agent.opinion_state[topic]+d)):.2f}")
                    agent.opinion_state[topic] = max(-1, min(1, agent.opinion_state[topic] + d))

                # Update algorithmic bubble
                old_bubble = agent.media.algorithmic_bubble
                update_algorithmic_bubble(agent.media, agent.opinion_state)
                if agent.media.algorithmic_bubble - old_bubble > 0.005:
                    LEDGER.record(TxType.ECHO_CHAMBER, "social media", "",
                        agent.name, agent.id, agent.media.algorithmic_bubble - old_bubble,
                        f"bubble {old_bubble:.2f} → {agent.media.algorithmic_bubble:.2f}")

        # ── Health tick: evolve indicators, affect agents ────────────
        from health import (
            evolve_health_indicators, evolve_agent_health,
            health_affect_economy, health_affect_capital, compute_health_stats,
        )
        from institutions import (
            evolve_institution_indicators, evolve_institutional_profile,
            institutions_affect_capital, institutions_affect_economy,
            compute_institution_stats,
        )

        evolve_health_indicators(env.indicators, rng)
        evolve_institution_indicators(env.indicators, rng)

        health_indicators = {k: env.indicators.get(k, 0) for k in
                           ("healthcare_access", "life_expectancy_index",
                            "mental_health_index", "health_inequality")}

        for a in agents:
            # Health evolution
            if a.health:
                old_physical = a.health.physical_health
                old_chronic = a.health.chronic_condition
                disp_risk = a.economy.displacement_risk if a.economy else 0
                evolve_agent_health(
                    a.health, a.age, a.habitus.current_class.rank,
                    a.capital.economic, a.capital.social,
                    disp_risk, a.satisfaction, health_indicators, rng,
                )
                health_affect_capital(a.health, a.capital)
                health_affect_economy(a.health, a.economy)
                if not old_chronic and a.health.chronic_condition:
                    LEDGER.record(TxType.CHRONIC_ONSET, f"age {a.age} / {a.habitus.current_class.value}", "",
                        a.name, a.id, -0.2,
                        f"chronic condition onset | physical {old_physical:.2f} → {a.health.physical_health:.2f}")
                elif abs(a.health.physical_health - old_physical) > 0.02:
                    LEDGER.record(TxType.HEALTH_CHANGE, "health system", "",
                        a.name, a.id, a.health.physical_health - old_physical,
                        f"physical {old_physical:.2f} → {a.health.physical_health:.2f} | stress {a.health.stress_level:.2f}")

            # Institutional evolution
            if a.institutions:
                old_n = len(a.institutions.memberships)
                evolve_institutional_profile(
                    a.institutions, a.age, a.habitus.current_class.rank,
                    a.habitus.education_track.value, rng,
                )
                institutions_affect_capital(a.institutions, a.capital)
                institutions_affect_economy(a.institutions, a.economy)
                for m in a.institutions.memberships:
                    if m.years_active == 0 and len(a.institutions.memberships) > old_n:
                        LEDGER.record(TxType.TIE_FORMED, a.name, a.id,
                            m.institution_name, "", 0.1,
                            f"joined {m.institution_name} ({m.institution_type.value})")
                    if m.economic_interest > 0.15:
                        LEDGER.record(TxType.INSTITUTIONAL_CAP, m.institution_name, "",
                            a.name, a.id, m.economic_interest * 0.01,
                            f"{m.institution_name} | econ interest {m.economic_interest:.0%}{'  LEADER' if m.leadership_role else ''}")

        # ── Standard environment ↔ agent coupling ─────────────────
        # Record env→agent effects for significant cases
        for node_id in G.nodes:
            a = G.nodes[node_id]["agent"]
            old_econ = a.capital.economic
            old_sym = a.capital.symbolic
        environment_affect_agents(env, G)
        # Sample a few env→agent effects for the ledger
        sample_agents = agents[:50]  # record first 50 to keep ledger manageable
        for a in sample_agents:
            econ_delta = a.capital.economic - (old_econ if a == sample_agents[0] else a.capital.economic)
            if abs(a.capital.economic - 0.5) > 0.3:
                LEDGER.record(TxType.ENV_AGENT, "GDP + unemployment", "",
                    a.name, a.id, env.indicators.get("gdp_growth", 0),
                    f"econ capital: {a.capital.economic:.3f} | class: {a.habitus.current_class.value}")
        agents_affect_environment(env, G)

        # Age agents by 1 year
        from capital import life_phase_from_age, apply_lifecycle
        for node_id in G.nodes:
            agent = G.nodes[node_id]["agent"]
            agent.age += 1
            new_phase = life_phase_from_age(agent.age)
            if new_phase != agent.life_phase:
                agent.life_phase = new_phase
                agent.capital = apply_lifecycle(agent.capital, new_phase)

        env.record()
        summaries.append(env.snapshot())

    # Collect stats
    all_media = [G.nodes[n]["agent"].media for n in G.nodes
                 if G.nodes[n]["agent"].media]
    media_stats = compute_media_stats(ml, all_media) if all_media else {}
    all_health = [a.health for a in agents if a.health]
    health_stats = compute_health_stats(all_health) if all_health else {}
    all_inst = [a.institutions for a in agents if a.institutions]
    inst_stats = compute_institution_stats(all_inst) if all_inst else {}

    return {
        "years_advanced": years,
        "current_year": env.year,
        "current": env.snapshot(),
        "summaries": summaries,
        "economy": econ_summary if years > 0 else {},
        "media": media_stats,
        "health": health_stats,
        "institutions": inst_stats,
        "transactions": LEDGER.summary(),
    }
