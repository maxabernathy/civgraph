# CivGraph

Agent-based modeling on a social graph. Simulates 500 influential people in a mid-scale city with clan ties, political leanings, professional networks, and district connections. Watch influence cascade through the network in real time.

![Main graph view — 500 agents colored by clan](docs/01-main-graph.png)

## Quick Start

```bash
pip install -r requirements.txt
python run.py
# Open http://localhost:8420
```

## The Graph

500 agents connected by 2,600+ weighted edges across 6 relationship types. The force-directed layout clusters tightly-knit communities together and pushes rivals apart. Zoom, pan, and drag nodes to explore the network.

### Color by political leaning

Switch to **Politics** mode to see the ideological landscape. Red = left, blue = right, gray = center. Notice how political clusters overlap with but don't perfectly mirror clan boundaries.

![Politics color mode — red/blue/gray spectrum](docs/02-politics-view.png)

### Inspect any agent

Click a node to see their full profile: clan, district, occupation, personality traits (openness, assertiveness, loyalty), influence score, and all connections sorted by relationship weight. The right panel shows bar charts for each trait and lists neighbors with their relationship type.

![Agent detail panel with personality traits and connections](docs/03-agent-detail.png)

### Fire events and watch influence propagate

Select an origin agent, configure an event (type, topic, sentiment, intensity, political bias), and fire it. Influence cascades outward through the network — agents flash green (support) or red (oppose) as the event reaches them. Each agent's reaction depends on their political alignment, clan loyalty, personality, and the trust weight of the edge that carried the information.

![Event propagation — agents reacting to a corruption scandal](docs/04-event-propagation.png)

The event log tracks every event with impact metrics: how many agents were affected, how many propagation steps occurred, and the sentiment breakdown.

![Post-event state with event log](docs/05-post-event.png)

### Find bridge agents

Identify the people who connect otherwise disconnected communities. Bridge agents have the highest betweenness centrality — they are the gatekeepers through which information and influence must travel between clusters.

![Bridge agents highlighted with betweenness centrality scores](docs/06-bridge-agents.png)

## Exportable Artifacts

Five print-resolution visualizations rendered to canvas, exportable as high-res PNG or PDF at up to 8x resolution (poster quality). The aesthetic draws from scientific engraving and naturalist specimen plates — ivory paper, fine ink lines, crosshatching, serif typography — rather than the typical tech-dashboard look.

### Anatomies of Agency

The hero artifact. Each of the city's 80 most influential agents is rendered as a unique radial glyph — a complete visual portrait encoding three dimensions of the individual:

- **Agency** (core dot) — radius proportional to influence multiplied by assertiveness. How much this person can actually move the needle.
- **Constraint** (ring arcs) — loyalty fills the ring clockwise, resources fill it counter-clockwise. The gap between arcs is proportional to openness: a narrow gap means a rigid, hard-to-sway agent; a wide gap means a receptive one.
- **Intention** (outer spokes) — each spoke points to one of 20 fixed interest-domain positions (like hours on a clock). The pattern of spokes reveals what this person cares about.
- **Political lean** — the entire glyph is rotated: left-leaning agents tilt left, right-leaning tilt right.
- **Connectedness** — stipple density within the glyph encodes network degree.
- **Clan** — ink color.

No two glyphs are alike. The plate reads like a page from a 19th-century naturalist's field journal.

![Agent Anatomies — specimen plate of the city's most influential individuals](docs/07-agent-anatomies.png)

### Survey of Influence

Topographic elevation map of influence density across the network. Agent positions from the force-directed layout become terrain coordinates; influence radiates outward via Gaussian kernel density estimation. Rendered with crosshatched elevation bands and ink contour lines at 15% intervals, with red survey markers for each agent.

![Influence Survey — crosshatched topographic map](docs/08-influence-survey.png)

### Constellations of Clan

Astronomical star chart. Each clan forms a constellation connected by minimum-spanning-tree lines. The horizontal axis is political leaning (far left to far right), the vertical axis is influence. Star brightness and size scale with influence; high-influence agents get cross-flares.

![Clan Constellations — star chart of social structure](docs/09-clan-constellations.png)

### Opinion Fabric and Event Seismograph

Two additional artifacts available after firing events:

- **Opinion Fabric** — a woven-textile grid (rows = clans, columns = topics). Vertical green hatching = support, horizontal red hatching = opposition. Perpendicular cross-hatch in sepia reveals internal clan disagreement.
- **Event Seismograph** — strip-chart waveforms. Each fired event gets a row. Amplitude = cascade reach per propagation step. Oscillation frequency increases with depth.

All artifacts can be exported at 1x (screen), 2x (print), 4x (high-res), or 8x (poster) resolution via the modal toolbar.

## What It Models

- **500 agents** — each with clan, district, occupation, political leaning, interests, personality traits (openness, assertiveness, loyalty), influence, and resources
- **20 clans** with power-law size distributions, each anchored to a home district
- **10 districts** — agents have a 60% chance of living in their clan's home base
- **7 political leanings** — far left to far right, with clan-correlated tendencies
- **6 relationship types** — clan bonds, professional ties, political alliances, district neighbors, friendships, rivalries
- **Influence propagation** — BFS cascade with per-hop decay, personality-modulated reactions, and rivalry inversion
- **Emergent coalitions** — detect groups that form around shared opinions after events

## Architecture

```
model.py      — Agent dataclass, city generator, graph queries, D3 export
events.py     — Event system, influence propagation engine, coalition detection
server.py     — FastAPI REST + WebSocket API
static/       — D3.js frontend (index.html, app.js, style.css, artifacts.js)
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
