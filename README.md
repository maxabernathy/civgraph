# CivGraph

An agent-based model of urban social dynamics, built on Pierre Bourdieu's theory of capital and habitus. 500 individuals in a mid-scale city form a living network where influence, opinion, and power flow through clan ties, professional bonds, and shared dispositions — shaped at every turn by the macro forces of economy, housing, migration, culture, and governance.

![The social graph of a city — 500 agents colored by clan affiliation, clustered by relationship density](docs/01-main-graph.png)

## Quick Start

```bash
pip install -r requirements.txt
python run.py
# http://localhost:8420
```

---

## Theoretical Foundations

CivGraph operationalizes concepts from Bourdieu's *Distinction* (1979) and *The Forms of Capital* (1986), combined with Granovetter's network embeddedness (1985) and Schelling-style emergent dynamics. The result is a simulation where macro-structural forces and micro-level dispositions produce stratification, coalition formation, and opinion cascades that mirror patterns observed in Western European cities.

### The four capitals

Bourdieu argued that social position is determined not by economic wealth alone, but by the interplay of multiple forms of capital. Each agent carries:

- **Economic capital** — wealth, income, property. Beta-distributed by social class with a Gini coefficient targeting ~0.32 (France/Germany average). A welfare-state floor of 0.15 prevents destitution — reflecting the social safety nets of the Rhineland model.
- **Cultural capital** — education, credentials, cultivated taste. Strongly path-dependent on education track (vocational: 0.20 base, elite/grande ecole: 0.78). This is the stickiest capital across generations — with an intergenerational elasticity of 0.50, it reproduces class position more reliably than wealth does.
- **Social capital** — network position, bridging ties, trust relationships. Derived from actual graph degree after city generation. Agents with high social capital lower the activation threshold for information propagation — they are the connectors.
- **Symbolic capital** — prestige, recognition, authority. Peaks in the established life phase (55-70). Partly inherited from clan reputation. Legitimized by democratic quality, devalued by corruption.

Influence is a derived composite: `0.4 × symbolic + 0.3 × social + 0.2 × economic + 0.1 × cultural`.

### Habitus

Bourdieu's concept of *habitus* — the durable, transposable dispositions acquired through socialization — is modeled as a set of internalized traits shaped by class origin and education:

- **Cultural taste** (-1 popular to +1 legitimate) — correlated r ≈ 0.6 with origin class. Determines who agents naturally gravitate toward.
- **Risk tolerance** — U-shaped by class: both upper classes (safety nets of wealth) and lower classes (nothing left to lose) show higher tolerance than the anxious middle.
- **Institutional trust** — peaks in the upper-middle class, where the system has most reliably worked in one's favor.
- **Class awareness** — stronger at class extremes, where the gap between one's position and the center is most felt.

Agents with similar habitus form bonds across clan boundaries (*habitus affinity ties*), reproducing Bourdieu's observation that class-based solidarity often cuts across ethnic and familial lines.

### Coloring the graph by social class

Switch to **Class** mode to see stratification. Brown/amber = lower and lower-middle, gray = middle, blue = upper-middle and upper. The clustering patterns reveal how class maps onto — but doesn't perfectly mirror — clan structure.

![Class color mode — stratification visible in network structure](docs/02-class-view.png)

### Inspecting an individual

Click any node to see the full Bourdieusian profile: four capital bars (economic in green, cultural in purple, social in blue, symbolic in gold), habitus section (origin class, current class, education track, cultural taste), and personality traits. The connections list shows relationship types and trust weights.

![Agent detail panel showing capital bars, habitus, and network connections](docs/03-agent-detail.png)

---

## Events and Influence Propagation

Events ripple through the social graph via a BFS cascade with decay. Each agent's reaction depends on:

1. **Capital field relevance** — agents with capital matching the event's domain react more strongly (high economic capital → stronger reaction to housing crises)
2. **Political alignment** — Gaussian-weighted distance between agent's politics and the event's bias
3. **Habitus disposition** — institutional trust amplifies governance reactions, risk tolerance dampens crisis responses, cultural taste amplifies arts/education events
4. **Habitus affinity** — when the source agent shares dispositional similarity with the receiver, the trust channel is amplified
5. **Social capital threshold** — well-connected agents (high social capital) have a lower activation threshold, spreading information more readily
6. **Clan loyalty** — when an event targets an agent's own clan negatively, loyalty acts as a buffer

![Event propagation — a housing crisis cascading through the network](docs/04-event-propagation.png)

The event log tracks impact metrics. Each event also shifts macro-environment indicators — a housing crisis pushes up the price index and rent burden, erodes social cohesion, and reduces net migration.

![Post-event state with event log and environment gauges](docs/05-post-event.png)

### Bridge agents

Betweenness centrality identifies the agents who connect otherwise disconnected communities — the brokers, translators, and gatekeepers through whom information and influence must pass.

![Bridge agents — the structural holes between communities](docs/06-bridge-agents.png)

---

## Macro-Environment

18 time-varying indicators across 5 domains model the city's structural context. These evolve endogenously through economic feedback loops (Okun's law, Phillips curve, housing supply/demand) and are bidirectionally coupled with agent capital.

| Domain | Indicators | Key dynamics |
|---|---|---|
| **Economy** | GDP growth, unemployment, inflation, business confidence | Okun's law, Phillips curve, confidence feedback |
| **Housing** | Price index, vacancy rate, rent burden, construction | Supply/demand cycle, price-construction response |
| **Migration** | Net migration, diversity, integration | Attracted by jobs, repelled by rent burden |
| **Culture** | Cultural spending, social cohesion, media pluralism | Cohesion eroded by inequality, boosted by integration |
| **Governance** | Public spending, corruption, policy stability, democratic quality | Corruption mean-reverts; democratic quality tracks cohesion |

Advance the simulation by 1-10 years at a time. Each tick ages all agents, recomputes lifecycle phases, applies capital curves, and runs the full environment coupling. The **Capital** color mode shows how total capital volume shifts across the population over time.

![After 5 years — capital volume color mode showing how macro forces reshaped individual positions](docs/07-environment-tick.png)

### Environment → Agent coupling

- GDP growth raises economic capital proportional to existing wealth (the Matthew effect)
- Unemployment penalizes lower classes disproportionately (class-weighted)
- Inflation erodes unhedged savings (inverse wealth protection)
- Rent burden drains economic capital of those with less
- Cultural spending boosts cultural capital accumulation
- Democratic quality legitimizes symbolic capital; corruption devalues it

### Agent → Environment feedback

- Average economic capital drives business confidence
- Average symbolic capital supports democratic quality
- Opinion polarization (variance across agents) erodes social cohesion

---

## Lifecycle and Intergenerational Transmission

Five phases with capital multipliers reflecting empirical Western European life-course patterns:

| Phase | Ages | Economic | Cultural | Social | Symbolic |
|---|---|---|---|---|---|
| Education | 18-24 | 0.15 | 0.55 | 0.30 | 0.05 |
| Early career | 25-34 | 0.50 | 0.75 | 0.50 | 0.15 |
| Mid career | 35-54 | 1.00 | 0.90 | 0.80 | 0.50 |
| Established | 55-69 | 0.85 | 1.00 | 1.00 | 1.00 |
| Elder | 70+ | 0.70 | 0.95 | 0.75 | 0.90 |

Within clans, agents aged 45+ are assigned as parents of agents under 30. Capital transmits with friction:

- **Economic**: transfer rate 0.65 (after inheritance tax, FR/DE/NL average), intergenerational elasticity 0.35
- **Cultural**: elasticity 0.50 — Bourdieu's central finding that cultural capital reproduces class position more reliably than wealth
- **Symbolic**: 30% from parent, 20% from clan average (the family name effect)
- **Habitus**: child inherits parent's cultural taste (weight 0.6), institutional trust (0.5), risk tolerance (0.4) — dispositions are durable but not deterministic
- **Education track**: class-correlated probability tables calibrated to FR/DE patterns (upper: 35% elite + 45% academic; lower: 60% vocational + 9% academic)

### Class structure

20 clans are assigned class centers (Delacroix = 3.8/upper, Kowalski = 1.1/lower). Individual members deviate with noise, creating realistic within-clan variation while preserving the correlation between family origin and class position that Bourdieu documented.

---

## Exportable Artifacts

Six print-quality visualizations rendered to canvas in a scientific engraving aesthetic — ivory paper, fine ink lines, crosshatching, serif typography. All exportable as PNG or PDF, including dedicated **A2 300dpi** presets (landscape: 7016×4961px, portrait: 4961×7016px) for archival-quality prints.

### Anatomies of Agency (Plate I)

Each of the city's 80 most influential agents rendered as a unique radial glyph. Four colored quadrant arcs encode capital (green = economic, purple = cultural, blue = social, ochre = symbolic). Radiating spokes mark interest domains. The core dot sizes by agency (influence × assertiveness). Political lean rotates the glyph. Stipple density encodes network degree. Ink color = clan.

![Anatomies of Agency — specimen plate of the city's most influential individuals](docs/08-anatomies.png)

### Survey of Influence (Plate II)

Gaussian kernel density estimation over force-layout positions. Influence radiates as terrain elevation, rendered with crosshatched bands and ink contour lines at 15% intervals. Red survey markers for agents, labeled for top influencers.

![Survey of Influence — cartographic elevation map](docs/09-topography.png)

### Constellations of Clan (Plate III)

Star chart. Each clan is a constellation connected by minimum-spanning-tree lines. Horizontal axis = political leaning (far left to far right). Vertical axis = influence. Star brightness scales with influence; high-influence agents get cross-flares.

![Constellations of Clan — astronomical chart of social structure](docs/10-constellations.png)

### Pulse of the City (Plate VI)

Layered time-series strips showing all 18 environment indicators evolving over simulation years. Five domain rows (economy, housing, migration, culture, governance), each with overlapping ink traces.

![Pulse of the City — macro-environment evolution over time](docs/11-citypulse.png)

### Additional artifacts

- **Fabric of Opinion** (Plate IV) — woven-textile grid (rows = clans, columns = topics). Vertical green hatching = support, horizontal red = opposition, cross-hatch sepia = internal disagreement. Requires fired events.
- **Seismograph of Events** (Plate V) — strip-chart waveforms showing cascade amplitude per propagation step. Oscillation frequency increases with depth.

---

## Architecture

```
environment.py — 18-indicator macro model, internal dynamics (Okun, Phillips,
                 supply/demand), bidirectional agent coupling, event coupling
capital.py     — Bourdieu's four capitals, habitus, lifecycle curves,
                 intergenerational transmission, Western European calibration
model.py       — Agent dataclass, city generator (500 agents, 7 edge types,
                 class-stratified clans), graph queries, D3 export
events.py      — Event system, capital-aware BFS propagation, habitus
                 disposition filtering, coalition detection
server.py      — FastAPI REST + WebSocket API, Pydantic validation,
                 security-hardened (XSS, CSRF, origin checking)
static/        — D3.js frontend (8 color modes, 6 artifacts, environment
                 gauges, A2 print export)
run.py         — Launcher (localhost-only)
```

## API

| Endpoint | Description |
|---|---|
| `GET /api/graph` | Full graph (nodes with capital/habitus, edges with types) |
| `GET /api/stats` | Network statistics + class distribution + capital averages |
| `GET /api/agent/{id}` | Agent detail (capital, habitus, neighbors) |
| `GET /api/search` | Search by name, clan, district, politics |
| `GET /api/meta` | Metadata (clans, districts, classes, education tracks) |
| `POST /api/event` | Trigger event with capital-aware propagation |
| `GET /api/opinion/{topic}` | Opinion breakdown by clan/district/politics |
| `GET /api/bridges` | Top 20 bridge agents by betweenness centrality |
| `GET /api/coalitions/{topic}` | Emergent coalitions around a topic |
| `GET /api/influence_path/{a}/{b}` | Shortest influence path between agents |
| `GET /api/environment` | Current macro-environment indicators |
| `GET /api/environment/history` | Full indicator history (for City Pulse artifact) |
| `GET /api/environment/meta` | Indicator metadata (labels, ranges, domains) |
| `POST /api/tick` | Advance simulation 1-10 years |
| `POST /api/reset?seed=N` | Reset city + environment with new seed |
| `WS /ws` | WebSocket for live propagation animation |
