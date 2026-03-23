# CivGraph Scalability Audit

**Date:** 2026-03-23
**Scope:** Analyze how the architecture scales with agent count (N), interactions (edges E), agent properties (P), and simulation ticks (T).

---

## Executive Summary

The current architecture works well at its design point (N=500, ~2500 edges, ~20 topics, low tick counts). However, it contains **multiple O(N²) bottlenecks**, **unbounded state growth**, and **per-tick compute that scales with the product of N × E × P**. At 5,000+ agents, 50+ topics, or 100+ ticks, performance will degrade significantly. The core mathematical model (NetworkX graph + Python dicts for per-agent state) is sound for small-to-medium scale but needs structural changes to support larger simulations.

---

## 1. Complexity Analysis by Module

### 1.1 Graph Generation (`model.py: generate_city`)

| Operation | Current Complexity | Bottleneck at Scale? |
|---|---|---|
| Clan bonds (ring + shortcuts) | O(N) | No |
| District neighbors | O(N × d_district) | Mild — d_district grows with N |
| Professional ties | O(N × d_occupation) | Mild |
| **Political alliances** | **O(N²)** | **Yes** — full scan of all agents per candidate (line 329-338) |
| **Shared-interest friendships** | **O(N²)** | **Yes** — full scan with set intersection (line 341-351) |
| **Rivalries** | **O(N²)** | **Yes** — full scan with multi-condition filter (line 355-364) |
| Hub connectors | O(30²) = O(1) | No — fixed top-30 |
| Habitus affinity | O(N × 20) = O(N) | No — sampled to 20 |

**Impact at N=5000:** The three O(N²) loops become ~25M iterations each. Generation would go from <1s to ~15-30s.

**Fix:** Spatial indexing / locality-sensitive hashing. For political alliances, partition agents into political buckets and only scan within ±1. For interest-based friendships, use an inverted interest index. For rivalries, only compare within influence bands.

### 1.2 Event Propagation (`events.py: propagate_event`)

| Operation | Complexity | Notes |
|---|---|---|
| BFS cascade | O(V + E) per event | Scales well |
| `_reaction_strength` | O(1) per agent | Good |
| `opinion_summary` | O(N) | Good |
| `find_bridges` (betweenness_centrality) | **O(N × E)** | **NetworkX unweighted: O(NE), weighted: O(NE + N² log N)** |
| `find_coalitions` | O(N + E) per topic | Good |

**Critical issue:** `find_bridges()` calls `nx.betweenness_centrality(G, weight="weight")` which is O(N × E) ≈ O(N² × avg_degree). At N=5000 with avg_degree ~10, this is ~250M operations. At N=50,000 it becomes infeasible.

**Fix:** Use approximate betweenness (`nx.betweenness_centrality(G, k=100)` — sample k nodes) or switch to a faster algorithm (Brandes with sampling).

### 1.3 Environment Coupling (`environment.py`)

| Operation | Complexity | Notes |
|---|---|---|
| `environment_affect_agents` | O(N) | Good |
| `agents_affect_environment` | O(N + Σ opinions) | **Grows with opinions** |
| `advance_environment` per year | O(N) | Good |

**Subtle issue:** `agents_affect_environment` iterates all agents' `opinion_state` values (line 308-312). As topics accumulate, this grows to O(N × T) where T is the number of topics that have been introduced via events. There's **no mechanism to decay or prune old opinion state**, so T grows monotonically.

### 1.4 Emergence Computations (`emergence.py`)

This is where the scalability problems concentrate. The `EmergenceTracker.snapshot()` runs **all 13 dimensions** on every tick:

| Dimension | Complexity | Key Operations |
|---|---|---|
| Polarization | O(N + 7² + N×T) | Esteban-Ray over 7 categories is fine; topic loop is O(N×T) |
| Inequality | O(N log N) | Gini sort |
| Collective Intelligence | O(N + E + **50 × BFS**) | `single_source_shortest_path_length` on 50 nodes: O(50 × (V+E)) |
| Contagion Susceptibility | O(N + **5 × BFS**) | 5-hub BFS cutoff=3 |
| **Network Resilience** | **O(N + E) × 3** | **Graph copy + connected_components + articulation_points** |
| Phase Transitions | O(N × T) | Topic iteration |
| **Echo Chambers** | **O(E + N×T + T × modularity)** | **Modularity is O(N+E) per topic** → O(T×(N+E)) |
| Power Law | O(N log N) | Sort + OLS regression |
| Institutional Trust | O(N + E) | Good |
| Cultural Convergence | O(N + min(500, E)) | Sampled — good |
| **Information Theoretic** | **O(min(800,E) × T + 100 × d × T)** | **Transfer entropy + synergy loops** |
| Norm Emergence | O(N + N×norms) | Grows with norm count |
| **Segregation** | O(N + N × clans × districts) | **Cross-product of categorical variables** |

**Per-tick total for emergence snapshot:** roughly O(N × T × (E/N)) = **O(E × T)**, plus several O(N + E) graph algorithms.

**At N=5000, T=20 topics, avg_degree=10:**
- E ≈ 25,000
- Echo chambers: 20 × (5000 + 25,000) = 600K
- Info theoretic: 800 × 20 + 100 × 10 × 20 = 36K
- Network resilience: 3 × 30K = 90K
- Total snapshot: ~1-2M operations → ~0.5-1s per tick

**At N=50,000, T=50 topics, avg_degree=15:**
- E ≈ 375,000
- Echo chambers: 50 × 425,000 = 21M
- Total snapshot: ~50-100M operations → **10-30s per tick**

### 1.5 Per-Tick Dynamics (`advance_emergence_dynamics`)

| Step | Complexity | Notes |
|---|---|---|
| Downward causation | O(N) | Good |
| **Adaptive rewiring** | O(N × rate × 15) + **O(N)** recompute | The recompute of social capital for ALL nodes (line 1267) runs even if only 5% rewired |
| **Norm evolution** | **O(N × d × T)** | **For each node, for each active topic, iterates neighbors** |
| Schelling step | O(N × d + movers × 10 × 30) | Moderate |

**Critical bottleneck: `evolve_norms`** at line 1281. For each of N agents, it gathers active topics from up to 10 neighbors (line 1309), then for each topic iterates all neighbors again for weighted averaging (line 1317). This is **O(N × d × T)** where d is average degree and T is number of active topics/norms.

**With N=5000, d=10, T=30:** 5000 × 10 × 30 = 1.5M iterations per tick — manageable.
**With N=50,000, d=15, T=50:** 50,000 × 15 × 50 = **37.5M iterations per tick** — problematic.

### 1.6 Memory & State Growth

| State | Growth Pattern | Bounded? |
|---|---|---|
| `agent.opinion_state` | Grows by 1 entry per new event topic | **No** — never pruned |
| `agent.norms` | Grows per norm evolution tick | **No** — accumulates every active topic |
| `EmergenceTracker.history` | 1 snapshot per tick | **No** — stores full `agent_scores` dict (N × 4 floats) per snapshot |
| `EVENT_HISTORY` | Capped at 200 | Yes |
| Edge count | **Monotonically increasing** | **No** — `adaptive_rewire` adds more than it removes (triadic closure is additive) |

**Memory at 100 ticks with N=5000:**
- `agent_scores`: 100 × 5000 × 4 × 8 bytes ≈ 16 MB (manageable)
- `opinion_state`: If 50 topics accumulate, 5000 × 50 × 24 bytes ≈ 6 MB
- **Edge growth**: Starting at 25K edges, if triadic closure adds ~50 edges/tick over 100 ticks, we reach ~30K. At 1000 ticks, this could reach 75K+ — the graph densifies, making all O(E) operations progressively slower.

---

## 2. Architectural Scaling Walls

### Wall 1: Python + NetworkX Overhead
NetworkX stores each node/edge as a Python dict-of-dicts. Each edge access involves multiple hash lookups. At 50K+ nodes this becomes the dominant overhead. NumPy/scipy sparse matrices would be 10-100× faster for graph algorithms.

### Wall 2: Monolithic Tick
Every tick runs the full pipeline: environment coupling → emergence dynamics → full 13-dimension snapshot. There's no way to run a "light" tick or skip dimensions that haven't changed much. The snapshot alone costs O(E × T) per tick.

### Wall 3: No Incremental Computation
Every emergence dimension recomputes from scratch each tick. For dimensions like Gini (inequality), if only 5% of agents' capital changed, we're still sorting all N values. Echo chambers recompute modularity for every topic even if opinions haven't shifted.

### Wall 4: Unbounded State Accumulation
Opinion states, norms, and edge counts grow without bound. Over long simulations, the inner loops that iterate "all topics" or "all norms" become progressively more expensive.

---

## 3. Scaling Recommendations

### Tier 1: Low-effort, high-impact (keep current model)

1. **Index political alliances and friendships by bucket** in `generate_city`. Replace O(N²) scans with dict lookups. Estimated speedup: 10-50× for generation at N=5000.

2. **Approximate betweenness centrality** in `find_bridges`: use `nx.betweenness_centrality(G, k=min(100, N))`. Speedup: N/100× for large graphs.

3. **Prune stale opinion state and norms.** Add a decay/eviction policy: opinions older than K ticks without reinforcement fade to 0 and are removed. This bounds T.

4. **Cap edge growth.** In `adaptive_rewire`, enforce a per-agent max degree (e.g., Dunbar's number ~150). Before adding an edge, check degree and skip if at cap.

5. **Lazy emergence snapshots.** Don't recompute all 13 dimensions every tick. Use a schedule: heavy dimensions (network resilience, echo chambers, info-theoretic) every 5 ticks; lightweight ones (inequality, polarization) every tick.

6. **Prune `EmergenceTracker.history`:** Drop `agent_scores` from old snapshots (keep only composites + coupled_composites for trend analysis). This prevents O(N × T_ticks) memory growth.

### Tier 2: Moderate refactor (better mathematical model)

7. **Switch to sparse matrix representation.** Replace NetworkX with scipy.sparse adjacency matrix + NumPy arrays for agent attributes. This enables vectorized computation of:
   - Opinion propagation (sparse matrix–vector multiply instead of BFS loop)
   - Norm averaging (sparse weighted mean per row)
   - Capital updates (vectorized array ops)

   **Estimated speedup: 10-50× for per-tick dynamics.** The event propagation BFS, norm evolution, and environment coupling would all become matrix operations.

8. **Incremental emergence computation.** Track a "dirty set" of agents whose state changed since last tick. Only recompute dimensions that depend on those agents. For graph-global metrics (clustering, modularity), maintain incrementally-updated approximations.

9. **Batch event propagation.** Instead of sequential BFS per event, represent opinions as a dense N × T matrix and propagate via sparse matrix multiplication: `O_new = (1-α)O + α W O` where W is the weighted adjacency matrix. This is the standard DeGroot/Friedkin-Johnsen opinion dynamics model and runs in O(E × T) but with NumPy vectorization (~100× faster than Python loops).

### Tier 3: Architectural rethink (alternative mathematical models)

10. **Mean-field approximation for large N.** Instead of simulating every agent, represent groups (by clan × class × district) as aggregate state vectors. With 20 clans × 5 classes × 10 districts = 1000 groups, the dynamics become a 1000-dimensional ODE system regardless of N. Individual agents are sampled from group distributions only when needed for visualization.

    This is the standard approach in computational sociology for scaling agent-based models: Banisch & Olbrich (2019) "Opinion Polarization by Learning from Social Feedback" show that mean-field approximations of ABMs on networks closely track the full simulation for large N.

11. **Stochastic block model (SBM) for network structure.** Instead of storing the full graph, represent it as a block matrix of connection probabilities between groups. Edge queries become probabilistic: P(edge between agent i in group A and agent j in group B) = p_AB. This reduces storage from O(E) to O(K²) where K is the number of blocks, and enables analytical computation of many emergence metrics (clustering, modularity, betweenness) directly from the block structure.

12. **Continuous-time dynamics.** Replace discrete per-tick updates with an ODE/SDE system where opinion state, capital, and norms evolve continuously. Solve with adaptive-step integrators (RK45 / Euler-Maruyama). This naturally handles variable time scales — fast opinion dynamics and slow capital drift — without wasting compute on unchanged slow variables.

---

## 4. Scaling Projections

| Metric | N=500 (current) | N=5,000 | N=50,000 |
|---|---|---|---|
| Generation time | ~0.5s | ~15s (O(N²) walls) | **~25 min** |
| Per-tick dynamics | ~0.1s | ~1s | **~30s** |
| Emergence snapshot | ~0.2s | ~2s | **~30s** |
| Total per tick | ~0.3s | ~3s | **~60s** |
| Memory (100 ticks) | ~5 MB | ~50 MB | ~500 MB |

With Tier 2 optimizations (sparse matrix + vectorization):

| Metric | N=500 | N=5,000 | N=50,000 |
|---|---|---|---|
| Generation time | ~0.3s | ~2s | ~30s |
| Per-tick total | ~0.05s | ~0.3s | ~3s |
| Memory (100 ticks) | ~3 MB | ~30 MB | ~200 MB |

With Tier 3 (mean-field for K=1000 groups):

| Metric | Any N | Notes |
|---|---|---|
| Per-tick total | ~0.01s | Constant in N |
| Memory | ~10 MB | Constant in N |

---

## 5. Recommendation

**For scaling to N=5,000-10,000:** Implement Tier 1 fixes (2-3 days of work). The model stays conceptually identical; you're just eliminating unnecessary O(N²) scans and bounding state growth.

**For scaling to N=50,000+:** Implement Tier 2 (sparse matrix backbone). The Bourdieusian capital model, habitus, and emergence dimensions all map naturally to matrix operations. The sociological model doesn't need to change — only the computational substrate.

**For city-scale simulation (N=500,000+):** Tier 3 mean-field approach is the only viable path. At this scale, individual agent resolution is both computationally infeasible and sociologically unnecessary — macro dynamics emerge from group-level interactions, which is exactly what Bourdieu's field theory describes.

The current mathematical model (Bourdieusian capital fields + opinion dynamics + Schelling segregation + network co-evolution) is well-chosen and sociologically grounded. The scaling issue is not the model — it's the implementation's reliance on Python-level iteration over individual agents where vectorized or analytical operations would suffice.
