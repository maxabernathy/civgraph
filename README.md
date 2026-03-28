# CivGraph

An agent-based model of urban social dynamics, built on Pierre Bourdieu's theory of capital and habitus. 1,000 individuals in a mid-scale city form a living network where influence, opinion, and power flow through clan ties, professional bonds, institutional memberships, and shared dispositions -- shaped by macro forces of economy, housing, migration, culture, and governance, disrupted by waves of technological change, refracted through print, mass, and social media, and grounded in the social determinants of health.

![The social graph of a city -- 1,000 agents colored by clan affiliation, with economy, media, and health panels visible](docs/01-main-graph.png)

## Quick Start

```bash
pip install -r requirements.txt
python run.py
# http://localhost:8420
```

---

## Theoretical Foundations

CivGraph operationalizes concepts from Bourdieu's *Distinction* (1979) and *The Forms of Capital* (1986), Autor's task-content framework (2003), Marmot's social determinants of health (2005), Mizruchi's interlocking directorates (1996), and McCombs & Shaw's agenda-setting theory (1972), combined with Granovetter's network embeddedness (1985) and Schelling-style emergent dynamics.

### The four capitals

Each agent carries four forms of capital that determine social position:

- **Economic capital** -- wealth, income, property. Beta-distributed by social class with a Gini target of ~0.32 (FR/DE average). Dynamically shaped by task-based income, technological displacement, health constraints, and board economic interests. A welfare-state floor of 0.15 prevents destitution.
- **Cultural capital** -- education, credentials, cultivated taste. Strongly path-dependent on education track (vocational: 0.20, elite: 0.78). The stickiest capital across generations (intergenerational elasticity 0.50).
- **Social capital** -- network position, bridging ties, trust relationships. Derived from actual graph degree. Amplified by institutional memberships and civic participation. Agents with high social capital spread information more readily.
- **Symbolic capital** -- prestige, recognition, authority. Accumulated through board leadership, institutional seniority, and clan reputation. Legitimized by democratic quality, devalued by corruption.

Influence is derived: `0.4 x symbolic + 0.3 x social + 0.2 x economic + 0.1 x cultural`.

### Habitus

Bourdieu's *habitus* -- durable dispositions acquired through socialization:

- **Cultural taste** (-1 popular to +1 legitimate) -- correlated r ~ 0.6 with origin class
- **Risk tolerance** -- U-shaped by class (both extremes show higher tolerance than the anxious middle)
- **Institutional trust** -- peaks in the upper-middle class
- **Class awareness** -- stronger at class extremes

### Coloring the graph

Fourteen color modes reveal different layers of the simulation. Switch between Clan, Politics, Class, Capital, Age, Education, District, Influence, Emergence, Income, Disruption, Media, Health, and Boards.

![Class color mode -- stratification visible in network structure](docs/02-class-view.png)

### Inspecting an individual

Click any node to see the full profile: four capital bars, habitus, personality, task-based economy (income, disruption risk, individual task disruption percentages), media consumption (print/mass/social exposure, media literacy, algorithmic bubble), health (physical, mental, work capacity, stress, chronic conditions), and institutional memberships (named boards and clubs with type, years, leadership status, economic interest, skill currency).

![Agent detail showing capital, habitus, economy, media, health, and institutions](docs/03-agent-detail.png)

---

## Task-Based Economy and Technological Disruption

Each of the 20 occupations is decomposed into 3-5 concrete tasks. Every task sits on three axes (cognitive vs. manual, routine vs. creative, interpersonal vs. solo) that determine its vulnerability to automation per the Autor (2003) framework.

### Four technology waves

| Wave | Adoption | Primary targets |
|---|---|---|
| **Mechanization** | ~95% | Manual routine (assembly, farming) |
| **Digitization** | ~82% | Cognitive routine (data entry, filing) |
| **AI / ML** | ~18% (rapid S-curve) | Cognitive routine AND creative (writing, coding, diagnosis) |
| **Robotics** | ~8% | Manual routine and some manual creative |

### Income and Disruption color modes

![Income color mode -- green gradient shows earning power](docs/15-income-color.png)

![Disruption color mode -- red gradient shows automation displacement risk](docs/16-displacement-color.png)

### Economy-environment coupling

Displacement risk feeds unemployment. AI adoption boosts GDP. Task-based income shapes economic capital. Health constrains work capacity and productivity. Board economic interests boost income. Skill currency (which decays 3%/year without refreshment) affects productivity.

![After 15 years -- disruption visible with agent detail showing task disruption](docs/18-disruption-10yr.png)

---

## Health System

Social determinants of health (Marmot 2005, WHO CSDH 2008): health outcomes are shaped by class, education, social networks, economic security, and working conditions -- not just biology.

### Per-agent health

- **Physical health** -- class gradient: each step up the class ladder means systematically better health. Declines with age, worsened by chronic conditions.
- **Mental health** -- buffered by social capital (Berkman & Syme 1979), eroded by displacement stress and job insecurity (Case & Deaton 2015, "deaths of despair").
- **Chronic conditions** -- age-dependent onset with class-weighted risk (lower class = 1.5x). Once developed, managed through healthcare access and health literacy.
- **Work capacity** -- derived from physical health, mental health, and disability. Directly constrains economic productivity.
- **Stress** -- accumulated from displacement risk, low satisfaction, economic insecurity. Buffered by social capital and economic security.

### Health color mode

![Health color mode -- red-yellow-green gradient shows overall health composite](docs/19-health-color.png)

### Health environment indicators

Four macro indicators: healthcare access, life expectancy index, mental health index, and health inequality. Mental health tracks social cohesion and unemployment. Health inequality is moderated by healthcare access.

---

## Institutional Memberships

Agents participate in institutions beyond family and workplace. These create cross-cutting ties, concentrate power through interlocking directorates, generate economic interests, and shape capital accumulation.

### Eight institution types

| Type | Prestige | Economic benefit | Access pattern |
|---|---|---|---|
| **Professional boards** | Very high | High (board fees, deals) | Upper class, high economic capital |
| **Civic associations** | Moderate | Low | Broad, especially middle class |
| **Cultural clubs** | Moderate | Low | Education-driven, cultural capital |
| **Social clubs** | High | Moderate (networking) | Class-stratified, referral-based |
| **Political organizations** | Low-moderate | Low | Politically active agents |
| **Religious communities** | Low | Low (high social) | Broad, especially lower/middle |
| **Industry bodies** | Moderate | Moderate | Occupation-driven |
| **Alumni networks** | Moderate | Moderate | Education-track driven |

40+ named institutions (e.g., "City Development Corp", "Arts Patronage Circle", "Metropolitan Club", "Finance Roundtable"). Agents join 0-4 institutions based on occupation affinity, class, education, and interests.

### Interlocking directorates (Mizruchi 1996)

Shared board membership creates network ties with aligned economic interests. Leadership roles emerge with seniority and concentrate board power. Agents who sit on multiple professional boards accumulate disproportionate symbolic and economic capital.

### Boards color mode

![Boards color mode -- orange gradient shows board power and membership count](docs/20-institutions-color.png)

### Skill currency and lifelong learning

Skills decay ~3% per year without refreshment. Lifelong learning propensity (driven by education and age) and institutional membership (alumni networks, industry bodies) offset this decay. Skill currency directly affects productivity.

---

## Media Dynamics

Three media ecosystems shape how information flows, opinions form, and events propagate.

- **Print media** -- declining reach (~2.5%/yr), high trust, analytical depth. Pulls opinions toward moderation.
- **Mass media** -- broad reach, homogenizes opinions toward mainstream consensus. Rising sensationalism.
- **Social media** -- growing toward 95% saturation, echo chambers deepen with engagement, polarization amplifier, viral dynamics.

### Media color mode

![Media color mode -- purple gradient shows social media exposure and algorithmic bubble](docs/17-media-color.png)

Each agent has a media consumption profile (print/mass/social exposure, media literacy, algorithmic bubble depth) shaped by age, education, class, and social capital. Media amplifies or dampens event propagation per agent.

---

## Events and Influence Propagation

Events ripple through the social graph via a BFS cascade with decay. Reaction strength depends on capital field relevance, political alignment, habitus disposition, social capital threshold, clan loyalty, and media amplification.

![Event propagation -- a tech boom cascading through the network](docs/04-event-propagation.png)

![Post-event state with all dashboard panels populated](docs/05-post-event.png)

### Bridge agents

Betweenness centrality identifies structural-hole brokers.

![Bridge agents -- the structural holes between communities](docs/06-bridge-agents.png)

---

## Macro-Environment

26 time-varying indicators across 7 domains, all bidirectionally coupled with agents.

| Domain | Indicators |
|---|---|
| **Economy** | GDP growth, unemployment, inflation, business confidence |
| **Housing** | Price index, vacancy rate, rent burden, construction |
| **Migration** | Net migration, diversity, integration |
| **Culture** | Cultural spending, social cohesion, media pluralism |
| **Governance** | Public spending, corruption, policy stability, democratic quality |
| **Health** | Healthcare access, life expectancy, mental health index, health inequality |
| **Institutions** | Education quality, vocational training, civic participation, associational density |

![After 5 years -- capital color mode with all dashboard panels populated](docs/07-environment-tick.png)

---

## Emergent Properties

Thirteen macro-phenomena computed from micro-level interactions, with bidirectional coupling, downward causation, adaptive network rewiring, norm emergence, and Schelling segregation.

![Emergence color mode -- agents colored by catalyst score](docs/12-emergence-color.png)

| # | Dimension | Research basis |
|---|---|---|
| 1 | Polarization | Esteban & Ray 1994 |
| 2 | Inequality | Piketty 2014, Merton 1968 |
| 3 | Collective Intelligence | Woolley et al. 2010 |
| 4 | Contagion Risk | Watts 2002 |
| 5 | Network Resilience | Barabasi 2002 |
| 6 | Phase Transitions | Granovetter 1978 |
| 7 | Echo Chambers | Sunstein 2001 |
| 8 | Power Law | Barabasi & Albert 1999 |
| 9 | Institutional Trust | Putnam 2000 |
| 10 | Cultural Convergence | Henrich 2015 |
| 11 | Information Integration | Rosas et al. 2020 |
| 12 | Norm Emergence | Axelrod 1986 |
| 13 | Segregation | Schelling 1971 |

Per-agent emergence attribution (catalyst vs. constrained scores), critical slowing down detection, and inter-dimension coupling.

![Agent detail showing economy, media, health, institutions, and emergence](docs/14-agent-emergence-detail.png)

---

## Exportable Artifacts

Seven print-quality visualizations rendered to canvas in a scientific engraving aesthetic -- ivory paper, fine ink lines, crosshatching, stipple, serif typography. All exportable as PNG or PDF at up to A2 300dpi. **Designed for pen-plotter output**: all marks are strokes, stipple dots, or hatching -- no gradients, no solid fills, no transparency blending.

### Anatomies of Agency (Plate I)

Each of the city's 80 most influential agents rendered as a unique radial glyph. Four colored quadrant arcs encode capital. Radiating spokes mark interest domains. Inner arc shows health status (green = good, red = poor; X marks chronic conditions). Ochre ticks mark institutional memberships. Core dot sizes by agency. Political lean rotates the glyph. Stipple density encodes network degree. Ink color = clan.

![Anatomies of Agency -- specimen plate with health arcs and institution marks](docs/08-anatomies.png)

### Survey of Influence (Plate II)

Gaussian kernel density estimation rendered as crosshatched elevation bands with marching-squares contour lines. Open circles with survey crosshairs mark agent positions.

![Survey of Influence -- cartographic elevation map](docs/09-topography.png)

### Constellations of Clan (Plate III)

Ivory-paper star chart. Each clan forms a constellation connected by minimum-spanning-tree lines. Horizontal axis = political leaning. Vertical axis = influence. Open circles with stipple halos. Cross-flares mark high-influence agents (8-point stars for the most influential). Ruled survey grid. Fully pen-plotter compatible.

![Constellations of Clan -- pen-plotter star chart on ivory](docs/10-constellation.png)

### Pulse of the City (Plate VI)

Seven domain strips (economy, housing, migration, culture, governance, health, institutions) showing all 26 environment indicators as overlapping ink traces with diagonal crosshatch fill below lead traces.

![Pulse of the City -- 7-domain time-series](docs/11-citypulse.png)

### Observatory of Emergence (Plate VII)

13-dimension radar chart with crosshatch-filled polygon (no solid fills), historical overlays, side panels with ruled-line backgrounds, coupling web, temporal sparklines.

![Observatory of Emergence -- pen-plotter radar with hatched fill](docs/13-emergence.png)

### Additional artifacts

- **Fabric of Opinion** (Plate IV) -- woven-textile grid of opinions by clan and topic. Crosshatch only.
- **Seismograph of Events** (Plate V) -- cascade amplitude waveforms. Pure line work.

---

## Architecture

```
health.py        -- Social determinants of health: per-agent physical,
                    mental, stress, work capacity, chronic conditions.
                    Marmot class gradient, Berkman social buffering,
                    Case & Deaton displacement stress.
institutions.py  -- 8 institution types (boards, clubs, associations),
                    40+ named institutions, interlocking directorates,
                    leadership emergence, skill currency, lifelong
                    learning, civic participation, board power.
economy.py       -- 20 occupations x 3-5 tasks, 4 tech waves,
                    Autor framework, S-curve adoption, per-agent
                    disruption, income, productivity.
media.py         -- Print/mass/social media ecosystems, per-agent
                    consumption, algorithmic bubbles, echo chambers,
                    media-event amplification.
emergence.py     -- 13-dimension emergent properties, downward
                    causation, adaptive rewiring, norms, Schelling
                    segregation, coupling matrix, critical slowing.
environment.py   -- 26 indicators across 7 domains, endogenous
                    dynamics, bidirectional agent coupling.
capital.py       -- Bourdieu's four capitals, habitus, lifecycle,
                    intergenerational transmission.
model.py         -- Agent dataclass, city generator (1,000 agents,
                    9 edge types), D3 export.
events.py        -- Capital-aware BFS propagation, media amplification,
                    coalition detection.
server.py        -- FastAPI REST + WebSocket, 35+ endpoints.
static/          -- D3.js frontend (14 color modes, 7 pen-plotter
                    artifacts, 6-panel dashboard, A2 print export).
```

## API

| Endpoint | Description |
|---|---|
| `GET /api/graph` | Full graph (nodes with all agent systems, edges with types) |
| `GET /api/stats` | Network statistics + class distribution + capital averages |
| `GET /api/agent/{id}` | Agent detail (all systems + neighbors + emergence) |
| `GET /api/search` | Search by name, clan, district, politics |
| `GET /api/meta` | All metadata (clans, districts, occupations, institution types, etc.) |
| `POST /api/event` | Trigger event with media-amplified propagation |
| `POST /api/tick` | Advance 1-10 years (economy, media, health, institutions, emergence) |
| `POST /api/reset` | Reset with new seed |
| `GET /api/economy` | Tech state, aggregate stats, per-occupation breakdown |
| `GET /api/economy/occupations` | Task decomposition for all 20 occupations |
| `GET /api/media` | Media landscape + consumption statistics |
| `GET /api/health` | Aggregate health stats with class breakdown |
| `GET /api/institutions` | Institutional stats + top institutions by membership |
| `GET /api/institutions/types` | Institution type profiles and named instances |
| `GET /api/environment` | Current 26 macro indicators |
| `GET /api/emergence` | 13-dimension emergence state with coupling and warnings |
| `WS /ws` | WebSocket for live propagation animation |
