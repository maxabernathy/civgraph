"""
CivGraph — FastAPI server.

Serves the D3.js visualization and provides REST + WebSocket APIs
for interacting with the agent-based model.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field

from model import generate_city, export_for_d3, graph_stats, get_agent, INTEREST_POOL, DISTRICTS, CLAN_NAMES
from capital import SocialClass, LifePhase, EducationTrack, EU_CONFIG
from events import (
    create_event, opinion_summary, find_bridges, find_coalitions,
    EVENT_TEMPLATES,
)
from environment import (
    Environment, create_environment, advance_environment,
    event_affects_environment, INDICATOR_DOMAINS, INDICATOR_META,
)
from emergence import (
    EmergenceTracker, DIMENSION_META as EMERGENCE_META,
    advance_emergence_dynamics, COUPLING_MATRIX,
)
import random as _random

import networkx as nx

app = FastAPI(title="CivGraph", version="0.2.0")

# ── Constants ────────────────────────────────────────────────────────────────

MAX_EVENT_HISTORY = 200
MAX_PROPAGATION_STEPS = 20
MAX_SEARCH_LIMIT = 500

# ── State ────────────────────────────────────────────────────────────────────

GRAPH: nx.Graph | None = None
EVENT_HISTORY: list[dict] = []
ENV: Environment | None = None
EMERGENCE: EmergenceTracker | None = None


def ensure_graph(seed: int | None = 42) -> nx.Graph:
    global GRAPH, ENV, EMERGENCE
    if GRAPH is None:
        GRAPH = generate_city(500, seed=seed)
        ENV = create_environment(seed)
        EMERGENCE = EmergenceTracker()
        EMERGENCE.snapshot(GRAPH, year=0)
    return GRAPH


def ensure_env() -> Environment:
    global ENV
    if ENV is None:
        ensure_graph()
    return ENV


def ensure_emergence() -> EmergenceTracker:
    global EMERGENCE
    if EMERGENCE is None:
        ensure_graph()
    return EMERGENCE


def _validate_agent_id(G: nx.Graph, agent_id: str) -> None:
    """Raise 404 if agent_id is not in the graph."""
    if agent_id not in G.nodes:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")


# ── Input models ─────────────────────────────────────────────────────────────

class EventRequest(BaseModel):
    origin_agent: str
    event_type: str = "custom"
    title: str = "Untitled Event"
    topic: str = "governance"
    sentiment: float = Field(default=0.5, ge=-1.0, le=1.0)
    intensity: float = Field(default=0.7, ge=0.0, le=1.0)
    political_bias: float = Field(default=0.0, ge=-3.0, le=3.0)
    max_steps: int = Field(default=6, ge=1, le=MAX_PROPAGATION_STEPS)
    target_district: str | None = None
    target_clan: str | None = None
    description: str = ""


# ── Static files ─────────────────────────────────────────────────────────────

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(static_dir / "index.html"))


# ── REST API ─────────────────────────────────────────────────────────────────

@app.post("/api/reset")
async def reset_graph(seed: int = 42):
    global GRAPH, EVENT_HISTORY, ENV, EMERGENCE
    GRAPH = generate_city(500, seed=seed)
    ENV = create_environment(seed)
    EMERGENCE = EmergenceTracker()
    EMERGENCE.snapshot(GRAPH, year=0)
    EVENT_HISTORY = []
    return {"status": "ok", "stats": graph_stats(GRAPH), "environment": ENV.to_dict()}


@app.get("/api/graph")
async def get_graph(highlight: Optional[str] = None):
    G = ensure_graph()
    h = set(highlight.split(",")[:500]) if highlight else None
    return export_for_d3(G, highlight=h)


@app.get("/api/stats")
async def get_stats():
    G = ensure_graph()
    return graph_stats(G)


@app.get("/api/agent/{agent_id}")
async def get_agent_detail(agent_id: str):
    G = ensure_graph()
    _validate_agent_id(G, agent_id)
    agent = get_agent(G, agent_id)

    neighbors = []
    for nid in G.neighbors(agent_id):
        na = get_agent(G, nid)
        edge = G.edges[agent_id, nid]
        neighbors.append({
            "id": na.id,
            "name": na.name,
            "clan": na.clan,
            "rel": edge.get("rel", "unknown"),
            "weight": edge.get("weight", 0),
        })

    # Include emergence scores if available
    emg = ensure_emergence()
    emergence_scores = {}
    if emg.history:
        emergence_scores = emg.history[-1].agent_scores.get(agent_id, {})

    return {
        "agent": agent.to_dict(),
        "neighbors": neighbors,
        "degree": G.degree(agent_id),
        "emergence": emergence_scores,
    }


@app.get("/api/search")
async def search_agents(
    q: str = "",
    clan: Optional[str] = None,
    district: Optional[str] = None,
    politics: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=MAX_SEARCH_LIMIT),
):
    G = ensure_graph()
    results = []
    for n in G.nodes:
        a = get_agent(G, n)
        if clan and a.clan != clan:
            continue
        if district and a.district != district:
            continue
        if politics and a.politics.value != politics:
            continue
        if q and q.lower() not in a.name.lower():
            continue
        results.append(a.to_dict())
        if len(results) >= limit:
            break
    return results


@app.get("/api/meta")
async def get_meta():
    return {
        "clans": CLAN_NAMES,
        "districts": DISTRICTS,
        "interests": INTEREST_POOL,
        "event_types": list(EVENT_TEMPLATES.keys()),
        "social_classes": [c.value for c in SocialClass],
        "life_phases": [p.value for p in LifePhase],
        "education_tracks": [t.value for t in EducationTrack],
    }


@app.post("/api/event")
async def trigger_event(body: EventRequest):
    G = ensure_graph()
    _validate_agent_id(G, body.origin_agent)

    event = create_event(
        G,
        event_type=body.event_type,
        title=body.title,
        origin_agent_id=body.origin_agent,
        topic=body.topic,
        sentiment=body.sentiment,
        intensity=body.intensity,
        political_bias=body.political_bias,
        target_district=body.target_district,
        target_clan=body.target_clan,
        description=body.description,
        max_steps=body.max_steps,
    )
    result = event.to_dict()

    EVENT_HISTORY.append(result)
    if len(EVENT_HISTORY) > MAX_EVENT_HISTORY:
        EVENT_HISTORY.pop(0)

    # Event → Environment coupling
    env = ensure_env()
    event_affects_environment(env, body.event_type, body.intensity)
    result["environment"] = env.to_dict()

    return result


@app.get("/api/events")
async def get_events():
    return EVENT_HISTORY


# ── Environment endpoints ───────────────────────────────────────────────────

class TickRequest(BaseModel):
    years: int = Field(default=1, ge=1, le=10)


@app.get("/api/environment")
async def get_environment():
    env = ensure_env()
    return env.to_dict()


@app.get("/api/environment/history")
async def get_env_history():
    env = ensure_env()
    return env.get_history()


@app.get("/api/environment/meta")
async def get_env_meta():
    return {
        "domains": INDICATOR_DOMAINS,
        "indicators": {
            k: {"label": v[0], "min": v[1], "max": v[2], "format": v[3],
                "higher_is_better": v[4]}
            for k, v in INDICATOR_META.items()
        },
    }


@app.post("/api/tick")
async def advance_simulation(body: TickRequest):
    G = ensure_graph()
    env = ensure_env()
    emg = ensure_emergence()
    rng = _random.Random()
    result = advance_environment(env, G, years=body.years)
    # Run emergence dynamics (downward causation, rewiring, norms, segregation)
    dynamics = advance_emergence_dynamics(G, emg, rng)
    result["stats"] = graph_stats(G)
    # Compute emergence snapshot at end of tick
    snap = emg.snapshot(G, year=env.year)
    result["emergence"] = snap.to_dict()
    result["emergence_dynamics"] = dynamics
    return result


@app.get("/api/opinion/{topic}")
async def get_opinion(topic: str):
    G = ensure_graph()
    return opinion_summary(G, topic)


@app.get("/api/bridges")
async def get_bridges():
    G = ensure_graph()
    return find_bridges(G)


@app.get("/api/coalitions/{topic}")
async def get_coalitions(topic: str):
    G = ensure_graph()
    return find_coalitions(G, topic)


@app.get("/api/influence_path/{source}/{target}")
async def influence_path(source: str, target: str):
    G = ensure_graph()
    _validate_agent_id(G, source)
    _validate_agent_id(G, target)
    try:
        path = nx.shortest_path(G, source, target, weight="weight")
        agents = [get_agent(G, n).to_dict() for n in path]
        edges = []
        for i in range(len(path) - 1):
            e = G.edges[path[i], path[i + 1]]
            edges.append({"weight": e.get("weight", 0), "rel": e.get("rel", "")})
        return {"path": agents, "edges": edges, "length": len(path)}
    except nx.NetworkXNoPath:
        return {"path": [], "edges": [], "length": -1}


# ── Emergence endpoints ──────────────────────────────────────────────────────

@app.get("/api/emergence")
async def get_emergence():
    G = ensure_graph()
    emg = ensure_emergence()
    if not emg.history:
        emg.snapshot(G, year=ensure_env().year)
    return emg.to_dict()


@app.get("/api/emergence/snapshot")
async def get_emergence_snapshot():
    """Compute a fresh emergence snapshot (does not record to history)."""
    G = ensure_graph()
    from emergence import EMERGENCE_DIMENSIONS
    dimensions = {}
    composites = {}
    for name, func in EMERGENCE_DIMENSIONS:
        result = func(G)
        dimensions[name] = result
        composites[name] = result.get("composite", 0.0)
    return {"dimensions": dimensions, "composites": composites, "meta": EMERGENCE_META}


@app.get("/api/emergence/history")
async def get_emergence_history():
    emg = ensure_emergence()
    return emg.get_history()


@app.get("/api/emergence/meta")
async def get_emergence_meta():
    return EMERGENCE_META


@app.get("/api/emergence/coupling")
async def get_emergence_coupling():
    return COUPLING_MATRIX


@app.get("/api/emergence/agent/{agent_id}")
async def get_agent_emergence(agent_id: str):
    """Get per-agent emergence attribution scores."""
    G = ensure_graph()
    _validate_agent_id(G, agent_id)
    emg = ensure_emergence()
    if emg.history:
        scores = emg.history[-1].agent_scores.get(agent_id, {})
    else:
        from emergence import compute_agent_emergence_scores
        all_scores = compute_agent_emergence_scores(G)
        scores = all_scores.get(agent_id, {})
    return scores


# ── WebSocket for live propagation ──────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    # Origin validation: only accept connections from same host
    origin = ws.headers.get("origin", "")
    host = ws.headers.get("host", "")
    if origin and host:
        # Strip protocol prefix for comparison
        origin_host = origin.split("//", 1)[-1].rstrip("/")
        if origin_host != host:
            await ws.close(code=1008, reason="Origin mismatch")
            return

    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")

            if action == "propagate":
                origin_agent = data.get("origin_agent")
                if not origin_agent or not isinstance(origin_agent, str):
                    await ws.send_json({"type": "error", "detail": "origin_agent required"})
                    continue

                G = ensure_graph()
                if origin_agent not in G.nodes:
                    await ws.send_json({"type": "error", "detail": "Agent not found"})
                    continue

                max_steps = min(int(data.get("max_steps", 6)), MAX_PROPAGATION_STEPS)
                sentiment = max(-1.0, min(1.0, float(data.get("sentiment", 0.5))))
                intensity = max(0.0, min(1.0, float(data.get("intensity", 0.7))))
                pol_bias = max(-3.0, min(3.0, float(data.get("political_bias", 0.0))))

                event = create_event(
                    G,
                    event_type=data.get("event_type", "custom"),
                    title=data.get("title", "Live Event"),
                    origin_agent_id=origin_agent,
                    topic=data.get("topic", "governance"),
                    sentiment=sentiment,
                    intensity=intensity,
                    political_bias=pol_bias,
                    target_district=data.get("target_district"),
                    target_clan=data.get("target_clan"),
                    max_steps=max_steps,
                )
                result = event.to_dict()

                EVENT_HISTORY.append(result)
                if len(EVENT_HISTORY) > MAX_EVENT_HISTORY:
                    EVENT_HISTORY.pop(0)

                for step_data in result["propagation"]:
                    await ws.send_json({
                        "type": "propagation_step",
                        "event_id": result["id"],
                        "step": step_data,
                        "affected": list(event.affected_agents),
                    })
                    await asyncio.sleep(0.5)

                await ws.send_json({
                    "type": "propagation_complete",
                    "event": result,
                    "graph": export_for_d3(G, highlight=event.affected_agents),
                })

            elif action == "get_graph":
                G = ensure_graph()
                await ws.send_json({
                    "type": "graph_data",
                    "data": export_for_d3(G),
                })

    except WebSocketDisconnect:
        pass
    except (ValueError, TypeError, KeyError):
        # Malformed WebSocket message — close gracefully
        await ws.close(code=1003, reason="Invalid message format")
