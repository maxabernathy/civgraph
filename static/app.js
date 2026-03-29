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
let microscopeWin = null;

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
    case "emergence":
      // Use pre-computed emergence_score if available, else approximate
      const emScore = d.emergence_score > 0 ? d.emergence_score :
        Math.min(1, (d.influence * 0.3 + (d.capital?.social || 0) * 0.3 +
        (d.degree / 30) * 0.2 + (d.capital?.cultural || 0) * 0.2));
      return d3.interpolateMagma(0.15 + emScore * 0.75);
    case "income":
      return d3.interpolateGreens(0.15 + (d.income || 0.5) * 0.75);
    case "displacement":
      return d3.interpolateReds(0.1 + (d.displacement_risk || 0) * 0.85);
    case "media":
      // Social media exposure + algorithmic bubble
      const mediaScore = Math.min(1, (d.social_media_exposure || 0.5) * 0.6 + (d.algorithmic_bubble || 0) * 0.4);
      return d3.interpolatePurples(0.15 + mediaScore * 0.75);
    case "health":
      return d3.interpolateRdYlGn(d.health_composite || 0.75);
    case "institutions":
      // Board power + membership count
      const instScore = Math.min(1, (d.board_power || 0) * 0.6 + (d.membership_count || 0) / 4 * 0.4);
      return d3.interpolateOranges(0.15 + instScore * 0.75);
    case "agency":
      // OPP score (obligatory passage point — Callon/Latour)
      return d3.interpolateCividis(0.1 + Math.min(1, (d.opp_score || 0) * 2) * 0.85);
    default:
      return "#4a9eff";
  }
}

// Scale factor based on agent count — smaller nodes at higher N
let densityScale = 1.0;

function nodeRadius(d) {
  const base = (1.5 + Math.sqrt(d.influence) * 4 + Math.sqrt(d.degree) * 0.5) * densityScale;
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
  loadEconomyMedia();

  document.getElementById("loading").classList.add("hidden");
}

// ── D3 Force Graph ──────────────────────────────────────────────────────────

let svg, g, linkGroup, nodeGroup, zoomBehavior;
let visibleLinks = null; // subset of links to render (null = all)

function buildGraph() {
  const container = document.getElementById("graph-container");
  const width = container.clientWidth;
  const height = container.clientHeight;

  const nNodes = graphData.nodes.length;
  const nLinks = graphData.links.length;

  // Density-aware scaling: smaller nodes and weaker forces at high N
  densityScale = Math.min(1.0, Math.sqrt(1000 / nNodes));
  // Adaptive link opacity: lower at high edge counts
  linkOpacity = Math.min(0.15, 150 / Math.max(1, nLinks));
  document.getElementById("link-opacity").value = linkOpacity;
  document.getElementById("link-opacity-val").textContent = linkOpacity.toFixed(2);

  // Only render a fraction of edges when there are too many
  visibleLinks = graphData.links;
  if (nLinks > 15000) {
    const sorted = [...graphData.links].sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight));
    const cutoff = Math.floor(nLinks * 0.3);
    const kept = new Set(sorted.slice(0, cutoff));
    visibleLinks = graphData.links.filter(l => kept.has(l) || l.weight < 0);
  }

  svg = d3.select("#graph-svg").attr("viewBox", [0, 0, width, height]);
  svg.selectAll("*").remove();

  // Zoom
  zoomBehavior = d3
    .zoom()
    .scaleExtent([0.05, 12])
    .on("zoom", (event) => {
      g.attr("transform", event.transform);
    });
  svg.call(zoomBehavior);

  g = svg.append("g");
  linkGroup = g.append("g").attr("class", "links");
  nodeGroup = g.append("g").attr("class", "nodes");

  // Scale forces to viewport and agent count
  const dim = Math.min(width, height);
  const chargeStrength = (-15 - dim * 0.01) * (1 + Math.log10(nNodes / 500));
  const linkDistScale = 0.5 + 500 / nNodes;  // shorter distances at high N

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
          return (30 + (1 - w) * 60) * linkDistScale;
        })
        .strength((d) => Math.abs(d.weight) * 0.2)
    )
    .force("charge", d3.forceManyBody().strength(chargeStrength).distanceMax(dim * 0.5))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius((d) => nodeRadius(d) + 0.5 * densityScale))
    .alphaDecay(nNodes > 2000 ? 0.04 : 0.02)
    .on("tick", ticked);

  renderLinks();
  renderNodes();
}

function renderLinks() {
  const linksToRender = visibleLinks || graphData.links;
  const link = linkGroup
    .selectAll("line")
    .data(linksToRender, (d) => (d.source.id || d.source) + "-" + (d.target.id || d.target));

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
  const emLine = d.emergence_score > 0
    ? `<div class="dim">Emergence: ${(d.emergence_score * 100).toFixed(0)}% · Sat: ${(d.satisfaction * 100).toFixed(0)}%${d.norm_count ? ` · ${d.norm_count} norms` : ""}</div>`
    : "";
  const econLine = d.income !== undefined
    ? `<div class="dim">Income: ${(d.income * 100).toFixed(0)}% · Disruption: ${((d.displacement_risk || 0) * 100).toFixed(0)}%</div>`
    : "";
  const mediaLine = d.social_media_exposure !== undefined
    ? `<div class="dim">Social media: ${((d.social_media_exposure || 0) * 100).toFixed(0)}%${d.algorithmic_bubble > 0.01 ? ` · Bubble: ${(d.algorithmic_bubble * 100).toFixed(0)}%` : ""}</div>`
    : "";
  const healthLine = d.health_composite !== undefined
    ? `<div class="dim">Health: ${((d.health_composite || 0.75) * 100).toFixed(0)}%${d.chronic_condition ? ' · Chronic' : ''}${d.membership_count ? ` · ${d.membership_count} memberships` : ""}${d.opp_score > 0.3 ? ' · OPP' : ''}</div>`
    : "";
  tooltip.innerHTML = `
    <div class="name">${esc(d.name)}</div>
    <div class="dim">${esc(d.occupation.replace(/_/g, " "))} · ${esc(d.district)}</div>
    <div>Clan: ${esc(d.clan)} · ${esc(d.politics.replace(/_/g, " "))}</div>
    <div>Influence: ${(d.influence * 100).toFixed(0)}% · ${d.degree} connections</div>
    ${econLine}${mediaLine}${healthLine}${emLine}
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
      ${agent.economy ? `
      <div class="meta" style="margin-top:6px">
        <div style="color:var(--text-dim);font-size:0.8em;margin-bottom:3px">ECONOMY</div>
        <div class="bar-row"><span class="bar-label">Income</span><div class="bar-track"><div class="bar-fill positive" style="width:${(agent.economy.income||0) * 100}%"></div></div></div>
        <div class="bar-row"><span class="bar-label">Disruption</span><div class="bar-track"><div class="bar-fill negative" style="width:${(agent.economy.displacement_risk||0) * 100}%"></div></div></div>
        <div class="bar-row"><span class="bar-label">Productivity</span><div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, (agent.economy.productivity||1) / 3 * 100)}%;background:#38bdf8"></div></div></div>
        <div class="bar-row"><span class="bar-label">Adaptation</span><div class="bar-track"><div class="bar-fill" style="width:${(agent.economy.tech_adaptation||0) * 100}%;background:#a78bfa"></div></div></div>
        <div style="font-size:0.75em;color:var(--text-dim);margin-top:3px">
          Tasks: ${agent.economy.tasks ? agent.economy.tasks.map(t => esc(t.name.replace(/_/g," ")) + (t.disruption > 0.1 ? ' <span style="color:var(--negative)">(' + (t.disruption*100).toFixed(0) + '%)</span>' : '')).join(", ") : "—"}
        </div>
      </div>` : ""}
      ${agent.media ? `
      <div class="meta" style="margin-top:6px">
        <div style="color:var(--text-dim);font-size:0.8em;margin-bottom:3px">MEDIA</div>
        <div class="bar-row"><span class="bar-label">Print</span><div class="bar-track"><div class="bar-fill" style="width:${(agent.media.print_exposure||0) * 100}%;background:#94a3b8"></div></div></div>
        <div class="bar-row"><span class="bar-label">Mass</span><div class="bar-track"><div class="bar-fill" style="width:${(agent.media.mass_exposure||0) * 100}%;background:#fbbf24"></div></div></div>
        <div class="bar-row"><span class="bar-label">Social</span><div class="bar-track"><div class="bar-fill" style="width:${(agent.media.social_exposure||0) * 100}%;background:#8b5cf6"></div></div></div>
        <div class="bar-row"><span class="bar-label">Literacy</span><div class="bar-track"><div class="bar-fill" style="width:${(agent.media.media_literacy||0) * 100}%;background:#5ad49a"></div></div></div>
        ${agent.media.algorithmic_bubble > 0.01 ? `<div class="bar-row"><span class="bar-label">Bubble</span><div class="bar-track"><div class="bar-fill negative" style="width:${(agent.media.algorithmic_bubble||0) * 100}%"></div></div></div>` : ""}
      </div>` : ""}
      ${agent.health ? `
      <div class="meta" style="margin-top:6px">
        <div style="color:var(--text-dim);font-size:0.8em;margin-bottom:3px">HEALTH</div>
        <div class="bar-row"><span class="bar-label">Physical</span><div class="bar-track"><div class="bar-fill positive" style="width:${(agent.health.physical_health||0) * 100}%"></div></div></div>
        <div class="bar-row"><span class="bar-label">Mental</span><div class="bar-track"><div class="bar-fill" style="width:${(agent.health.mental_health||0) * 100}%;background:#60a5fa"></div></div></div>
        <div class="bar-row"><span class="bar-label">Work Cap.</span><div class="bar-track"><div class="bar-fill" style="width:${(agent.health.work_capacity||0) * 100}%;background:#fbbf24"></div></div></div>
        <div class="bar-row"><span class="bar-label">Stress</span><div class="bar-track"><div class="bar-fill negative" style="width:${(agent.health.stress_level||0) * 100}%"></div></div></div>
        <div style="font-size:0.75em;color:var(--text-dim);margin-top:2px">
          ${agent.health.chronic_condition ? '<span style="color:var(--negative)">Chronic condition</span> · ' : ''}
          Literacy: ${((agent.health.health_literacy||0)*100).toFixed(0)}%
          · Access: ${((agent.health.healthcare_access||0)*100).toFixed(0)}%
        </div>
      </div>` : ""}
      ${agent.institutions && agent.institutions.memberships && agent.institutions.memberships.length > 0 ? `
      <div class="meta" style="margin-top:6px">
        <div style="color:var(--text-dim);font-size:0.8em;margin-bottom:3px">INSTITUTIONS (${agent.institutions.membership_count})</div>
        ${agent.institutions.memberships.map(m => `
          <div style="font-size:0.75em;margin-bottom:2px">
            <span style="color:var(--accent)">${esc(m.name)}</span>
            <span style="color:var(--text-dim)"> · ${esc(m.type.replace(/_/g," "))}${m.leadership ? ' · <span style="color:var(--accent3)">Leader</span>' : ''} · ${m.years_active}y</span>
            ${m.economic_interest > 0.1 ? `<span style="color:var(--accent2)"> · econ: ${(m.economic_interest*100).toFixed(0)}%</span>` : ""}
          </div>
        `).join("")}
        <div class="bar-row" style="margin-top:3px"><span class="bar-label">Skills</span><div class="bar-track"><div class="bar-fill" style="width:${(agent.institutions.skill_currency||0) * 100}%;background:#38bdf8"></div></div></div>
        <div class="bar-row"><span class="bar-label">Learning</span><div class="bar-track"><div class="bar-fill" style="width:${(agent.institutions.lifelong_learning||0) * 100}%;background:#a78bfa"></div></div></div>
        ${agent.institutions.board_power > 0 ? `<div class="bar-row"><span class="bar-label">Board Pwr</span><div class="bar-track"><div class="bar-fill" style="width:${(agent.institutions.board_power||0) * 100}%;background:#fbbf24"></div></div></div>` : ""}
      </div>` : ""}
      <div style="margin-top:6px;font-size:0.85em;color:var(--text-dim)">
        Interests: ${agent.interests.map((i) => esc(i.replace(/_/g, " "))).join(", ")}
      </div>
      ${detail.degree > 5 ? `
      <div class="meta" style="margin-top:6px">
        <div style="color:var(--text-dim);font-size:0.8em;margin-bottom:3px">AGENCY <span style="font-style:italic;opacity:0.5">(Latour/Callon)</span></div>
        <div style="font-size:0.75em;color:var(--text-dim)">
          ${(() => {
            const opp = (agent.capital?.symbolic || 0) * 0.3 + (agent.institutions?.board_power || 0) * 0.3 + (detail.degree / 50) * 0.2;
            const roles = [];
            if (opp > 0.35) roles.push('<span style="color:var(--accent)">Obligatory Passage Point</span>');
            if ((agent.institutions?.board_power || 0) > 0.3 && agent.capital?.symbolic > 0.4) roles.push('<span style="color:#b08f4a">Programmer</span>');
            if (detail.degree > 15 && (agent.institutions?.membership_count || 0) >= 2) roles.push('<span style="color:#3a7d6e">Switcher</span>');
            if ((agent.institutions?.membership_count || 0) >= 2 && agent.capital?.cultural > 0.4) roles.push('<span style="color:#5a4080">Center of Calc.</span>');
            return roles.length > 0 ? roles.join(' · ') : '<span style="opacity:0.4">peripheral actant</span>';
          })()}
        </div>
      </div>` : ""}
      ${detail.emergence && (detail.emergence.catalyst || detail.emergence.constrained) ? `
      <div class="meta" style="margin-top:6px">
        <div style="color:var(--text-dim);font-size:0.8em;margin-bottom:3px">EMERGENCE</div>
        <div class="bar-row"><span class="bar-label">Catalyst</span><div class="bar-track"><div class="bar-fill" style="width:${(detail.emergence.catalyst||0) * 100}%;background:#d4a85a"></div></div></div>
        <div class="bar-row"><span class="bar-label">Constrained</span><div class="bar-track"><div class="bar-fill" style="width:${(detail.emergence.constrained||0) * 100}%;background:#8a5ad4"></div></div></div>
        <div style="font-size:0.8em;color:var(--text-dim);margin-top:2px">
          Bridging: ${((detail.emergence.bridging||0)*100).toFixed(0)}%
          · Satisfaction: ${((agent.satisfaction||0)*100).toFixed(0)}%
          · Norms: ${Object.keys(agent.norms||{}).length}
        </div>
      </div>` : ""}
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

  // Microscope — open in separate window
  document.getElementById("btn-microscope").addEventListener("click", () => {
    microscopeWin = window.open("/microscope", "civgraph-microscope",
      "width=1200,height=700,menubar=no,toolbar=no,location=no,status=no");
  });

  // Listen for microscope highlight requests (origin-validated)
  window.addEventListener("message", (e) => {
    if (e.origin !== window.location.origin) return;
    if (e.data && e.data.type === "microscope_highlight" && e.data.agentIds) {
      const ids = new Set(e.data.agentIds);
      nodeGroup.selectAll("g.node").classed("highlighted", (d) => ids.has(d.id));
      linkGroup.selectAll("line").classed("highlighted", (l) => {
        const sid = typeof l.source === "object" ? l.source.id : l.source;
        const tid = typeof l.target === "object" ? l.target.id : l.target;
        return ids.has(sid) || ids.has(tid);
      });
    }
  });

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
  const allAgents = await fetch("/api/search?limit=3000").then((r) => r.json());
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
    topography: "INTERLOCKING DIRECTORATES",
    constellation: "CONSTELLATIONS OF CLAN",
    heatmap: "FABRIC OF OPINION",
    seismograph: "SEISMOGRAPH OF EVENTS",
    citypulse: "PULSE OF THE CITY",
    emergence: "OBSERVATORY OF EMERGENCE",
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
      // Fetch full agent data with institutions for the board visualization
      const agentsFull = await safeFetch("/api/search?limit=3000");
      Artifacts.renderTopography(agentsFull || nodes);
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
    case "emergence":
      const emergenceData = await safeFetch("/api/emergence");
      Artifacts.renderEmergence(emergenceData);
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

  // Load initial emergence data
  const emergence = await safeFetch("/api/emergence");
  if (emergence) renderEmergenceSummary(emergence);

  initSimControls();
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

// ── Simulation play/pause/step controls ─────────────────────────────────────
let simPlaying = false;
let simTimer = null;
let simTicking = false;
const SIM_SPEEDS = { 1: 2000, 2: 1000, 3: 400 };
let simSpeed = 1;

function initSimControls() {
  const btnPlay = document.getElementById("btn-play");
  const btnStep = document.getElementById("btn-step");

  btnPlay.addEventListener("click", togglePlay);
  btnStep.addEventListener("click", () => { if (!simTicking) advanceTick(); });

  document.getElementById("speed-group").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-speed]");
    if (!btn) return;
    simSpeed = parseInt(btn.dataset.speed);
    document.querySelectorAll(".btn-speed").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    if (simPlaying) { clearInterval(simTimer); scheduleAutoTick(); }
  });
}

function togglePlay() {
  simPlaying = !simPlaying;
  const btn = document.getElementById("btn-play");
  btn.innerHTML = simPlaying ? "&#9208;" : "&#9654;";
  btn.classList.toggle("playing", simPlaying);
  if (simPlaying) {
    advanceTick();
    scheduleAutoTick();
  } else {
    clearInterval(simTimer);
    simTimer = null;
  }
}

function scheduleAutoTick() {
  simTimer = setInterval(() => {
    if (!simTicking) advanceTick();
  }, SIM_SPEEDS[simSpeed] || 2000);
}

async function advanceTick() {
  simTicking = true;
  const years = parseInt(document.getElementById("tick-years").value) || 1;
  let result;
  try {
    result = await fetch("/api/tick", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ years }),
    }).then((r) => r.json());
  } finally {
    simTicking = false;
  }

  if (result && result.current) {
    renderEnvironment(result.current);
  }
  if (result && result.stats) {
    updateStats(result.stats);
  }
  if (result && result.emergence) {
    renderEmergenceSummary(result.emergence);
  }
  if (result && result.economy) {
    // Tick returns economy summary; fetch full for occupation breakdown
    const fullEcon = await safeFetch("/api/economy");
    renderEconomyPanel(fullEcon || result.economy);
  }
  if (result && result.media) {
    renderMediaPanel(result.media);
  }
  if (result) {
    const stsData = await safeFetch("/api/sts");
    renderHealthPanel(result.health || null, result.institutions || null, stsData);
  }

  // Notify Microscope window of tick completion
  if (microscopeWin && !microscopeWin.closed) {
    microscopeWin.postMessage({ type: "tick_complete" }, window.location.origin);
  }

  // Refresh graph data to reflect capital/economy/media changes
  graphData = await fetch("/api/graph").then((r) => r.json());
  // Update node visuals without rebuilding simulation
  // Merge positions from current simulation nodes
  const posMap = {};
  simulation.nodes().forEach(n => { posMap[n.id] = { x: n.x, y: n.y, vx: n.vx, vy: n.vy, fx: n.fx, fy: n.fy }; });
  graphData.nodes.forEach(n => {
    const pos = posMap[n.id];
    if (pos) { n.x = pos.x; n.y = pos.y; n.vx = pos.vx; n.vy = pos.vy; n.fx = pos.fx; n.fy = pos.fy; }
  });
  simulation.nodes(graphData.nodes);
  simulation.force("link").links(graphData.links);
  renderLinks();
  renderNodes();
  simulation.alpha(0.1).restart();
}

// ── Emergence summary ───────────────────────────────────────────────────────

const EMERGENCE_GROUPS = {
  "social": {
    label: "social",
    dims: ["polarization", "echo_chambers", "segregation", "contagion_susceptibility"],
  },
  "structure": {
    label: "structure",
    dims: ["network_resilience", "power_law", "phase_transitions"],
  },
  "capital": {
    label: "capital",
    dims: ["inequality", "institutional_trust", "collective_intelligence"],
  },
  "culture": {
    label: "culture",
    dims: ["cultural_convergence", "norm_emergence", "information_theoretic"],
  },
};

const EMERGENCE_DIM_LABELS = {
  polarization: "Polarization",
  inequality: "Inequality",
  collective_intelligence: "Coll. Intl.",
  contagion_susceptibility: "Contagion",
  network_resilience: "Resilience",
  phase_transitions: "Tipping",
  echo_chambers: "Echo Chmbrs",
  power_law: "Power Law",
  institutional_trust: "Trust",
  cultural_convergence: "Convergence",
  information_theoretic: "Info Intgr.",
  norm_emergence: "Norms",
  segregation: "Segregation",
};

const EMERGENCE_DIM_COLORS = {
  polarization: "#d46b6b",
  inequality: "#d46b6b",
  collective_intelligence: "#5ad49a",
  contagion_susceptibility: "#d4a85a",
  network_resilience: "#5a8fd4",
  phase_transitions: "#d46b6b",
  echo_chambers: "#8a5ad4",
  power_law: "#8895a7",
  institutional_trust: "#5ad49a",
  cultural_convergence: "#a0845c",
  information_theoretic: "#5a8fb0",
  norm_emergence: "#b09a5a",
  segregation: "#b05a6b",
};

function renderEmergenceSummary(emergence) {
  const container = document.getElementById("emergence-gauges");
  const statusEl = document.getElementById("emergence-status");
  if (!container || !emergence || !emergence.current) return;

  const composites = emergence.current.coupled_composites || emergence.current.composites || {};
  const trends = emergence.trends || {};
  const warnings = emergence.current.early_warnings || {};

  // Status: count active warnings
  const warnCount = Object.values(warnings).filter(w => w.warning_level >= 2).length;
  const watchCount = Object.values(warnings).filter(w => w.warning_level === 1).length;
  if (statusEl) {
    if (warnCount > 0) {
      statusEl.innerHTML = `<span style="color:var(--negative)">${warnCount} warning${warnCount > 1 ? "s" : ""}</span>`;
    } else if (watchCount > 0) {
      statusEl.innerHTML = `<span style="color:#d4a85a">${watchCount} watch</span>`;
    } else {
      statusEl.textContent = "stable";
    }
  }

  let html = "";
  for (const [groupKey, group] of Object.entries(EMERGENCE_GROUPS)) {
    html += `<div class="emergence-group-label">${esc(group.label)}</div>`;
    for (const dim of group.dims) {
      const val = composites[dim];
      if (val === undefined) continue;
      const label = EMERGENCE_DIM_LABELS[dim] || dim;
      const color = EMERGENCE_DIM_COLORS[dim] || "var(--accent)";
      const pct = Math.max(0, Math.min(100, val * 100));
      const trend = trends[dim] || 0;
      const arrow = trend > 0.005 ? "\u2191" : trend < -0.005 ? "\u2193" : "";
      const warning = warnings[dim];
      let warnDot = "";
      if (warning && warning.warning_level >= 3) {
        warnDot = `<span class="emergence-warn critical" title="Critical: approaching tipping point"></span>`;
      } else if (warning && warning.warning_level >= 2) {
        warnDot = `<span class="emergence-warn warning" title="Warning: rising instability"></span>`;
      } else if (warning && warning.warning_level >= 1) {
        warnDot = `<span class="emergence-warn watch" title="Watch: rising autocorrelation"></span>`;
      }
      html += `<div class="emergence-gauge">
        <span class="emergence-gauge-label">${esc(label)}${warnDot}</span>
        <div class="emergence-gauge-track">
          <div class="emergence-gauge-fill" style="width:${pct}%;background:${color}"></div>
        </div>
        <span class="emergence-gauge-val">${pct.toFixed(0)}%${arrow}</span>
      </div>`;
    }
  }
  container.innerHTML = html;
}

// ── Economy & Media panels ─────────────────────────────────────────────────

const TECH_COLORS = {
  mechanization: "#8895a7", digitization: "#60a5fa",
  ai_ml: "#a78bfa", robotics: "#fbbf24",
};

const TECH_LABELS = {
  mechanization: "Mechanization", digitization: "Digitization",
  ai_ml: "AI / ML", robotics: "Robotics",
};

function renderEconomyPanel(econData) {
  const container = document.getElementById("economy-gauges");
  if (!container || !econData) return;

  let html = "";

  // Tech adoption gauges
  if (econData.tech_state) {
    html += `<div class="env-domain-label">tech adoption</div>`;
    for (const [key, wave] of Object.entries(econData.tech_state)) {
      const pct = (wave.adoption || 0) * 100;
      const color = TECH_COLORS[key] || "var(--accent)";
      const label = TECH_LABELS[key] || wave.name || key;
      html += `<div class="env-gauge">
        <span class="env-gauge-label">${esc(label)}</span>
        <div class="env-gauge-track">
          <div class="env-gauge-fill" style="width:${pct}%;background:${color}"></div>
        </div>
        <span class="env-gauge-val">${pct.toFixed(0)}%</span>
      </div>`;
    }
  }

  // Aggregate stats
  html += `<div class="env-domain-label">aggregate</div>`;
  const stats = [
    { label: "Avg Income", val: econData.avg_income || 0, color: "var(--positive)" },
    { label: "Avg Disruption", val: econData.avg_displacement_risk || 0, color: "var(--negative)" },
    { label: "Avg Productivity", val: Math.min(1, (econData.avg_productivity || 1) / 3), color: "#38bdf8" },
    { label: "Avg Adaptation", val: econData.avg_tech_adaptation || 0, color: "#a78bfa" },
  ];
  for (const s of stats) {
    html += `<div class="env-gauge">
      <span class="env-gauge-label">${esc(s.label)}</span>
      <div class="env-gauge-track">
        <div class="env-gauge-fill" style="width:${s.val * 100}%;background:${s.color}"></div>
      </div>
      <span class="env-gauge-val">${(s.val * 100).toFixed(0)}%</span>
    </div>`;
  }

  container.innerHTML = html;
}

const MEDIA_GAUGE_DEFS = [
  { key: "print_reach", label: "Print Reach", color: "#94a3b8", group: "reach" },
  { key: "mass_reach", label: "Mass Reach", color: "#fbbf24", group: "reach" },
  { key: "social_reach", label: "Social Reach", color: "#8b5cf6", group: "reach" },
  { key: "print_trust", label: "Print Trust", color: "#94a3b8", group: "trust" },
  { key: "mass_trust", label: "Mass Trust", color: "#fbbf24", group: "trust" },
  { key: "social_trust", label: "Social Trust", color: "#8b5cf6", group: "trust" },
  { key: "social_echo_chamber", label: "Echo Chamber", color: "#d46b6b", group: "effects" },
  { key: "social_polarization", label: "Polarization", color: "#d46b6b", group: "effects" },
  { key: "misinformation_level", label: "Misinfo", color: "#f87171", group: "effects" },
  { key: "media_fragmentation", label: "Fragmentation", color: "#d4a85a", group: "effects" },
];

function renderMediaPanel(mediaData) {
  const container = document.getElementById("media-gauges");
  if (!container || !mediaData) return;

  let html = "";
  const landscape = mediaData.landscape || {};

  let currentGroup = "";
  for (const def of MEDIA_GAUGE_DEFS) {
    if (def.group !== currentGroup) {
      currentGroup = def.group;
      html += `<div class="env-domain-label">${esc(currentGroup)}</div>`;
    }
    const val = landscape[def.key] || 0;
    html += `<div class="env-gauge">
      <span class="env-gauge-label">${esc(def.label)}</span>
      <div class="env-gauge-track">
        <div class="env-gauge-fill" style="width:${val * 100}%;background:${def.color}"></div>
      </div>
      <span class="env-gauge-val">${(val * 100).toFixed(0)}%</span>
    </div>`;
  }

  // Aggregate consumption
  html += `<div class="env-domain-label">population</div>`;
  const pop = [
    { label: "Avg Literacy", val: mediaData.avg_media_literacy || 0, color: "#5ad49a" },
    { label: "Avg Bubble", val: mediaData.avg_algorithmic_bubble || 0, color: "#d46b6b" },
    { label: "Deep Bubble", val: mediaData.deep_bubble_fraction || 0, color: "#f87171" },
    { label: "Low Literacy", val: mediaData.low_literacy_fraction || 0, color: "#d4a85a" },
  ];
  for (const s of pop) {
    html += `<div class="env-gauge">
      <span class="env-gauge-label">${esc(s.label)}</span>
      <div class="env-gauge-track">
        <div class="env-gauge-fill" style="width:${s.val * 100}%;background:${s.color}"></div>
      </div>
      <span class="env-gauge-val">${(s.val * 100).toFixed(0)}%</span>
    </div>`;
  }

  container.innerHTML = html;
}

function renderHealthPanel(healthData, instData, stsData) {
  const container = document.getElementById("health-gauges");
  if (!container) return;

  let html = "";

  if (healthData) {
    html += `<div class="env-domain-label">health</div>`;
    const healthGauges = [
      { label: "Avg Physical", val: healthData.avg_physical_health || 0, color: "var(--positive)" },
      { label: "Avg Mental", val: healthData.avg_mental_health || 0, color: "#60a5fa" },
      { label: "Work Capacity", val: healthData.avg_work_capacity || 0, color: "#fbbf24" },
      { label: "Avg Stress", val: healthData.avg_stress || 0, color: "var(--negative)" },
      { label: "Chronic Rate", val: healthData.chronic_condition_rate || 0, color: "#d4a85a" },
    ];
    for (const g of healthGauges) {
      html += `<div class="env-gauge">
        <span class="env-gauge-label">${esc(g.label)}</span>
        <div class="env-gauge-track">
          <div class="env-gauge-fill" style="width:${g.val * 100}%;background:${g.color}"></div>
        </div>
        <span class="env-gauge-val">${(g.val * 100).toFixed(0)}%</span>
      </div>`;
    }
  }

  if (instData) {
    html += `<div class="env-domain-label">institutions</div>`;
    const instGauges = [
      { label: "Avg Memberships", val: Math.min(1, (instData.avg_memberships || 0) / 4), color: "#a78bfa", raw: (instData.avg_memberships || 0).toFixed(1) },
      { label: "Board Members", val: instData.board_member_fraction || 0, color: "#fbbf24" },
      { label: "Leaders", val: instData.leadership_fraction || 0, color: "#d4a85a" },
      { label: "Skill Currency", val: instData.avg_skill_currency || 0, color: "#38bdf8" },
      { label: "Civic Partic.", val: instData.avg_civic_participation || 0, color: "var(--positive)" },
    ];
    for (const g of instGauges) {
      const display = g.raw || (g.val * 100).toFixed(0) + "%";
      html += `<div class="env-gauge">
        <span class="env-gauge-label">${esc(g.label)}</span>
        <div class="env-gauge-track">
          <div class="env-gauge-fill" style="width:${g.val * 100}%;background:${g.color}"></div>
        </div>
        <span class="env-gauge-val">${display}</span>
      </div>`;
    }
  }

  if (stsData) {
    html += `<div class="env-domain-label">agency (STS)</div>`;
    const stsGauges = [
      { label: "Performativity", val: stsData.performativity?.composite || 0, color: "#5a4080" },
      { label: "Black-boxing", val: stsData.black_boxing?.composite || 0, color: SEPIA || "#6b5b4f" },
      { label: "Alignment", val: stsData.heterogeneous_alignment?.composite || 0, color: "#3a7d6e" },
      { label: "Fragility", val: stsData.heterogeneous_alignment?.fragility || 0, color: "var(--negative)" },
    ];
    for (const g of stsGauges) {
      html += `<div class="env-gauge">
        <span class="env-gauge-label">${esc(g.label)}</span>
        <div class="env-gauge-track">
          <div class="env-gauge-fill" style="width:${g.val * 100}%;background:${g.color}"></div>
        </div>
        <span class="env-gauge-val">${(g.val * 100).toFixed(0)}%</span>
      </div>`;
    }
  }

  container.innerHTML = html || '<span class="emergence-placeholder">No data yet</span>';
}

// Load initial economy/media/health/institution/STS data
async function loadEconomyMedia() {
  const econData = await safeFetch("/api/economy");
  if (econData) renderEconomyPanel(econData);
  const mediaData = await safeFetch("/api/media");
  if (mediaData) renderMediaPanel(mediaData);
  const healthData = await safeFetch("/api/health");
  const instData = await safeFetch("/api/institutions");
  const stsData = await safeFetch("/api/sts");
  renderHealthPanel(healthData, instData, stsData);
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
