"""
CivGraph -- Task-based economic model with technological disruption.

Each agent has an occupation composed of concrete tasks. Each task sits on
three axes (cognitive vs manual, routine vs creative, interpersonal vs solo)
that determine its vulnerability to successive technology waves.

Technology waves follow logistic S-curve adoption:
  1. Mechanization   (historical, fully diffused)
  2. Digitization    (1990s-2020s, nearly saturated)
  3. AI / ML         (2020s+, rapid early-mid adoption)
  4. Robotics        (physical automation, early adoption)

Follows the Autor (2003) task-content framework extended for AI per
Acemoglu & Restrepo (2019) and Eloundou et al. (2023, GPT-4 exposure).

Calibrated to Western European labour market (~2020s baseline).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════════════════
# TASK DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Task:
    """A discrete work activity within an occupation."""
    name: str
    cognitive: float       # 0 = fully manual, 1 = fully cognitive
    routine: float         # 0 = fully creative/non-routine, 1 = fully routine
    interpersonal: float   # 0 = solo work, 1 = high interpersonal
    time_share: float      # fraction of working time (0-1)
    base_value: float      # relative economic output (0-1 scale)


# ── Occupation → task portfolio ─────────────────────────────────────────────
# Each occupation is decomposed into 3-5 concrete tasks that sum to ~1.0
# time_share.  The cognitive/routine/interpersonal axes drive automation
# exposure differently per technology wave.

OCCUPATION_TASKS: dict[str, list[Task]] = {
    "mayor": [
        Task("public_speaking",          0.7, 0.2, 0.95, 0.25, 0.8),
        Task("policy_negotiation",       0.8, 0.2, 0.90, 0.30, 0.9),
        Task("administrative_oversight", 0.6, 0.7, 0.50, 0.25, 0.5),
        Task("constituency_engagement",  0.5, 0.3, 0.95, 0.20, 0.6),
    ],
    "council_member": [
        Task("legislative_drafting",     0.8, 0.5, 0.30, 0.25, 0.7),
        Task("committee_deliberation",   0.7, 0.3, 0.85, 0.30, 0.7),
        Task("constituent_casework",     0.5, 0.6, 0.80, 0.25, 0.5),
        Task("campaign_outreach",        0.4, 0.3, 0.90, 0.20, 0.4),
    ],
    "business_owner": [
        Task("strategic_planning",       0.9, 0.2, 0.40, 0.20, 0.9),
        Task("financial_management",     0.8, 0.6, 0.30, 0.20, 0.7),
        Task("employee_management",      0.6, 0.3, 0.85, 0.25, 0.6),
        Task("client_relations",         0.5, 0.3, 0.90, 0.20, 0.7),
        Task("operations_oversight",     0.5, 0.7, 0.40, 0.15, 0.5),
    ],
    "developer": [
        Task("software_architecture",    0.95, 0.15, 0.30, 0.20, 0.9),
        Task("coding_implementation",    0.90, 0.40, 0.15, 0.35, 0.8),
        Task("code_review",             0.85, 0.30, 0.50, 0.15, 0.6),
        Task("debugging",               0.90, 0.25, 0.20, 0.20, 0.7),
        Task("documentation",           0.70, 0.65, 0.10, 0.10, 0.3),
    ],
    "lawyer": [
        Task("legal_research",          0.90, 0.50, 0.10, 0.25, 0.7),
        Task("contract_drafting",       0.85, 0.60, 0.15, 0.25, 0.7),
        Task("courtroom_advocacy",      0.80, 0.15, 0.95, 0.20, 0.9),
        Task("client_counseling",       0.70, 0.20, 0.90, 0.20, 0.8),
        Task("compliance_review",       0.75, 0.75, 0.20, 0.10, 0.5),
    ],
    "doctor": [
        Task("patient_diagnosis",       0.90, 0.30, 0.80, 0.30, 0.9),
        Task("treatment_planning",      0.85, 0.35, 0.50, 0.20, 0.8),
        Task("physical_examination",    0.50, 0.40, 0.90, 0.20, 0.7),
        Task("medical_record_keeping",  0.60, 0.80, 0.10, 0.15, 0.3),
        Task("patient_communication",   0.60, 0.20, 0.95, 0.15, 0.6),
    ],
    "journalist": [
        Task("investigative_research",  0.85, 0.20, 0.50, 0.25, 0.8),
        Task("writing_editing",         0.80, 0.35, 0.15, 0.30, 0.7),
        Task("source_interviewing",     0.60, 0.15, 0.95, 0.25, 0.7),
        Task("fact_checking",           0.75, 0.70, 0.10, 0.15, 0.4),
        Task("social_media_publishing", 0.50, 0.55, 0.30, 0.05, 0.3),
    ],
    "professor": [
        Task("original_research",       0.95, 0.10, 0.20, 0.30, 0.9),
        Task("lecture_preparation",     0.85, 0.40, 0.15, 0.15, 0.5),
        Task("classroom_teaching",      0.70, 0.30, 0.90, 0.25, 0.7),
        Task("student_mentoring",       0.65, 0.15, 0.95, 0.15, 0.6),
        Task("grading_assessment",      0.60, 0.75, 0.20, 0.15, 0.3),
    ],
    "banker": [
        Task("credit_risk_analysis",    0.85, 0.60, 0.20, 0.25, 0.8),
        Task("portfolio_management",    0.80, 0.45, 0.30, 0.25, 0.8),
        Task("client_advisory",         0.70, 0.25, 0.90, 0.25, 0.7),
        Task("regulatory_compliance",   0.75, 0.80, 0.15, 0.15, 0.5),
        Task("transaction_processing",  0.50, 0.90, 0.10, 0.10, 0.3),
    ],
    "police_chief": [
        Task("strategic_command",       0.75, 0.25, 0.70, 0.25, 0.8),
        Task("crisis_management",       0.65, 0.10, 0.85, 0.20, 0.9),
        Task("personnel_management",    0.55, 0.40, 0.80, 0.20, 0.6),
        Task("report_processing",       0.50, 0.80, 0.15, 0.15, 0.3),
        Task("community_relations",     0.50, 0.25, 0.90, 0.20, 0.6),
    ],
    "union_leader": [
        Task("collective_bargaining",   0.75, 0.20, 0.95, 0.30, 0.8),
        Task("member_organizing",       0.50, 0.25, 0.90, 0.25, 0.7),
        Task("grievance_handling",      0.65, 0.50, 0.80, 0.20, 0.5),
        Task("public_advocacy",         0.60, 0.20, 0.90, 0.15, 0.6),
        Task("administrative_duties",   0.40, 0.80, 0.20, 0.10, 0.3),
    ],
    "pastor": [
        Task("sermon_preparation",      0.80, 0.20, 0.10, 0.20, 0.6),
        Task("worship_leading",         0.50, 0.30, 0.95, 0.25, 0.7),
        Task("pastoral_counseling",     0.65, 0.10, 0.95, 0.30, 0.8),
        Task("community_organizing",    0.45, 0.30, 0.90, 0.20, 0.5),
        Task("administrative_tasks",    0.40, 0.80, 0.20, 0.05, 0.2),
    ],
    "nonprofit_director": [
        Task("fundraising",             0.65, 0.25, 0.85, 0.25, 0.8),
        Task("programme_design",        0.80, 0.25, 0.40, 0.25, 0.7),
        Task("stakeholder_management",  0.60, 0.30, 0.90, 0.25, 0.7),
        Task("grant_writing",           0.80, 0.50, 0.15, 0.15, 0.6),
        Task("impact_reporting",        0.65, 0.65, 0.20, 0.10, 0.4),
    ],
    "lobbyist": [
        Task("policy_analysis",         0.85, 0.40, 0.15, 0.20, 0.7),
        Task("relationship_cultivation",0.50, 0.10, 0.95, 0.30, 0.9),
        Task("strategic_messaging",     0.80, 0.25, 0.50, 0.25, 0.8),
        Task("research_briefings",      0.75, 0.55, 0.20, 0.15, 0.5),
        Task("event_coordination",      0.40, 0.50, 0.70, 0.10, 0.4),
    ],
    "engineer": [
        Task("technical_design",        0.90, 0.25, 0.30, 0.25, 0.9),
        Task("calculations_modeling",   0.85, 0.55, 0.10, 0.25, 0.7),
        Task("site_inspection",         0.40, 0.40, 0.50, 0.15, 0.5),
        Task("project_management",      0.65, 0.40, 0.70, 0.20, 0.6),
        Task("regulatory_documentation",0.70, 0.75, 0.10, 0.15, 0.4),
    ],
    "restaurateur": [
        Task("menu_creation",           0.60, 0.15, 0.20, 0.15, 0.7),
        Task("food_preparation",        0.30, 0.40, 0.30, 0.25, 0.6),
        Task("customer_service",        0.30, 0.30, 0.95, 0.25, 0.6),
        Task("supply_management",       0.50, 0.70, 0.40, 0.20, 0.4),
        Task("staff_coordination",      0.45, 0.40, 0.80, 0.15, 0.5),
    ],
    "artist": [
        Task("creative_production",     0.70, 0.05, 0.10, 0.40, 0.9),
        Task("exhibition_curation",     0.65, 0.20, 0.50, 0.20, 0.6),
        Task("arts_networking",         0.40, 0.15, 0.90, 0.20, 0.5),
        Task("self_promotion",          0.50, 0.30, 0.60, 0.15, 0.4),
        Task("material_sourcing",       0.20, 0.50, 0.30, 0.05, 0.2),
    ],
    "contractor": [
        Task("project_estimation",      0.70, 0.45, 0.40, 0.15, 0.7),
        Task("physical_construction",   0.15, 0.50, 0.40, 0.30, 0.6),
        Task("crew_supervision",        0.40, 0.35, 0.85, 0.25, 0.6),
        Task("blueprint_interpretation",0.65, 0.60, 0.10, 0.15, 0.5),
        Task("permit_management",       0.55, 0.75, 0.40, 0.15, 0.3),
    ],
    "realtor": [
        Task("market_analysis",         0.75, 0.50, 0.10, 0.20, 0.7),
        Task("property_showings",       0.30, 0.35, 0.90, 0.30, 0.6),
        Task("deal_negotiation",        0.70, 0.20, 0.95, 0.25, 0.8),
        Task("paperwork_processing",    0.50, 0.85, 0.15, 0.15, 0.3),
        Task("client_prospecting",      0.40, 0.30, 0.85, 0.10, 0.5),
    ],
    "consultant": [
        Task("problem_diagnosis",       0.90, 0.15, 0.50, 0.25, 0.9),
        Task("data_analysis",           0.85, 0.50, 0.15, 0.25, 0.7),
        Task("presentation_delivery",   0.70, 0.25, 0.85, 0.20, 0.7),
        Task("report_writing",          0.75, 0.50, 0.10, 0.20, 0.5),
        Task("stakeholder_interviews",  0.60, 0.20, 0.90, 0.10, 0.6),
    ],
}

# Fallback for any occupation not listed
_DEFAULT_TASKS = [
    Task("core_work",        0.50, 0.40, 0.40, 0.40, 0.6),
    Task("administration",   0.55, 0.75, 0.20, 0.25, 0.4),
    Task("communication",    0.50, 0.30, 0.80, 0.20, 0.5),
    Task("planning",         0.70, 0.35, 0.30, 0.15, 0.5),
]


def get_tasks_for_occupation(occupation: str) -> list[Task]:
    return OCCUPATION_TASKS.get(occupation, _DEFAULT_TASKS)


# ══════════════════════════════════════════════════════════════════════════════
# TECHNOLOGY WAVES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TechWave:
    """A technology wave with logistic adoption and task-displacement profile."""
    name: str
    adoption: float           # current 0-1 diffusion level
    growth_rate: float        # logistic growth rate per year
    ceiling: float            # maximum adoption (0-1)
    year_introduced: int      # when the wave started
    # Displacement profile: how much this tech displaces each task quadrant
    # Indexed by (cognitive, routine): (low,low), (low,high), (high,low), (high,high)
    manual_routine: float     # low cognitive, high routine
    manual_creative: float    # low cognitive, low routine
    cognitive_routine: float  # high cognitive, high routine
    cognitive_creative: float # high cognitive, low routine
    # Interpersonal discount: how much interpersonal tasks resist automation
    interpersonal_shield: float  # 0-1: 1.0 means interpersonal fully protects
    # Productivity boost to surviving workers
    productivity_boost: float    # multiplier on remaining human output
    # New task creation rate (compensating new jobs)
    new_task_creation: float     # 0-1 how many new tasks this tech creates


# Current state of technology waves (baseline ~year 0 of simulation)
TECH_WAVES: dict[str, TechWave] = {
    "mechanization": TechWave(
        name="Mechanization",
        adoption=0.95,
        growth_rate=0.01,
        ceiling=0.98,
        year_introduced=-200,     # ~1820s
        manual_routine=0.85,      # assembly lines, farming machines
        manual_creative=0.15,     # crafts, construction still human
        cognitive_routine=0.05,   # barely affects cognitive work
        cognitive_creative=0.0,
        interpersonal_shield=0.9,
        productivity_boost=1.8,
        new_task_creation=0.30,   # created many new industrial jobs
    ),
    "digitization": TechWave(
        name="Digitization",
        adoption=0.82,
        growth_rate=0.03,
        ceiling=0.95,
        year_introduced=-30,      # ~1990s
        manual_routine=0.20,      # barcode scanners, automated checkout
        manual_creative=0.05,
        cognitive_routine=0.70,   # spreadsheets, databases, ERP
        cognitive_creative=0.10,  # creative tools assist but don't replace
        interpersonal_shield=0.7,
        productivity_boost=1.5,
        new_task_creation=0.40,   # created IT, data, digital marketing jobs
    ),
    "ai_ml": TechWave(
        name="AI / Machine Learning",
        adoption=0.18,
        growth_rate=0.12,         # rapid adoption
        ceiling=0.85,
        year_introduced=-3,       # ~2020s
        manual_routine=0.10,      # minimal direct physical impact
        manual_creative=0.05,
        cognitive_routine=0.75,   # data entry, basic analysis, translation
        cognitive_creative=0.45,  # writing, coding, design, diagnosis
        interpersonal_shield=0.6, # AI chatbots reduce some interpersonal shield
        productivity_boost=1.8,
        new_task_creation=0.25,   # prompt engineering, AI oversight, etc.
    ),
    "robotics": TechWave(
        name="Advanced Robotics",
        adoption=0.08,
        growth_rate=0.06,
        ceiling=0.70,
        year_introduced=-5,
        manual_routine=0.60,      # warehouse, logistics, manufacturing
        manual_creative=0.25,     # construction robots, surgical robots
        cognitive_routine=0.10,
        cognitive_creative=0.02,
        interpersonal_shield=0.85,
        productivity_boost=1.4,
        new_task_creation=0.15,   # robot maintenance, programming
    ),
}


def advance_tech_adoption(tech: TechWave) -> float:
    """Logistic S-curve: advance adoption by one year. Returns new adoption."""
    # Logistic growth: dA/dt = r * A * (1 - A/ceiling)
    delta = tech.growth_rate * tech.adoption * (1 - tech.adoption / tech.ceiling)
    tech.adoption = min(tech.ceiling, tech.adoption + delta)
    return tech.adoption


# ══════════════════════════════════════════════════════════════════════════════
# AGENT ECONOMIC STATE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentEconomy:
    """Per-agent economic state derived from their task portfolio."""
    tasks: list[Task]
    income: float = 0.5                 # 0-1 normalized income
    displacement_risk: float = 0.0      # 0-1 automation exposure
    productivity: float = 1.0           # output multiplier
    tech_adaptation: float = 0.5        # ability to adapt (retraining capacity)
    task_disruption: dict[str, float] = field(default_factory=dict)  # per-task disruption

    def to_dict(self) -> dict:
        return {
            "income": round(self.income, 3),
            "displacement_risk": round(self.displacement_risk, 3),
            "productivity": round(self.productivity, 3),
            "tech_adaptation": round(self.tech_adaptation, 3),
            "tasks": [
                {
                    "name": t.name,
                    "cognitive": t.cognitive,
                    "routine": t.routine,
                    "interpersonal": t.interpersonal,
                    "time_share": t.time_share,
                    "disruption": round(self.task_disruption.get(t.name, 0.0), 3),
                }
                for t in self.tasks
            ],
        }


def generate_agent_economy(
    occupation: str,
    education_track_value: str,
    age: int,
    class_rank: int,
    rng: random.Random | None = None,
) -> AgentEconomy:
    """Initialize economic state for an agent based on occupation and traits."""
    r = rng or random
    tasks = get_tasks_for_occupation(occupation)

    # Tech adaptation capacity: younger + better educated = more adaptable
    age_factor = max(0.1, 1.0 - (age - 25) / 60)  # peaks at 25, declines
    edu_factor = {"vocational": 0.3, "applied": 0.5, "academic": 0.7, "elite": 0.9}.get(
        education_track_value, 0.5
    )
    tech_adaptation = min(1.0, age_factor * 0.5 + edu_factor * 0.4 + r.gauss(0, 0.08))
    tech_adaptation = max(0.05, tech_adaptation)

    # Base income from task portfolio value + class position
    base_output = sum(t.base_value * t.time_share for t in tasks)
    class_mult = 0.6 + class_rank * 0.15  # lower=0.6, upper=1.2
    income = min(1.0, base_output * class_mult + r.gauss(0, 0.05))
    income = max(0.1, income)

    return AgentEconomy(
        tasks=tasks,
        income=income,
        productivity=1.0,
        tech_adaptation=tech_adaptation,
    )


# ══════════════════════════════════════════════════════════════════════════════
# DISRUPTION COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════

def _task_displacement(task: Task, tech: TechWave) -> float:
    """How much a single technology wave displaces a single task (0-1)."""
    # Determine task quadrant weights
    cog = task.cognitive
    rout = task.routine
    inter = task.interpersonal

    # Weighted displacement from quadrant profile
    displacement = (
        (1 - cog) * rout       * tech.manual_routine +
        (1 - cog) * (1 - rout) * tech.manual_creative +
        cog       * rout       * tech.cognitive_routine +
        cog       * (1 - rout) * tech.cognitive_creative
    )

    # Interpersonal tasks are harder to automate
    interpersonal_protection = inter * tech.interpersonal_shield
    displacement *= (1 - interpersonal_protection * 0.6)

    # Scale by adoption level
    return displacement * tech.adoption


def compute_disruption(econ: AgentEconomy, tech_waves: dict[str, TechWave]) -> None:
    """Update an agent's displacement risk and income based on current tech state."""
    total_displacement = 0.0
    total_productivity_boost = 1.0
    total_new_tasks = 0.0
    econ.task_disruption.clear()

    for task in econ.tasks:
        task_disp = 0.0
        task_prod = 1.0
        for tech in tech_waves.values():
            d = _task_displacement(task, tech)
            # Technologies compound but saturate
            task_disp = 1 - (1 - task_disp) * (1 - d)
            task_prod *= (1 + (tech.productivity_boost - 1) * tech.adoption * 0.3)

        # Agent's adaptation reduces displacement
        adapted_disp = task_disp * (1 - econ.tech_adaptation * 0.4)
        econ.task_disruption[task.name] = adapted_disp
        total_displacement += adapted_disp * task.time_share
        total_productivity_boost *= task_prod ** task.time_share

    # New task creation offsets some displacement
    for tech in tech_waves.values():
        total_new_tasks += tech.new_task_creation * tech.adoption * 0.15

    # Net displacement
    econ.displacement_risk = max(0, min(1.0, total_displacement - total_new_tasks))

    # Income = base output × productivity × (1 - net displacement)
    base_output = sum(t.base_value * t.time_share for t in econ.tasks)
    econ.productivity = min(3.0, total_productivity_boost)
    econ.income = max(0.05, min(1.0,
        base_output * econ.productivity * (1 - econ.displacement_risk * 0.6)
    ))


# ══════════════════════════════════════════════════════════════════════════════
# AGGREGATE ECONOMY
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TechState:
    """Snapshot of all technology waves for serialization."""
    waves: dict[str, dict]

    def to_dict(self) -> dict:
        return self.waves


def get_tech_state() -> TechState:
    """Current state of all technology waves."""
    return TechState(waves={
        name: {
            "name": tw.name,
            "adoption": round(tw.adoption, 3),
            "growth_rate": tw.growth_rate,
            "ceiling": tw.ceiling,
        }
        for name, tw in TECH_WAVES.items()
    })


def advance_economy_tick(agents_econ: list[AgentEconomy]) -> dict:
    """Advance technology by one year and recompute all agent disruption.

    Returns summary statistics.
    """
    # Advance tech adoption
    for tech in TECH_WAVES.values():
        advance_tech_adoption(tech)

    # Recompute each agent
    total_income = 0.0
    total_disp = 0.0
    disp_by_occ: dict[str, list[float]] = {}
    income_by_occ: dict[str, list[float]] = {}

    for econ in agents_econ:
        compute_disruption(econ, TECH_WAVES)
        total_income += econ.income
        total_disp += econ.displacement_risk

    n = len(agents_econ) or 1

    return {
        "tech_state": get_tech_state().to_dict(),
        "avg_income": round(total_income / n, 3),
        "avg_displacement_risk": round(total_disp / n, 3),
    }


def economy_affect_capital(agent_capital, agent_economy: AgentEconomy):
    """Income from task-based economy feeds into economic capital."""
    # Blend task-based income into economic capital
    # Income represents earning power; displacement reduces it
    income_effect = (agent_economy.income - 0.5) * 0.08
    disp_penalty = agent_economy.displacement_risk * 0.04
    agent_capital.economic += income_effect - disp_penalty
    agent_capital.economic = max(0.15, min(1.0, agent_capital.economic))


def economy_from_environment(agent_economy: AgentEconomy, env_indicators: dict):
    """Macro-environment affects individual economic outcomes."""
    # GDP growth boosts income
    gdp = env_indicators.get("gdp_growth", 0.018)
    agent_economy.income *= (1 + gdp * 0.5)
    # Unemployment risk increases displacement perception
    unemp = env_indicators.get("unemployment", 0.065)
    if unemp > 0.08:
        agent_economy.displacement_risk += (unemp - 0.08) * 0.3
    agent_economy.income = max(0.05, min(1.0, agent_economy.income))
    agent_economy.displacement_risk = max(0, min(1.0, agent_economy.displacement_risk))
