# CivGraph

Agent-based modeling on a social graph. Simulates 500 influential people in a mid-scale city with clan ties, political leanings, professional networks, and district connections.

## Quick Start

```bash
pip install -r requirements.txt
python run.py
# Open http://localhost:8420
```

## What It Does

- **500 agents** — each with clan, district, occupation, political leaning, interests, personality traits (openness, assertiveness, loyalty), influence, and resources
- **Graph engine** — NetworkX graph with 6 relationship types: clan, professional, political, district, friendship, rivalry
- **Event system** — trigger elections, scandals, crises, protests, etc. and watch influence cascade through the network in real time
- **Emergent coalitions** — detect groups that form around shared opinions after events
- **Bridge agents** — find the people who connect otherwise disconnected communities
- **D3.js visualization** — interactive force-directed graph, color by clan/politics/district/influence, filter, zoom, click to inspect

## Architecture

```
model.py      — Agent dataclass, city generator, graph queries, D3 export
events.py     — Event system, influence propagation engine, coalition detection
server.py     — FastAPI REST + WebSocket API
static/       — D3.js frontend (index.html, app.js, style.css)
run.py        — Launcher
```

## API

| Endpoint | Description |
|---|---|
| `GET /api/graph` | Full graph in D3 format |
| `GET /api/stats` | Network statistics |
| `GET /api/agent/{id}` | Agent detail + neighbors |
| `GET /api/search?q=&clan=&district=&politics=` | Search agents |
| `POST /api/event` | Trigger event and propagate |
| `GET /api/opinion/{topic}` | Opinion breakdown by clan/district/politics |
| `GET /api/bridges` | Top 20 bridge agents by betweenness centrality |
| `GET /api/coalitions/{topic}` | Emergent coalitions around a topic |
| `GET /api/influence_path/{source}/{target}` | Shortest influence path |
| `POST /api/reset?seed=N` | Reset with new random city |
| `WS /ws` | WebSocket for live propagation animation |
