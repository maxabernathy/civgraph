"""
CivGraph — FastAPI server.

Serves the D3.js visualization and provides REST + WebSocket APIs
for interacting with the agent-based model.
"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from model import generate_city, export_for_d3, graph_stats, get_agent, INTEREST_POOL, DISTRICTS, CLAN_NAMES
from events import (
    create_event, opinion_summary, find_bridges, find_coalitions,
    EVENT_TEMPLATES,
)

import networkx as nx

app = FastAPI(title="CivGraph", version="0.1.0")

# ── State ────────────────────────────────────────────────────────────────────

GRAPH: nx.Graph | None = None
EVENT_HISTORY: list[dict] = []


def ensure_graph(seed: int | None = 42) -> nx.Graph:
    global GRAPH
    if GRAPH is None:
        GRAPH = generate_city(500, seed=seed)
    return GRAPH


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
    h = set(highlight.split(",")) if highlight else None
    return export_for_d3(G, highlight=h)


@app.get("/api/stats")
async def get_stats():
    G = ensure_graph()
    return graph_stats(G)


@app.get("/api/agent/{agent_id}")
async def get_agent_detail(agent_id: str):
    G = ensure_graph()
    try:
        agent = get_agent(G, agent_id)
    except KeyError:
        return {"error": "Agent not found"}

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
    limit: int = 20,
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
async def trigger_event(body: dict):
    G = ensure_graph()
    event = create_event(
        G,
        event_type=body.get("event_type", "custom"),
        title=body.get("title", "Untitled Event"),
        origin_agent_id=body["origin_agent"],
        topic=body.get("topic", "governance"),
        sentiment=body.get("sentiment", 0.5),
        intensity=body.get("intensity", 0.7),
        political_bias=body.get("political_bias", 0.0),
        target_district=body.get("target_district"),
        target_clan=body.get("target_clan"),
        description=body.get("description", ""),
        max_steps=body.get("max_steps", 6),
    )
    result = event.to_dict()
    EVENT_HISTORY.append(result)
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
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")

            if action == "propagate":
                G = ensure_graph()
                event = create_event(
                    G,
                    event_type=data.get("event_type", "custom"),
                    title=data.get("title", "Live Event"),
                    origin_agent_id=data["origin_agent"],
                    topic=data.get("topic", "governance"),
                    sentiment=data.get("sentiment", 0.5),
                    intensity=data.get("intensity", 0.7),
                    political_bias=data.get("political_bias", 0.0),
                    target_district=data.get("target_district"),
                    target_clan=data.get("target_clan"),
                    max_steps=data.get("max_steps", 6),
                )
                result = event.to_dict()
                EVENT_HISTORY.append(result)

                # Send step by step for animation
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
