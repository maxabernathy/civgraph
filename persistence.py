"""
CivGraph -- Persistence: save, load, and export simulation state.

Save format: gzip-compressed JSON (.civgraph.json.gz)
  - Full-precision agent state (not rounded like to_dict)
  - Graph topology (edges with weights and types)
  - Environment indicators + history
  - Emergence composites + history (agent_scores pruned for old snapshots)
  - Media landscape, tech waves, event history
  - Format version for forward compatibility

Export formats:
  - CSV bundle (ZIP): flat tables for R, Excel, Python pandas
  - JSON (uncompressed, pretty-printed): for programmatic access
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

FORMAT_VERSION = 1


# ══════════════════════════════════════════════════════════════════════════════
# SERIALIZATION (Python objects → dicts)
# ══════════════════════════════════════════════════════════════════════════════

def _serialize_agent(agent) -> dict:
    """Serialize an Agent to a dict with full precision (not rounded)."""
    d = {
        "id": agent.id,
        "name": agent.name,
        "clan": agent.clan,
        "district": agent.district,
        "occupation": agent.occupation,
        "interests": agent.interests,
        "politics": agent.politics.value,
        "age": agent.age,
        "life_phase": agent.life_phase.value,
        "openness": agent.openness,
        "assertiveness": agent.assertiveness,
        "loyalty": agent.loyalty,
        "generation": agent.generation,
        "parent_id": agent.parent_id,
        "opinion_state": dict(agent.opinion_state),
        "norms": dict(agent.norms),
        "satisfaction": agent.satisfaction,
        "emergence_score": agent.emergence_score,
    }

    # Capital (full precision)
    d["capital"] = {
        "economic": agent.capital.economic,
        "cultural": agent.capital.cultural,
        "social": agent.capital.social,
        "symbolic": agent.capital.symbolic,
    }

    # Habitus
    d["habitus"] = {
        "origin_class": agent.habitus.origin_class.value,
        "current_class": agent.habitus.current_class.value,
        "education_track": agent.habitus.education_track.value,
        "cultural_taste": agent.habitus.cultural_taste,
        "risk_tolerance": agent.habitus.risk_tolerance,
        "institutional_trust": agent.habitus.institutional_trust,
        "class_awareness": agent.habitus.class_awareness,
        "aspiration_gap": agent.habitus.aspiration_gap,
    }

    # Economy
    if agent.economy:
        d["economy"] = {
            "income": agent.economy.income,
            "displacement_risk": agent.economy.displacement_risk,
            "productivity": agent.economy.productivity,
            "tech_adaptation": agent.economy.tech_adaptation,
            "task_disruption": dict(agent.economy.task_disruption),
        }
    else:
        d["economy"] = None

    # Media
    if agent.media:
        d["media"] = {
            "print_exposure": agent.media.print_exposure,
            "mass_exposure": agent.media.mass_exposure,
            "social_exposure": agent.media.social_exposure,
            "media_literacy": agent.media.media_literacy,
            "algorithmic_bubble": agent.media.algorithmic_bubble,
        }
    else:
        d["media"] = None

    # Health
    if agent.health:
        d["health"] = {
            "physical_health": agent.health.physical_health,
            "mental_health": agent.health.mental_health,
            "healthcare_access": agent.health.healthcare_access,
            "chronic_condition": agent.health.chronic_condition,
            "health_literacy": agent.health.health_literacy,
            "work_capacity": agent.health.work_capacity,
            "stress_level": agent.health.stress_level,
            "disability": agent.health.disability,
        }
    else:
        d["health"] = None

    # Institutions
    if agent.institutions:
        d["institutions"] = {
            "memberships": [
                {
                    "type": m.institution_type.value,
                    "name": m.institution_name,
                    "years_active": m.years_active,
                    "leadership": m.leadership_role,
                    "economic_interest": m.economic_interest,
                }
                for m in agent.institutions.memberships
            ],
            "skill_currency": agent.institutions.skill_currency,
            "lifelong_learning": agent.institutions.lifelong_learning,
            "civic_participation": agent.institutions.civic_participation,
        }
    else:
        d["institutions"] = None

    return d


def _serialize_graph(G: nx.Graph) -> dict:
    """Serialize the full graph to a dict."""
    nodes = []
    for nid in G.nodes:
        agent = G.nodes[nid]["agent"]
        nodes.append(_serialize_agent(agent))

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "weight": data.get("weight", 0.5),
            "rel": data.get("rel", "unknown"),
        })

    return {"nodes": nodes, "edges": edges}


def _serialize_environment(env) -> dict:
    """Serialize Environment state."""
    return {
        "year": env.year,
        "indicators": dict(env.indicators),
        "history": list(env.history),
        "shocks": list(env.shocks),
    }


def _serialize_emergence(tracker) -> dict:
    """Serialize EmergenceTracker, pruning agent_scores for old snapshots."""
    history = []
    for i, snap in enumerate(tracker.history):
        entry = {
            "year": snap.year,
            "composites": dict(snap.composites),
            "coupled_composites": dict(snap.coupled_composites),
            "early_warnings": snap.early_warnings,
        }
        # Keep agent_scores only for the last 2 snapshots
        if i >= len(tracker.history) - 2:
            entry["agent_scores"] = snap.agent_scores
        else:
            entry["agent_scores"] = None
        history.append(entry)
    return {"history": history}


def _serialize_media(media) -> dict:
    """Serialize MediaLandscape."""
    if media is None:
        return None
    return media.to_dict()


def _serialize_tech_waves() -> dict:
    """Serialize current tech wave state."""
    from economy import TECH_WAVES
    result = {}
    for name, tw in TECH_WAVES.items():
        result[name] = {
            "adoption": tw.adoption,
            "growth_rate": tw.growth_rate,
            "ceiling": tw.ceiling,
        }
    return result


# ══════════════════════════════════════════════════════════════════════════════
# DESERIALIZATION (dicts → Python objects)
# ══════════════════════════════════════════════════════════════════════════════

def _deserialize_agent(d: dict):
    """Reconstruct an Agent from a saved dict."""
    from model import Agent, PoliticalLeaning
    from capital import Capital, Habitus, SocialClass, EducationTrack, LifePhase
    from economy import AgentEconomy, get_tasks_for_occupation
    from media import MediaConsumption
    from health import AgentHealth
    from institutions import InstitutionalProfile, Membership, InstitutionType

    # Capital
    cap_d = d["capital"]
    capital = Capital(
        economic=cap_d["economic"], cultural=cap_d["cultural"],
        social=cap_d["social"], symbolic=cap_d["symbolic"],
    )

    # Habitus
    hab_d = d["habitus"]
    habitus = Habitus(
        origin_class=SocialClass(hab_d["origin_class"]),
        current_class=SocialClass(hab_d["current_class"]),
        education_track=EducationTrack(hab_d["education_track"]),
        cultural_taste=hab_d["cultural_taste"],
        risk_tolerance=hab_d["risk_tolerance"],
        institutional_trust=hab_d["institutional_trust"],
        class_awareness=hab_d["class_awareness"],
        aspiration_gap=hab_d["aspiration_gap"],
    )

    # Economy
    economy = None
    if d.get("economy"):
        econ_d = d["economy"]
        tasks = get_tasks_for_occupation(d["occupation"])
        economy = AgentEconomy(
            tasks=tasks,
            income=econ_d["income"],
            displacement_risk=econ_d["displacement_risk"],
            productivity=econ_d["productivity"],
            tech_adaptation=econ_d["tech_adaptation"],
            task_disruption=dict(econ_d.get("task_disruption", {})),
        )

    # Media
    media = None
    if d.get("media"):
        med_d = d["media"]
        media = MediaConsumption(
            print_exposure=med_d["print_exposure"],
            mass_exposure=med_d["mass_exposure"],
            social_exposure=med_d["social_exposure"],
            media_literacy=med_d["media_literacy"],
            algorithmic_bubble=med_d["algorithmic_bubble"],
        )

    # Health
    health = None
    if d.get("health"):
        h_d = d["health"]
        health = AgentHealth(
            physical_health=h_d["physical_health"],
            mental_health=h_d["mental_health"],
            healthcare_access=h_d["healthcare_access"],
            chronic_condition=h_d["chronic_condition"],
            health_literacy=h_d["health_literacy"],
            work_capacity=h_d["work_capacity"],
            stress_level=h_d["stress_level"],
            disability=h_d["disability"],
        )

    # Institutions
    institutions = None
    if d.get("institutions"):
        inst_d = d["institutions"]
        memberships = []
        for m in inst_d.get("memberships", []):
            memberships.append(Membership(
                institution_type=InstitutionType(m["type"]),
                institution_name=m["name"],
                years_active=m["years_active"],
                leadership_role=m.get("leadership", False),
                economic_interest=m.get("economic_interest", 0.0),
            ))
        from institutions import _recompute_derived
        institutions = InstitutionalProfile(
            memberships=memberships,
            skill_currency=inst_d.get("skill_currency", 0.7),
            lifelong_learning=inst_d.get("lifelong_learning", 0.4),
            civic_participation=inst_d.get("civic_participation", 0.3),
        )
        _recompute_derived(institutions)

    agent = Agent(
        id=d["id"],
        name=d["name"],
        clan=d["clan"],
        district=d["district"],
        occupation=d["occupation"],
        interests=d["interests"],
        politics=PoliticalLeaning(d["politics"]),
        age=d["age"],
        life_phase=LifePhase(d["life_phase"]),
        capital=capital,
        habitus=habitus,
        openness=d["openness"],
        assertiveness=d["assertiveness"],
        loyalty=d["loyalty"],
        economy=economy,
        media=media,
        health=health,
        institutions=institutions,
        generation=d.get("generation", 0),
        parent_id=d.get("parent_id"),
        opinion_state=dict(d.get("opinion_state", {})),
        norms=dict(d.get("norms", {})),
        satisfaction=d.get("satisfaction", 1.0),
        emergence_score=d.get("emergence_score", 0.0),
    )
    return agent


def _deserialize_graph(data: dict) -> nx.Graph:
    """Reconstruct a NetworkX graph from saved data."""
    G = nx.Graph()
    for node_data in data["nodes"]:
        agent = _deserialize_agent(node_data)
        G.add_node(agent.id, agent=agent)
    for edge_data in data["edges"]:
        G.add_edge(
            edge_data["source"], edge_data["target"],
            weight=edge_data["weight"], rel=edge_data["rel"],
        )
    return G


def _deserialize_environment(data: dict):
    """Reconstruct Environment from saved data."""
    from environment import Environment
    env = Environment(
        year=data["year"],
        indicators=dict(data["indicators"]),
        history=list(data.get("history", [])),
        shocks=list(data.get("shocks", [])),
    )
    return env


def _deserialize_emergence(data: dict):
    """Reconstruct EmergenceTracker from saved data."""
    from emergence import EmergenceTracker, EmergenceSnapshot
    tracker = EmergenceTracker()
    tracker.history = []
    for entry in data.get("history", []):
        snap = EmergenceSnapshot(
            year=entry["year"],
            dimensions={},  # recomputed on next snapshot() call
            composites=dict(entry.get("composites", {})),
            coupled_composites=dict(entry.get("coupled_composites", {})),
            early_warnings=entry.get("early_warnings", {}),
            agent_scores=entry.get("agent_scores") or {},
        )
        tracker.history.append(snap)
    return tracker


def _deserialize_media(data: dict):
    """Reconstruct MediaLandscape from saved data."""
    if data is None:
        return None
    from media import MediaLandscape
    ml = MediaLandscape()
    for key, val in data.items():
        if hasattr(ml, key):
            setattr(ml, key, val)
    return ml


def _deserialize_tech_waves(data: dict):
    """Restore tech wave adoption levels to module globals."""
    from economy import TECH_WAVES
    for name, wave_data in data.items():
        if name in TECH_WAVES:
            tw = TECH_WAVES[name]
            tw.adoption = wave_data.get("adoption", tw.adoption)
            tw.growth_rate = wave_data.get("growth_rate", tw.growth_rate)
            tw.ceiling = wave_data.get("ceiling", tw.ceiling)


# ══════════════════════════════════════════════════════════════════════════════
# SAVE / LOAD
# ══════════════════════════════════════════════════════════════════════════════

def save_simulation(
    filepath: str | Path,
    graph: nx.Graph,
    env,
    emergence,
    media,
    event_history: list,
    label: str = "",
) -> dict:
    """Save full simulation state to a gzip-compressed JSON file.

    Returns metadata dict.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    state = {
        "format_version": FORMAT_VERSION,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "simulation_year": env.year if env else 0,
        "metadata": {
            "agent_count": graph.number_of_nodes() if graph else 0,
            "edge_count": graph.number_of_edges() if graph else 0,
            "event_count": len(event_history),
            "emergence_snapshots": len(emergence.history) if emergence else 0,
        },
        "graph": _serialize_graph(graph) if graph else None,
        "environment": _serialize_environment(env) if env else None,
        "emergence": _serialize_emergence(emergence) if emergence else None,
        "media_landscape": _serialize_media(media),
        "tech_waves": _serialize_tech_waves(),
        "event_history": event_history,
    }

    # Atomic write: write to temp file, then rename
    tmp_path = str(filepath) + ".tmp"
    try:
        with gzip.open(tmp_path, "wt", encoding="utf-8", compresslevel=6) as f:
            json.dump(state, f, separators=(",", ":"))
        os.replace(tmp_path, str(filepath))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    size = filepath.stat().st_size
    return {
        "filename": filepath.name,
        "size_bytes": size,
        "size_human": f"{size / 1024 / 1024:.1f} MB",
        **state["metadata"],
        "simulation_year": state["simulation_year"],
        "saved_at": state["saved_at"],
    }


def load_simulation(filepath: str | Path) -> dict:
    """Load simulation state from a saved file.

    Returns dict with: graph, environment, emergence, media, event_history
    """
    filepath = Path(filepath)

    with gzip.open(str(filepath), "rt", encoding="utf-8") as f:
        state = json.load(f)

    version = state.get("format_version", 0)
    if version > FORMAT_VERSION:
        raise ValueError(f"Save file format version {version} is newer than supported ({FORMAT_VERSION})")

    graph = _deserialize_graph(state["graph"]) if state.get("graph") else None
    env = _deserialize_environment(state["environment"]) if state.get("environment") else None
    emergence = _deserialize_emergence(state["emergence"]) if state.get("emergence") else None
    media = _deserialize_media(state.get("media_landscape"))
    event_history = state.get("event_history", [])

    # Restore tech waves
    if state.get("tech_waves"):
        _deserialize_tech_waves(state["tech_waves"])

    # Re-establish cross-references
    if env and media:
        env.media_landscape = media
    if graph and media:
        graph._media_landscape = media

    return {
        "graph": graph,
        "environment": env,
        "emergence": emergence,
        "media": media,
        "event_history": event_history,
        "metadata": state.get("metadata", {}),
        "simulation_year": state.get("simulation_year", 0),
        "label": state.get("label", ""),
    }


def list_saves(directory: str | Path) -> list[dict]:
    """List available save files with metadata."""
    directory = Path(directory)
    if not directory.exists():
        return []

    saves = []
    for f in sorted(directory.glob("*.json.gz"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with gzip.open(str(f), "rt", encoding="utf-8") as fh:
                # Read only the first ~2000 chars to extract metadata without loading full state
                header = fh.read(2000)
                # Parse enough to get metadata
                # Find the metadata closing brace by reading the partial JSON
                meta = json.loads(header[:header.find('"graph"') - 1] + "}")
            saves.append({
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "size_human": f"{f.stat().st_size / 1024 / 1024:.1f} MB",
                "saved_at": meta.get("saved_at", ""),
                "label": meta.get("label", ""),
                "simulation_year": meta.get("simulation_year", 0),
                "agent_count": meta.get("metadata", {}).get("agent_count", 0),
            })
        except Exception:
            # If we can't read metadata, still list the file
            saves.append({
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "size_human": f"{f.stat().st_size / 1024 / 1024:.1f} MB",
                "saved_at": "",
                "label": "",
                "simulation_year": 0,
            })

    return saves


# ══════════════════════════════════════════════════════════════════════════════
# CSV EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def export_csv_bundle(graph: nx.Graph, env, emergence, event_history: list) -> bytes:
    """Export simulation state as a ZIP of CSV files.

    Returns the ZIP file contents as bytes.
    """
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # ── agents.csv ─────────────────────────────────────────────
        agents_buf = io.StringIO()
        agents = [graph.nodes[n]["agent"] for n in graph.nodes]

        # Collect all opinion/norm topics
        all_opinion_topics = set()
        all_norm_topics = set()
        for a in agents:
            all_opinion_topics.update(a.opinion_state.keys())
            all_norm_topics.update(a.norms.keys())
        opinion_cols = sorted(all_opinion_topics)
        norm_cols = sorted(all_norm_topics)

        fieldnames = [
            "id", "name", "clan", "district", "occupation", "politics",
            "age", "life_phase", "openness", "assertiveness", "loyalty",
            "generation", "satisfaction", "emergence_score", "degree",
            "cap_economic", "cap_cultural", "cap_social", "cap_symbolic", "cap_volume",
            "hab_origin_class", "hab_current_class", "hab_education_track",
            "hab_cultural_taste", "hab_risk_tolerance", "hab_institutional_trust",
            "hab_class_awareness", "hab_aspiration_gap",
            "econ_income", "econ_displacement_risk", "econ_productivity", "econ_tech_adaptation",
            "media_print", "media_mass", "media_social", "media_literacy", "media_bubble",
            "health_physical", "health_mental", "health_access", "health_chronic",
            "health_literacy", "health_work_capacity", "health_stress", "health_disability",
            "inst_count", "inst_skill_currency", "inst_lifelong_learning",
            "inst_civic_participation", "inst_board_power",
            "influence",
        ] + [f"opinion_{t}" for t in opinion_cols] + [f"norm_{t}" for t in norm_cols]

        writer = csv.DictWriter(agents_buf, fieldnames=fieldnames)
        writer.writeheader()
        for a in agents:
            row = {
                "id": a.id, "name": a.name, "clan": a.clan,
                "district": a.district, "occupation": a.occupation,
                "politics": a.politics.value, "age": a.age,
                "life_phase": a.life_phase.value,
                "openness": a.openness, "assertiveness": a.assertiveness,
                "loyalty": a.loyalty, "generation": a.generation,
                "satisfaction": a.satisfaction, "emergence_score": a.emergence_score,
                "degree": graph.degree(a.id),
                "cap_economic": a.capital.economic, "cap_cultural": a.capital.cultural,
                "cap_social": a.capital.social, "cap_symbolic": a.capital.symbolic,
                "cap_volume": a.capital.total_volume,
                "hab_origin_class": a.habitus.origin_class.value,
                "hab_current_class": a.habitus.current_class.value,
                "hab_education_track": a.habitus.education_track.value,
                "hab_cultural_taste": a.habitus.cultural_taste,
                "hab_risk_tolerance": a.habitus.risk_tolerance,
                "hab_institutional_trust": a.habitus.institutional_trust,
                "hab_class_awareness": a.habitus.class_awareness,
                "hab_aspiration_gap": a.habitus.aspiration_gap,
                "influence": a.influence,
            }
            if a.economy:
                row.update({
                    "econ_income": a.economy.income,
                    "econ_displacement_risk": a.economy.displacement_risk,
                    "econ_productivity": a.economy.productivity,
                    "econ_tech_adaptation": a.economy.tech_adaptation,
                })
            if a.media:
                row.update({
                    "media_print": a.media.print_exposure,
                    "media_mass": a.media.mass_exposure,
                    "media_social": a.media.social_exposure,
                    "media_literacy": a.media.media_literacy,
                    "media_bubble": a.media.algorithmic_bubble,
                })
            if a.health:
                row.update({
                    "health_physical": a.health.physical_health,
                    "health_mental": a.health.mental_health,
                    "health_access": a.health.healthcare_access,
                    "health_chronic": a.health.chronic_condition,
                    "health_literacy": a.health.health_literacy,
                    "health_work_capacity": a.health.work_capacity,
                    "health_stress": a.health.stress_level,
                    "health_disability": a.health.disability,
                })
            if a.institutions:
                row.update({
                    "inst_count": len(a.institutions.memberships),
                    "inst_skill_currency": a.institutions.skill_currency,
                    "inst_lifelong_learning": a.institutions.lifelong_learning,
                    "inst_civic_participation": a.institutions.civic_participation,
                    "inst_board_power": a.institutions.board_power,
                })
            for t in opinion_cols:
                row[f"opinion_{t}"] = a.opinion_state.get(t, "")
            for t in norm_cols:
                row[f"norm_{t}"] = a.norms.get(t, "")
            writer.writerow(row)
        zf.writestr("agents.csv", agents_buf.getvalue())

        # ── edges.csv ──────────────────────────────────────────────
        edges_buf = io.StringIO()
        ew = csv.writer(edges_buf)
        ew.writerow(["source", "target", "weight", "rel"])
        for u, v, data in graph.edges(data=True):
            ew.writerow([u, v, data.get("weight", 0.5), data.get("rel", "")])
        zf.writestr("edges.csv", edges_buf.getvalue())

        # ── environment_history.csv ────────────────────────────────
        if env and env.history:
            env_buf = io.StringIO()
            env_fields = list(env.history[0].keys())
            ew = csv.DictWriter(env_buf, fieldnames=env_fields)
            ew.writeheader()
            for row in env.history:
                ew.writerow(row)
            zf.writestr("environment_history.csv", env_buf.getvalue())

        # ── emergence_history.csv ──────────────────────────────────
        if emergence and emergence.history:
            emg_buf = io.StringIO()
            dim_names = list(emergence.history[0].coupled_composites.keys())
            emg_fields = ["year"] + dim_names
            ew = csv.DictWriter(emg_buf, fieldnames=emg_fields)
            ew.writeheader()
            for snap in emergence.history:
                row = {"year": snap.year}
                row.update(snap.coupled_composites)
                ew.writerow(row)
            zf.writestr("emergence_history.csv", emg_buf.getvalue())

        # ── events.csv ─────────────────────────────────────────────
        if event_history:
            evt_buf = io.StringIO()
            evt_fields = ["id", "event_type", "title", "origin_agent", "topic",
                         "sentiment", "intensity", "political_bias",
                         "target_district", "target_clan", "steps", "total_affected"]
            ew = csv.DictWriter(evt_buf, fieldnames=evt_fields)
            ew.writeheader()
            for e in event_history:
                ew.writerow({
                    "id": e.get("id", ""),
                    "event_type": e.get("event_type", ""),
                    "title": e.get("title", ""),
                    "origin_agent": e.get("origin_agent", ""),
                    "topic": e.get("topic", ""),
                    "sentiment": e.get("sentiment", ""),
                    "intensity": e.get("intensity", ""),
                    "political_bias": e.get("political_bias", ""),
                    "target_district": e.get("target_district", ""),
                    "target_clan": e.get("target_clan", ""),
                    "steps": e.get("steps", ""),
                    "total_affected": e.get("total_affected", ""),
                })
            zf.writestr("events.csv", evt_buf.getvalue())

        # ── memberships.csv ────────────────────────────────────────
        mem_buf = io.StringIO()
        mem_w = csv.writer(mem_buf)
        mem_w.writerow(["agent_id", "agent_name", "institution_type",
                       "institution_name", "years_active", "leadership", "economic_interest"])
        for a in agents:
            if a.institutions:
                for m in a.institutions.memberships:
                    mem_w.writerow([
                        a.id, a.name, m.institution_type.value,
                        m.institution_name, m.years_active,
                        m.leadership_role, m.economic_interest,
                    ])
        zf.writestr("memberships.csv", mem_buf.getvalue())

    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH DATABASE / GEPHI EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def export_gexf(graph: nx.Graph) -> str:
    """Export graph in GEXF format (Gephi's native format).

    All agent attributes are flattened as node attributes so Gephi
    can use them for filtering, coloring, and sizing.
    """
    # Create a copy with flattened attributes for Gephi
    G_export = nx.Graph()

    for nid in graph.nodes:
        agent = graph.nodes[nid]["agent"]
        attrs = {
            "label": agent.name,
            "clan": agent.clan,
            "district": agent.district,
            "occupation": agent.occupation,
            "politics": agent.politics.value,
            "age": agent.age,
            "life_phase": agent.life_phase.value,
            "influence": round(agent.influence, 4),
            "openness": round(agent.openness, 4),
            "assertiveness": round(agent.assertiveness, 4),
            "loyalty": round(agent.loyalty, 4),
            "satisfaction": round(agent.satisfaction, 4),
            "emergence_score": round(agent.emergence_score, 4),
            "cap_economic": round(agent.capital.economic, 4),
            "cap_cultural": round(agent.capital.cultural, 4),
            "cap_social": round(agent.capital.social, 4),
            "cap_symbolic": round(agent.capital.symbolic, 4),
            "cap_volume": round(agent.capital.total_volume, 4),
            "class_origin": agent.habitus.origin_class.value,
            "class_current": agent.habitus.current_class.value,
            "education": agent.habitus.education_track.value,
            "cultural_taste": round(agent.habitus.cultural_taste, 4),
        }
        if agent.economy:
            attrs["income"] = round(agent.economy.income, 4)
            attrs["displacement_risk"] = round(agent.economy.displacement_risk, 4)
            attrs["productivity"] = round(agent.economy.productivity, 4)
        if agent.health:
            attrs["health_physical"] = round(agent.health.physical_health, 4)
            attrs["health_mental"] = round(agent.health.mental_health, 4)
            attrs["chronic_condition"] = agent.health.chronic_condition
            attrs["work_capacity"] = round(agent.health.work_capacity, 4)
        if agent.institutions:
            attrs["membership_count"] = len(agent.institutions.memberships)
            attrs["board_power"] = round(agent.institutions.board_power, 4)
            attrs["skill_currency"] = round(agent.institutions.skill_currency, 4)
        if agent.media:
            attrs["media_social"] = round(agent.media.social_exposure, 4)
            attrs["media_bubble"] = round(agent.media.algorithmic_bubble, 4)

        G_export.add_node(nid, **attrs)

    for u, v, data in graph.edges(data=True):
        G_export.add_edge(u, v,
            weight=data.get("weight", 0.5),
            rel=data.get("rel", "unknown"),
        )

    buf = io.BytesIO()
    nx.write_gexf(G_export, buf)
    return buf.getvalue().decode("utf-8")


def export_graphml(graph: nx.Graph) -> str:
    """Export graph in GraphML format (universal graph exchange).

    Compatible with Gephi, yEd, Cytoscape, Neo4j, igraph, etc.
    """
    G_export = nx.Graph()

    for nid in graph.nodes:
        agent = graph.nodes[nid]["agent"]
        attrs = {
            "label": agent.name,
            "clan": agent.clan,
            "district": agent.district,
            "occupation": agent.occupation,
            "politics": agent.politics.value,
            "age": agent.age,
            "influence": round(agent.influence, 4),
            "cap_economic": round(agent.capital.economic, 4),
            "cap_cultural": round(agent.capital.cultural, 4),
            "cap_social": round(agent.capital.social, 4),
            "cap_symbolic": round(agent.capital.symbolic, 4),
            "class_current": agent.habitus.current_class.value,
            "education": agent.habitus.education_track.value,
        }
        if agent.economy:
            attrs["income"] = round(agent.economy.income, 4)
            attrs["displacement_risk"] = round(agent.economy.displacement_risk, 4)
        if agent.health:
            attrs["health"] = round(agent.health.composite, 4)
        if agent.institutions:
            attrs["memberships"] = len(agent.institutions.memberships)
            attrs["board_power"] = round(agent.institutions.board_power, 4)

        G_export.add_node(nid, **attrs)

    for u, v, data in graph.edges(data=True):
        G_export.add_edge(u, v,
            weight=data.get("weight", 0.5),
            rel=data.get("rel", "unknown"),
        )

    buf = io.BytesIO()
    nx.write_graphml(G_export, buf)
    return buf.getvalue().decode("utf-8")
