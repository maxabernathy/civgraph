/**
 * CivGraph — D3.js force-directed graph visualization
 *
 * Minimalist, interactive agent-based modeling visualization.
 */

// ── State ───────────────────────────────────────────────────────────────────

let graphData = null;
let simulation = null;
let selectedNode = null;
let colorMode = "clan";
let nodeSizeMultiplier = 1.0;
let linkOpacity = 0.15;
let ws = null;
let eventHistory = [];  // local mirror of fired events

// ── Security: HTML escaping ─────────────────────────────────────────────────

const _escMap = {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"};
function esc(s) {
  if (typeof s !== "string") return String(s);
  return s.replace(/[&<>"']/g, c => _escMap[c]);
}

// Safe fetch wrapper — returns parsed JSON or null on error
async function safeFetch(url, opts) {
  try {
    const r = await fetch(url, opts);
    if (!r.ok) { console.error(`Fetch ${url}: ${r.status}`); return null; }
    return await r.json();
  } catch (e) { console.error(`Fetch ${url}:`, e); return null; }
}

// ── Color palettes ──────────────────────────────────────────────────────────

const clanColors = d3.scaleOrdinal(d3.schemeTableau10.concat(d3.schemePastel1));

const politicsColors = {
  far_left: "#dc2626",
  left: "#ef4444",
  center_left: "#fb923c",
  center: "#94a3b8",
  center_right: "#60a5fa",
  right: "#3b82f6",
  far_right: "#1d4ed8",
};

const districtColors = d3.scaleOrdinal(d3.schemeSet3);

const classColors = {
  lower: "#8b5e3c", lower_middle: "#a0845c", middle: "#94a3b8",
  upper_middle: "#6b8bb5", upper: "#3a5a8c",
};

const phaseColors = {
  education: "#93c5fd", early_career: "#6ee7b7", mid_career: "#fbbf24",
  established: "#f87171", elder: "#a78bfa",
};

function nodeColor(d) {
  if (d.highlighted) return "#fff";
  switch (colorMode) {
    case "clan":
      return clanColors(d.clan);
    case "politics":
      return politicsColors[d.politics] || "#666";
    case "district":
      return districtColors(d.district);
    case "influence":
      return d3.interpolateYlOrRd(d.influence);
    case "class":
      return classColors[d.social_class] || "#666";
    case "capital":
      return d3.interpolateViridis(d.capital_volume);
    case "age":
      return d3.interpolatePlasma((d.age - 18) / 57);
    case "education":
      const edColors = {vocational:"#d97706",applied:"#059669",academic:"#2563eb",elite:"#7c3aed"};
      return edColors[d.education_track] || "#666";
    default:
      return "#4a9eff";
  }
}

function nodeRadius(d) {
  const base = 2 + Math.sqrt(d.influence) * 6 + Math.sqrt(d.degree) * 0.8;
  return base * nodeSizeMultiplier;
}

// ── Init ────────────────────────────────────────────────────────────────────

async function init() {
  // Populate dropdowns
  const meta = await fetch("/api/meta").then((r) => r.json());
  const topicSelect = document.getElementById("event-topic");
  meta.interests.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t.replace(/_/g, " ");
    topicSelect.appendChild(opt);
  });
  ["governance", "trust", "power"].forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    topicSelect.appendChild(opt);
  });

  const clanSelect = document.getElementById("filter-clan");
  meta.clans.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    clanSelect.appendChild(opt);
  });

  const districtSelect = document.getElementById("filter-district");
  meta.districts.forEach((d) => {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = d;
    districtSelect.appendChild(opt);
  });

  // Load graph
  graphData = await fetch("/api/graph").then((r) => r.json());
  const stats = await fetch("/api/stats").then((r) => r.json());
  updateStats(stats);

  buildGraph();
  setupEvents();
  setupArtifacts();
  connectWebSocket();
  loadEnvironment();

  document.getElementById("loading").classList.add("hidden");
}

// ── D3 Force Graph ──────────────────────────────────────────────────────────

let svg, g, linkGroup, nodeGroup, zoomBehavior;

function buildGraph() {
  const container = document.getElementById("graph-container");
  const width = container.clientWidth;
  const height = container.clientHeight;

  svg = d3.select("#graph-svg").attr("viewBox", [0, 0, width, height]);
  svg.selectAll("*").remove();

  // Zoom
  zoomBehavior = d3
    .zoom()
    .scaleExtent([0.1, 8])
    .on("zoom", (event) => {
      g.attr("transform", event.transform);
    });
  svg.call(zoomBehavior);

  g = svg.append("g");
  linkGroup = g.append("g").attr("class", "links");
  nodeGroup = g.append("g").attr("class", "nodes");

  // Scale forces to viewport
  const dim = Math.min(width, height);
  const chargeStrength = -20 - dim * 0.015;

  // Force simulation
  simulation = d3
    .forceSimulation(graphData.nodes)
    .force(
      "link",
      d3
        .forceLink(graphData.links)
        .id((d) => d.id)
        .distance((d) => {
          const w = Math.abs(d.weight);
          return 40 + (1 - w) * 80;
        })
        .strength((d) => Math.abs(d.weight) * 0.3)
    )
    .force("charge", d3.forceManyBody().strength(chargeStrength).distanceMax(dim * 0.5))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius((d) => nodeRadius(d) + 1))
    .alphaDecay(0.02)
    .on("tick", ticked);

  renderLinks();
  renderNodes();
}

function renderLinks() {
  const link = linkGroup
    .selectAll("line")
    .data(graphData.links, (d) => d.source.id + "-" + d.target.id);

  link.exit().remove();

  link
    .enter()
    .append("line")
    .attr("class", (d) => "link" + (d.rel === "rivalry" ? " rivalry" : ""))
    .attr("stroke", (d) => {
      if (d.weight < 0) return "#f87171";
      return "#4a9eff";
    })
    .attr("stroke-width", (d) => Math.max(0.5, Math.abs(d.weight) * 2))
    .attr("stroke-opacity", linkOpacity);
}

function renderNodes() {
  const node = nodeGroup
    .selectAll("g.node")
    .data(graphData.nodes, (d) => d.id);

  node.exit().remove();

  const enter = node.enter().append("g").attr("class", "node");

  enter
    .append("circle")
    .attr("r", nodeRadius)
    .attr("fill", nodeColor)
    .attr("stroke", (d) => d3.color(nodeColor(d)).darker(0.5))
    .on("click", (event, d) => selectAgent(d))
    .on("mouseover", (event, d) => showTooltip(event, d))
    .on("mouseout", hideTooltip)
    .call(drag(simulation));

  node.select("circle").attr("r", nodeRadius).attr("fill", nodeColor);
}

function ticked() {
  linkGroup
    .selectAll("line")
    .attr("x1", (d) => d.source.x)
    .attr("y1", (d) => d.source.y)
    .attr("x2", (d) => d.target.x)
    .attr("y2", (d) => d.target.y);

  nodeGroup
    .selectAll("g.node")
    .attr("transform", (d) => `translate(${d.x},${d.y})`);
}

function drag(sim) {
  return d3
    .drag()
    .on("start", (event, d) => {
      if (!event.active) sim.alphaTarget(0.1).restart();
      d.fx = d.x;
      d.fy = d.y;
    })
    .on("drag", (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on("end", (event, d) => {
      if (!event.active) sim.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    });
}

// ── Tooltip ─────────────────────────────────────────────────────────────────

function showTooltip(event, d) {
  const tooltip = document.getElementById("tooltip");
  tooltip.innerHTML = `
    <div class="name">${esc(d.name)}</div>
    <div class="dim">${esc(d.occupation.replace(/_/g, " "))} · ${esc(d.district)}</div>
    <div>Clan: ${esc(d.clan)} · ${esc(d.politics.replace(/_/g, " "))}</div>
    <div>Influence: ${(d.influence * 100).toFixed(0)}% · ${d.degree} connections</div>
  `;
  tooltip.classList.add("visible");

  const rect = document
    .getElementById("graph-container")
    .getBoundingClientRect();
  tooltip.style.left = event.clientX - rect.left + 12 + "px";
  tooltip.style.top = event.clientY - rect.top - 10 + "px";
}

function hideTooltip() {
  document.getElementById("tooltip").classList.remove("visible");
}

// ── Agent selection ─────────────────────────────────────────────────────────

async function selectAgent(d) {
  selectedNode = d;

  const detail = await fetch(`/api/agent/${d.id}`).then((r) => r.json());
  const neighborIds = new Set(detail.neighbors.map((n) => n.id));
  neighborIds.add(d.id);

  nodeGroup.selectAll("g.node").classed("highlighted", (n) => neighborIds.has(n.id));

  linkGroup.selectAll("line").classed("highlighted", (l) => {
    const sid = typeof l.source === "object" ? l.source.id : l.source;
    const tid = typeof l.target === "object" ? l.target.id : l.target;
    return sid === d.id || tid === d.id;
  });

  const agent = detail.agent;
  const opinions = Object.entries(agent.opinion_state)
    .map(
      ([k, v]) =>
        `<div class="bar-row">
        <span class="bar-label">${esc(k)}</span>
        <div class="bar-track">
          <div class="bar-fill ${v > 0 ? "positive" : v < 0 ? "negative" : "neutral"}"
               style="width:${Math.abs(v) * 100}%; margin-left:${v < 0 ? (100 - Math.abs(v) * 100) + "%" : "0"}"></div>
        </div>
      </div>`
    )
    .join("");

  const cap = agent.capital || {};
  const hab = agent.habitus || {};
  document.getElementById("agent-detail").innerHTML = `
    <div class="agent-card">
      <div class="name">${esc(agent.name)}</div>
      <div class="meta">
        <span class="tag clan">${esc(agent.clan)}</span>
        <span class="tag district">${esc(agent.district)}</span>
        <span class="tag politics">${esc(agent.politics.replace(/_/g, " "))}</span>
        <br>${esc(agent.occupation.replace(/_/g, " "))}
        · age ${agent.age} · ${esc((agent.life_phase || "").replace(/_/g, " "))}
      </div>
      <div class="meta" style="margin-top:6px">
        <div style="color:var(--text-dim);font-size:0.8em;margin-bottom:3px">CAPITAL</div>
        <div class="bar-row"><span class="bar-label">Economic</span><div class="bar-track"><div class="bar-fill positive" style="width:${(cap.economic||0) * 100}%"></div></div></div>
        <div class="bar-row"><span class="bar-label">Cultural</span><div class="bar-track"><div class="bar-fill" style="width:${(cap.cultural||0) * 100}%;background:#a78bfa"></div></div></div>
        <div class="bar-row"><span class="bar-label">Social</span><div class="bar-track"><div class="bar-fill" style="width:${(cap.social||0) * 100}%;background:#38bdf8"></div></div></div>
        <div class="bar-row"><span class="bar-label">Symbolic</span><div class="bar-track"><div class="bar-fill" style="width:${(cap.symbolic||0) * 100}%;background:#fbbf24"></div></div></div>
      </div>
      <div class="meta" style="margin-top:6px">
        <div style="color:var(--text-dim);font-size:0.8em;margin-bottom:3px">HABITUS</div>
        <div style="font-size:0.85em">
          Class: ${esc((hab.current_class||"").replace(/_/g," "))}
          (origin: ${esc((hab.origin_class||"").replace(/_/g," "))})
          <br>Education: ${esc((hab.education_track||"").replace(/_/g," "))}
          · Taste: ${(hab.cultural_taste||0) > 0 ? "legitimate" : "popular"} (${(hab.cultural_taste||0).toFixed(2)})
        </div>
      </div>
      <div class="meta" style="margin-top:6px">
        <div style="color:var(--text-dim);font-size:0.8em;margin-bottom:3px">PERSONALITY</div>
        <div class="bar-row"><span class="bar-label">Openness</span><div class="bar-track"><div class="bar-fill neutral" style="width:${agent.openness * 100}%"></div></div></div>
        <div class="bar-row"><span class="bar-label">Assertive</span><div class="bar-track"><div class="bar-fill neutral" style="width:${agent.assertiveness * 100}%"></div></div></div>
        <div class="bar-row"><span class="bar-label">Loyalty</span><div class="bar-track"><div class="bar-fill neutral" style="width:${agent.loyalty * 100}%"></div></div></div>
      </div>
      <div style="margin-top:6px;font-size:0.85em;color:var(--text-dim)">
        Interests: ${agent.interests.map((i) => esc(i.replace(/_/g, " "))).join(", ")}
      </div>
    </div>

    ${opinions ? `<h2>Opinions</h2>${opinions}` : ""}

    <h2>Connections (${detail.neighbors.length})</h2>
    <ul class="neighbor-list">
      ${detail.neighbors
        .sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight))
        .slice(0, 30)
        .map(
          (n) =>
            `<li data-agent-id="${esc(n.id)}">
              <span>${esc(n.name)}</span>
              <span class="rel">${esc(n.rel)} (${n.weight > 0 ? "+" : ""}${n.weight.toFixed(2)})</span>
            </li>`
        )
        .join("")}
    </ul>
  `;

  // Event delegation for neighbor clicks (replaces inline onclick)
  document.querySelectorAll("#agent-detail .neighbor-list li[data-agent-id]").forEach((li) => {
    li.addEventListener("click", () => selectAgentById(li.dataset.agentId));
  });

  document.getElementById("btn-fire-event").textContent = `Fire Event from ${agent.name}`;
}

function selectAgentById(id) {
  const node = graphData.nodes.find((n) => n.id === id);
  if (node) selectAgent(node);
}

// ── Filters ─────────────────────────────────────────────────────────────────

function applyFilters() {
  const search = document.getElementById("filter-search").value.toLowerCase();
  const clan = document.getElementById("filter-clan").value;
  const district = document.getElementById("filter-district").value;
  const politics = document.getElementById("filter-politics").value;

  nodeGroup.selectAll("g.node").each(function (d) {
    let visible = true;
    if (search && !d.name.toLowerCase().includes(search)) visible = false;
    if (clan && d.clan !== clan) visible = false;
    if (district && d.district !== district) visible = false;
    if (politics && d.politics !== politics) visible = false;

    d3.select(this).style("opacity", visible ? 1 : 0.05);
  });

  linkGroup.selectAll("line").style("opacity", function (l) {
    const sid = typeof l.source === "object" ? l.source.id : l.source;
    const tid = typeof l.target === "object" ? l.target.id : l.target;
    const sn = graphData.nodes.find((n) => n.id === sid);
    const tn = graphData.nodes.find((n) => n.id === tid);
    if (!sn || !tn) return linkOpacity;
    let sv = true,
      tv = true;
    if (search) {
      sv = sn.name.toLowerCase().includes(search);
      tv = tn.name.toLowerCase().includes(search);
    }
    if (clan) {
      sv = sv && sn.clan === clan;
      tv = tv && tn.clan === clan;
    }
    if (district) {
      sv = sv && sn.district === district;
      tv = tv && tn.district === district;
    }
    if (politics) {
      sv = sv && sn.politics === politics;
      tv = tv && tn.politics === politics;
    }
    return sv && tv ? linkOpacity : 0.02;
  });
}

// ── Events ──────────────────────────────────────────────────────────────────

function setupEvents() {
  // Filters
  document.getElementById("filter-search").addEventListener("input", applyFilters);
  document.getElementById("filter-clan").addEventListener("change", applyFilters);
  document.getElementById("filter-district").addEventListener("change", applyFilters);
  document.getElementById("filter-politics").addEventListener("change", applyFilters);

  // Color mode
  document.querySelectorAll(".color-modes .btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".color-modes .btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      colorMode = btn.dataset.mode;
      nodeGroup
        .selectAll("circle")
        .transition()
        .duration(400)
        .attr("fill", nodeColor)
        .attr("stroke", (d) => d3.color(nodeColor(d)).darker(0.5));
    });
  });

  // Display controls
  document.getElementById("link-opacity").addEventListener("input", (e) => {
    linkOpacity = parseFloat(e.target.value);
    document.getElementById("link-opacity-val").textContent = linkOpacity.toFixed(2);
    linkGroup.selectAll("line").attr("stroke-opacity", linkOpacity);
  });

  document.getElementById("node-size").addEventListener("input", (e) => {
    nodeSizeMultiplier = parseFloat(e.target.value);
    document.getElementById("node-size-val").textContent = nodeSizeMultiplier.toFixed(1);
    nodeGroup.selectAll("circle").attr("r", nodeRadius);
    simulation.force("collision", d3.forceCollide().radius((d) => nodeRadius(d) + 1));
    simulation.alpha(0.3).restart();
  });

  // Sliders in event form
  document.getElementById("event-sentiment").addEventListener("input", (e) => {
    document.getElementById("sentiment-val").textContent = parseFloat(e.target.value).toFixed(1);
  });
  document.getElementById("event-intensity").addEventListener("input", (e) => {
    document.getElementById("intensity-val").textContent = parseFloat(e.target.value).toFixed(1);
  });
  document.getElementById("event-bias").addEventListener("input", (e) => {
    document.getElementById("bias-val").textContent = parseFloat(e.target.value).toFixed(1);
  });

  // Fire event
  document.getElementById("btn-fire-event").addEventListener("click", fireEvent);

  // Find bridges
  document.getElementById("btn-bridges").addEventListener("click", findBridges);

  // Reset
  document.getElementById("btn-reset").addEventListener("click", resetSimulation);

  // Resize handler — rebuild graph on window resize
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (graphData) buildGraph();
    }, 250);
  });
}

async function fireEvent() {
  if (!selectedNode) {
    alert("Select an origin agent first (click a node)");
    return;
  }

  const body = {
    event_type: document.getElementById("event-type").value,
    title: document.getElementById("event-title").value || "Untitled Event",
    origin_agent: selectedNode.id,
    topic: document.getElementById("event-topic").value,
    sentiment: parseFloat(document.getElementById("event-sentiment").value),
    intensity: parseFloat(document.getElementById("event-intensity").value),
    political_bias: parseFloat(document.getElementById("event-bias").value),
    max_steps: parseInt(document.getElementById("event-steps").value),
  };

  const result = await fetch("/api/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => r.json());

  eventHistory.push(result);

  // Refresh opinion data on nodes
  await refreshNodeOpinions();

  // Animate propagation
  await animatePropagation(result);

  // Log it
  addLogEntry(result);
}

async function refreshNodeOpinions() {
  // Fetch fresh graph data to get updated opinion states
  const fresh = await fetch("/api/graph").then((r) => r.json());
  // Merge opinion data into current nodes (keep positions)
  const freshMap = {};
  for (const n of fresh.nodes) freshMap[n.id] = n;
  for (const n of graphData.nodes) {
    const fn = freshMap[n.id];
    if (fn) {
      n._opinions = fn._opinions;
    }
  }
  // Also fetch per-agent opinions for artifact use
  for (const n of graphData.nodes) {
    n._opinions = n._opinions || {};
  }
  // Batch fetch: use the search endpoint to get opinion_state for all agents
  // (more efficient: just re-fetch graph which includes opinion data)
  // The graph endpoint doesn't include opinion_state, so we need the agents endpoint
  // For efficiency, fetch a sample to populate _opinions
  const allAgents = await fetch("/api/search?limit=500").then((r) => r.json());
  const agentMap = {};
  for (const a of allAgents) agentMap[a.id] = a;
  for (const n of graphData.nodes) {
    const a = agentMap[n.id];
    if (a && a.opinion_state) {
      n._opinions = a.opinion_state;
    }
  }
}

async function animatePropagation(event) {
  const affected = new Set();

  for (const step of event.propagation) {
    for (const r of step.results) {
      if (r.activated) {
        affected.add(r.agent_id);
      }
    }

    nodeGroup.selectAll("g.node").each(function (d) {
      if (affected.has(d.id)) {
        d3.select(this)
          .select("circle")
          .transition()
          .duration(300)
          .attr("fill", (d) => {
            const result = step.results.find((r) => r.agent_id === d.id);
            if (!result) return nodeColor(d);
            if (result.stance === "support") return "#4ade80";
            if (result.stance === "oppose") return "#f87171";
            return "#94a3b8";
          })
          .attr("r", (d) => nodeRadius(d) * 1.5);
      }
    });

    await sleep(600);
  }

  await sleep(2000);

  nodeGroup
    .selectAll("circle")
    .transition()
    .duration(800)
    .attr("fill", nodeColor)
    .attr("r", nodeRadius);
}

function addLogEntry(event) {
  const log = document.getElementById("event-log");
  if (log.querySelector("p")) log.innerHTML = "";

  const time = new Date().toLocaleTimeString();
  const entry = document.createElement("div");
  entry.className = "log-entry";
  entry.innerHTML = `
    <span class="time">${esc(time)}</span>
    <span class="event-name"> ${esc(event.title)}</span>
    <div class="impact">
      ${event.total_affected} affected · ${event.steps} steps ·
      topic: ${esc(event.topic)} · sentiment: ${event.sentiment.toFixed(1)}
    </div>
  `;
  log.prepend(entry);
}

async function findBridges() {
  const bridges = await fetch("/api/bridges").then((r) => r.json());
  const bridgeIds = new Set(bridges.map((b) => b.agent.id));

  nodeGroup.selectAll("g.node").classed("highlighted", (d) => bridgeIds.has(d.id));

  document.getElementById("agent-detail").innerHTML = `
    <h2>Bridge Agents</h2>
    <p style="color:var(--text-dim);font-size:0.85em;margin-bottom:8px">
      Agents with highest betweenness centrality — they bridge communities.
    </p>
    <ul class="neighbor-list">
      ${bridges
        .map(
          (b) =>
            `<li data-agent-id="${esc(b.agent.id)}">
              <span>${esc(b.agent.name)}</span>
              <span class="rel">${esc(b.agent.clan)} (${b.betweenness})</span>
            </li>`
        )
        .join("")}
    </ul>
  `;

  // Event delegation for bridge agent clicks
  document.querySelectorAll("#agent-detail .neighbor-list li[data-agent-id]").forEach((li) => {
    li.addEventListener("click", () => selectAgentById(li.dataset.agentId));
  });
}

async function resetSimulation() {
  const seed = Math.floor(Math.random() * 100000);
  await fetch(`/api/reset?seed=${seed}`, { method: "POST" });
  graphData = await fetch("/api/graph").then((r) => r.json());
  const stats = await fetch("/api/stats").then((r) => r.json());
  updateStats(stats);
  buildGraph();
  selectedNode = null;
  eventHistory = [];
  document.getElementById("agent-detail").innerHTML =
    '<p style="color: var(--text-dim)">Click a node to inspect</p>';
  document.getElementById("event-log").innerHTML =
    '<p style="color: var(--text-dim)">No events yet</p>';
  document.getElementById("btn-fire-event").textContent =
    "Fire Event (select origin node first)";
}

// ── Artifacts ───────────────────────────────────────────────────────────────

function setupArtifacts() {
  const modal = document.getElementById("artifact-modal");

  // Artifact buttons
  document.querySelectorAll("[data-artifact]").forEach((btn) => {
    btn.addEventListener("click", () => openArtifact(btn.dataset.artifact));
  });

  // Close
  document.getElementById("btn-close-artifact").addEventListener("click", () => {
    modal.classList.remove("visible");
  });

  // Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") modal.classList.remove("visible");
  });

  // Export buttons
  document.getElementById("btn-export-png").addEventListener("click", () => Artifacts.exportPNG());
  document.getElementById("btn-export-pdf").addEventListener("click", () => Artifacts.exportPDF());

  // Re-render on resolution change
  document.getElementById("res-select").addEventListener("change", () => {
    if (currentArtifact) openArtifact(currentArtifact);
  });
}

let currentArtifact = null;

async function openArtifact(type) {
  currentArtifact = type;
  const modal = document.getElementById("artifact-modal");
  modal.classList.add("visible");

  const titles = {
    anatomies: "ANATOMIES OF AGENCY",
    topography: "SURVEY OF INFLUENCE",
    constellation: "CONSTELLATIONS OF CLAN",
    heatmap: "FABRIC OF OPINION",
    seismograph: "SEISMOGRAPH OF EVENTS",
    citypulse: "PULSE OF THE CITY",
  };
  document.getElementById("artifact-title").textContent = titles[type] || "ARTIFACT";

  // Ensure we have opinion data
  if (type === "heatmap" && eventHistory.length > 0) {
    await refreshNodeOpinions();
  }

  // Small delay to let modal render
  await sleep(50);

  const nodes = graphData.nodes;
  const links = graphData.links;

  switch (type) {
    case "anatomies":
      Artifacts.renderAnatomies(nodes);
      break;
    case "topography":
      Artifacts.renderTopography(nodes);
      break;
    case "constellation":
      Artifacts.renderConstellation(nodes);
      break;
    case "heatmap":
      Artifacts.renderHeatmap(nodes);
      break;
    case "seismograph":
      Artifacts.renderSeismograph(nodes, links, eventHistory);
      break;
    case "citypulse":
      const envHist = await fetch("/api/environment/history").then((r) => r.json());
      const envMetaData = await fetch("/api/environment/meta").then((r) => r.json());
      Artifacts.renderCityPulse(envHist, envMetaData);
      break;
  }
}

// ── WebSocket ───────────────────────────────────────────────────────────────

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "propagation_step") {
      const affected = new Set(data.affected);
      nodeGroup.selectAll("g.node").each(function (d) {
        if (affected.has(d.id)) {
          d3.select(this)
            .select("circle")
            .transition()
            .duration(300)
            .attr("fill", "#4ade80")
            .attr("r", (d) => nodeRadius(d) * 1.3);
        }
      });
    }
  };

  ws.onclose = () => {
    setTimeout(connectWebSocket, 3000);
  };
}

// ── Environment ─────────────────────────────────────────────────────────────

let envMeta = null;

async function loadEnvironment() {
  envMeta = await fetch("/api/environment/meta").then((r) => r.json());
  const env = await fetch("/api/environment").then((r) => r.json());
  renderEnvironment(env);

  document.getElementById("btn-tick").addEventListener("click", advanceTick);
}

function renderEnvironment(env) {
  document.getElementById("env-year").textContent = `Year ${env.year}`;
  const container = document.getElementById("env-gauges");

  if (!envMeta) return;
  const domains = envMeta.domains;
  const meta = envMeta.indicators;

  const domainColors = {
    economy: "#4ade80", housing: "#fbbf24", migration: "#60a5fa",
    culture: "#a78bfa", governance: "#f87171",
  };

  let html = "";
  for (const [domain, keys] of Object.entries(domains)) {
    html += `<div class="env-domain-label">${esc(domain)}</div>`;
    for (const key of keys) {
      const m = meta[key];
      if (!m) continue;
      const val = env.indicators[key] || 0;
      const lo = m.min, hi = m.max;
      const pct = Math.max(0, Math.min(100, ((val - lo) / (hi - lo)) * 100));
      let display = m.format === "pct" ? (val * 100).toFixed(1) + "%" :
                    m.format === "index" ? val.toFixed(2) : val.toFixed(2);
      const color = domainColors[domain] || "var(--accent)";
      html += `<div class="env-gauge">
        <span class="env-gauge-label">${esc(m.label)}</span>
        <div class="env-gauge-track">
          <div class="env-gauge-fill" style="width:${pct}%;background:${color}"></div>
        </div>
        <span class="env-gauge-val">${display}</span>
      </div>`;
    }
  }
  container.innerHTML = html;
}

async function advanceTick() {
  const years = parseInt(document.getElementById("tick-years").value) || 1;
  const result = await fetch("/api/tick", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ years }),
  }).then((r) => r.json());

  if (result && result.current) {
    renderEnvironment(result.current);
  }
  if (result && result.stats) {
    updateStats(result.stats);
  }

  // Refresh graph data to reflect capital changes
  graphData = await fetch("/api/graph").then((r) => r.json());
  // Update node visuals without rebuilding simulation
  nodeGroup.selectAll("circle")
    .transition().duration(500)
    .attr("fill", nodeColor)
    .attr("r", nodeRadius);
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function updateStats(stats) {
  document.getElementById("stat-nodes").textContent = `${stats.nodes} agents`;
  document.getElementById("stat-edges").textContent = `${stats.edges} links`;
  document.getElementById("stat-density").textContent = `density ${stats.density}`;
  document.getElementById("stat-clusters").textContent = `clustering ${stats.avg_clustering}`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ── Boot ────────────────────────────────────────────────────────────────────

window.addEventListener("load", init);
