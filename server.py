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
from events import (
    create_event, opinion_summary, find_bridges, find_coalitions,
    EVENT_TEMPLATES,
)

import networkx as nx

app = FastAPI(title="CivGraph", version="0.2.0")

# ── Constants ────────────────────────────────────────────────────────────────

MAX_EVENT_HISTORY = 200
MAX_PROPAGATION_STEPS = 20
MAX_SEARCH_LIMIT = 500

# ── State ────────────────────────────────────────────────────────────────────

GRAPH: nx.Graph | None = None
EVENT_HISTORY: list[dict] = []


def ensure_graph(seed: int | None = 42) -> nx.Graph:
    global GRAPH
    if GRAPH is None:
        GRAPH = generate_city(500, seed=seed)
    return GRAPH


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
    global GRAPH, EVENT_HISTORY
    GRAPH = generate_city(500, seed=seed)
    EVENT_HISTORY = []
    return {"status": "ok", "stats": graph_stats(GRAPH)}


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

    return {
        "agent": agent.to_dict(),
        "neighbors": neighbors,
        "degree": G.degree(agent_id),
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

    return result


@app.get("/api/events")
async def get_events():
    return EVENT_HISTORY


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
