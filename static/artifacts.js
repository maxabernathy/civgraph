/**
 * CivGraph — Artifact Renderers
 *
 * Print-quality visualizations rendered to high-resolution canvas.
 * Aesthetic: 1960s German industrial design / Swiss International Style.
 * Near-white backgrounds, sans-serif typography, functional color,
 * geometric precision, visible grid construction.
 *
 * Design references:
 *   Dieter Rams (Braun), Otl Aicher (Munich 1972), HfG Ulm,
 *   Josef Müller-Brockmann (Grid Systems), Adrian Frutiger,
 *   Deutsche Bahn / SBB railway typography.
 *
 * Pen-plotter compatible: all marks are strokes, stipple, or crosshatch.
 *
 * 1. Agent Anatomies       — radial glyph specimen plate
 * 2. Interlocking Boards   — institutional power network (replaces Topography)
 * 3. Clan Constellations   — political-influence scatter
 * 4. Opinion Fabric        — crosshatch matrix
 * 5. Event Seismograph     — cascade waveforms
 * 6. City Pulse            — 7-domain time-series strips
 * 7. Emergence Observatory — 13-dimension radar + detail panels
 */

const Artifacts = (() => {
  // ── Palette: functional signal colors (Aicher/Rams) ─────────────────
  const PAPER = "#fafafa";       // near-white, no warmth
  const INK = "#1a1a1a";         // true near-black
  const INK_LIGHT = "#4a4a4a";   // mid grey
  const INK_FAINT = "#b0b0b0";   // light grey (construction)
  const GRID = "#e0e0e0";        // visible grid lines
  const SEPIA = "#6a6a6a";       // annotation grey
  const INDIGO = "#003366";      // primary data (DB blue)
  const OCHRE = "#e89f00";       // signal yellow (Aicher)
  const OXIDE = "#cc0000";       // signal red (DIN)
  const VERDIGRIS = "#008844";   // signal green
  const SLATE = "#707070";       // secondary

  const FONT = '-apple-system, "Helvetica Neue", Arial, sans-serif';

  const CLAN_INKS = [
    "#003366", "#cc0000", "#008844", "#e89f00", "#6633aa",
    "#0077bb", "#cc4400", "#227755", "#997700", "#883377",
    "#005599", "#aa2200", "#338866", "#aa8800", "#553388",
    "#0066aa", "#bb3300", "#449977", "#887700", "#773399",
  ];

  const INTEREST_ANGLES = {};
  const ALL_INTERESTS = [
    "real_estate", "tech", "healthcare", "education", "arts", "finance",
    "manufacturing", "media", "law", "energy", "agriculture", "hospitality",
    "transport", "security", "environment", "sports", "retail", "philanthropy",
    "religion", "unions",
  ];
  ALL_INTERESTS.forEach((interest, i) => {
    INTEREST_ANGLES[interest] = (i / ALL_INTERESTS.length) * Math.PI * 2 - Math.PI / 2;
  });

  const POL_NUM = {
    far_left: -3, left: -2, center_left: -1, center: 0,
    center_right: 1, right: 2, far_right: 3,
  };

  // ── Shared drawing primitives ─────────────────────────────────────

  const FORMAT_PRESETS = {
    "1":    { label: "1x screen",   scale: 1 },
    "2":    { label: "2x print",    scale: 2 },
    "4":    { label: "4x high-res", scale: 4 },
    "8":    { label: "8x poster",   scale: 8 },
    "a2":   { label: "A2 300dpi",   w: 7016, h: 4961 },
    "a2p":  { label: "A2 portrait", w: 4961, h: 7016 },
  };

  function getCanvasCtx() {
    const fmt = document.getElementById("res-select").value;
    const preset = FORMAT_PRESETS[fmt] || FORMAT_PRESETS["2"];
    const canvas = document.getElementById("artifact-canvas");
    const wrap = document.getElementById("artifact-canvas-wrap");

    let baseW, baseH, scale;

    if (preset.w) {
      scale = 1;
      baseW = preset.w;
      baseH = preset.h;
      canvas.width = baseW;
      canvas.height = baseH;
      const maxScreenW = wrap.clientWidth - 48;
      const maxScreenH = wrap.clientHeight - 48;
      const fitScale = Math.min(maxScreenW / baseW, maxScreenH / baseH);
      canvas.style.width = Math.floor(baseW * fitScale) + "px";
      canvas.style.height = Math.floor(baseH * fitScale) + "px";
    } else {
      scale = preset.scale || 2;
      baseW = Math.min(wrap.clientWidth - 48, 1400);
      baseH = Math.min(wrap.clientHeight - 48, 900);
      canvas.width = baseW * scale;
      canvas.height = baseH * scale;
      canvas.style.width = baseW + "px";
      canvas.style.height = baseH + "px";
    }

    const ctx = canvas.getContext("2d");
    if (scale > 1) ctx.scale(scale, scale);

    // Clean white background (no texture — Swiss precision)
    ctx.fillStyle = PAPER;
    ctx.fillRect(0, 0, baseW, baseH);

    return { ctx, w: baseW, h: baseH, canvas, scale };
  }

  // Crop marks (print registration, replaces decorative double rule)
  function drawRegistration(ctx, w, h) {
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.3;
    // Single border rule
    ctx.strokeRect(12, 12, w - 24, h - 24);
    // Crop marks at corners (L-shaped, 8px long, 2px gap from corner)
    const m = 12;
    const gap = 2;
    const len = 8;
    [[m,m,1,1],[w-m,m,-1,1],[m,h-m,1,-1],[w-m,h-m,-1,-1]].forEach(([x,y,dx,dy]) => {
      ctx.beginPath();
      ctx.moveTo(x - dx * (len + gap), y); ctx.lineTo(x - dx * gap, y);
      ctx.moveTo(x, y - dy * (len + gap)); ctx.lineTo(x, y - dy * gap);
      ctx.stroke();
    });
    // Center ticks on each edge
    ctx.lineWidth = 0.2;
    const cx = w / 2, cy = h / 2;
    [[cx, m, 0, -4], [cx, h - m, 0, 4], [m, cy, -4, 0], [w - m, cy, 4, 0]].forEach(([x, y, dx, dy]) => {
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + dx, y + dy); ctx.stroke();
    });
  }

  // Swiss-style asymmetric header
  function drawPlateTitle(ctx, w, title, subtitle, plateNum) {
    // Title: left-aligned, semibold, uppercase
    ctx.fillStyle = INK;
    ctx.font = `600 15px ${FONT}`;
    ctx.textAlign = "left";
    ctx.fillText(title.toUpperCase(), 20, 34);
    // Subtitle: light weight
    ctx.font = `300 9px ${FONT}`;
    ctx.fillStyle = INK_LIGHT;
    ctx.fillText(subtitle, 20, 46);
    // Plate number: large, light, right-aligned (Rams/Braun label style)
    ctx.font = `600 22px ${FONT}`;
    ctx.fillStyle = INK_FAINT;
    ctx.textAlign = "right";
    ctx.fillText(String(plateNum || "01").padStart(2, "0"), w - 20, 36);
    // Colophon
    ctx.font = `500 7px ${FONT}`;
    ctx.fillStyle = INK_FAINT;
    ctx.fillText("CIVGRAPH", w - 20, 46);
    ctx.font = `300 7px ${FONT}`;
    ctx.fillText(new Date().toISOString().slice(0, 10), w - 20, 54);
    ctx.textAlign = "left";
    // Single rule beneath
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.4;
    ctx.beginPath();
    ctx.moveTo(20, 58);
    ctx.lineTo(w - 20, 58);
    ctx.stroke();
  }

  function crosshatch(ctx, x, y, w, h, density, angle, color, alpha) {
    ctx.save();
    ctx.globalAlpha = alpha || 0.3;
    ctx.strokeStyle = color || INK_LIGHT;
    ctx.lineWidth = 0.4;
    const step = Math.max(2, 8 / density);
    const cos = Math.cos(angle || Math.PI / 4);
    const sin = Math.sin(angle || Math.PI / 4);
    ctx.beginPath();
    ctx.rect(x, y, w, h);
    ctx.clip();
    const diag = Math.sqrt(w * w + h * h);
    for (let d = -diag; d < diag; d += step) {
      ctx.beginPath();
      ctx.moveTo(x + w / 2 + cos * d - sin * diag, y + h / 2 + sin * d + cos * diag);
      ctx.lineTo(x + w / 2 + cos * d + sin * diag, y + h / 2 + sin * d - cos * diag);
      ctx.stroke();
    }
    ctx.restore();
  }

  function stipple(ctx, cx, cy, radius, density, color) {
    ctx.fillStyle = color || INK;
    const n = Math.round(density * radius * radius * 0.3);
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = Math.sqrt(Math.random()) * radius;
      const x = cx + Math.cos(a) * r;
      const y = cy + Math.sin(a) * r;
      ctx.fillRect(x, y, 0.6, 0.6);
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // 1. RHIZOME ANATOMIES — Diverging Alliances
  //    (Deleuze & Guattari 1980 — A Thousand Plateaus)
  //
  //    Each agent is a root node from which branching tendrils grow
  //    outward. Tendrils represent domains of alliance: four capitals
  //    (Bourdieu), interests, institutional ties, political lean.
  //    Forks visualize how a single person's allegiances diverge
  //    across incompatible domains. Pen-plotter compatible.
  // ═══════════════════════════════════════════════════════════════════

  function renderAnatomies(nodes) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Rhizome Anatomies",
      "Diverging alliances and interests \u2014 Deleuze & Guattari after Bourdieu",
      "01"
    );

    const sorted = [...nodes].sort((a, b) => b.influence - a.influence);
    const subjects = sorted.slice(0, 48);
    const cols = 8;
    const rows = 6;
    const margin = { top: 66, right: 24, bottom: 56, left: 24 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;
    const cellW = iw / cols;
    const cellH = ih / rows;

    // Faint construction grid
    ctx.strokeStyle = GRID;
    ctx.lineWidth = 0.12;
    for (let c = 0; c <= cols; c++) {
      const x = margin.left + c * cellW;
      ctx.beginPath(); ctx.moveTo(x, margin.top); ctx.lineTo(x, margin.top + ih); ctx.stroke();
    }
    for (let r = 0; r <= rows; r++) {
      const y = margin.top + r * cellH;
      ctx.beginPath(); ctx.moveTo(margin.left, y); ctx.lineTo(margin.left + iw, y); ctx.stroke();
    }

    const clanSet = [...new Set(nodes.map(n => n.clan))].sort();
    const clanIdx = {};
    clanSet.forEach((c, i) => { clanIdx[c] = i; });

    for (let i = 0; i < subjects.length; i++) {
      const n = subjects[i];
      const col = i % cols;
      const row = Math.floor(i / cols);
      const cx = margin.left + col * cellW + cellW / 2;
      const cy = margin.top + row * cellH + cellH / 2 - 4;
      const span = Math.min(cellW, cellH) * 0.42;
      drawRhizomeGlyph(ctx, cx, cy, span, n, clanIdx);

      // Name label
      ctx.fillStyle = INK;
      ctx.font = `500 6.5px ${FONT}`;
      ctx.textAlign = "center";
      const surname = n.name.split(" ").slice(-1)[0];
      ctx.fillText(surname.toUpperCase(), cx, cy + span + 13);
      ctx.fillStyle = INK_FAINT;
      ctx.font = `300 5.5px ${FONT}`;
      ctx.fillText(String(i + 1).padStart(2, "0"), cx, cy + span + 20);
      ctx.textAlign = "left";
    }

    // Legend
    const ly = h - 48;
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.3;
    ctx.beginPath(); ctx.moveTo(24, ly - 6); ctx.lineTo(w - 24, ly - 6); ctx.stroke();

    ctx.fillStyle = INK_LIGHT;
    ctx.font = `600 8px ${FONT}`;
    ctx.textAlign = "left";
    ctx.fillText("READING THE RHIZOME", 30, ly + 5);
    ctx.font = `300 7px ${FONT}`;
    ctx.fillStyle = SEPIA;
    ctx.fillText(
      "Root node = agent (size = influence).  Four primary tendrils: green = economic, purple = cultural, blue = social, ochre = symbolic capital.",
      30, ly + 16
    );
    ctx.fillText(
      "Branch forks = interests diverging from each capital.  Red thorns = chronic condition.  Dotted runners = institutional ties.  Lean = political orientation.",
      30, ly + 27
    );

    setMeta("Top 48 agents by influence. Rhizome glyphs show diverging alliances across capital, interests, institutions, and political orientation (Deleuze & Guattari).");
  }

  // Seeded pseudo-random for deterministic rhizome growth
  function _rhizoRng(seed) {
    let s = seed | 0;
    return () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
  }

  function drawRhizomeGlyph(ctx, cx, cy, span, agent, clanIdx) {
    const ink = CLAN_INKS[clanIdx[agent.clan] % CLAN_INKS.length];
    const pol = POL_NUM[agent.politics] || 0;
    const cap = agent.capital || {};
    const capValues = [cap.economic || 0, cap.cultural || 0, cap.social || 0, cap.symbolic || 0];
    const capColors = [VERDIGRIS, "#6633aa", INDIGO, OCHRE];
    const capLabels = ["Ec", "Cu", "So", "Sy"];
    const influence = agent.influence || 0;
    const assertiveness = agent.assertiveness || 0.5;
    const degree = agent.degree || 1;
    const interests = agent.interests || [];
    const healthVal = agent.health_composite || 0.75;
    const chronic = agent.chronic_condition || false;
    const nMemb = agent.membership_count || 0;

    // Deterministic RNG per agent
    let seed = 0;
    for (let ci = 0; ci < (agent.name || "x").length; ci++) seed += agent.name.charCodeAt(ci) * (ci + 1);
    const rng = _rhizoRng(seed);

    ctx.save();
    ctx.translate(cx, cy);

    // Political lean shifts the whole rhizome slightly left/right
    const polShift = (pol / 3) * span * 0.12;

    // ── Root node ──────────────────────────────────────────────
    const rootR = 2 + influence * assertiveness * span * 0.08;
    ctx.beginPath();
    ctx.arc(polShift, 0, rootR, 0, Math.PI * 2);
    ctx.fillStyle = ink;
    ctx.fill();

    // Faint root halo (degree)
    if (degree > 3) {
      ctx.beginPath();
      ctx.arc(polShift, 0, rootR + 2 + Math.sqrt(degree) * 0.8, 0, Math.PI * 2);
      ctx.strokeStyle = ink;
      ctx.globalAlpha = 0.1;
      ctx.lineWidth = 0.3;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // ── Four primary tendrils (capitals) ───────────────────────
    // Grow outward in four cardinal-ish directions, with organic wobble
    const baseAngles = [
      -Math.PI / 2 + (rng() - 0.5) * 0.3,  // up-ish (economic)
      0 + (rng() - 0.5) * 0.3,               // right-ish (cultural)
      Math.PI / 2 + (rng() - 0.5) * 0.3,     // down-ish (social)
      Math.PI + (rng() - 0.5) * 0.3,          // left-ish (symbolic)
    ];

    // Map interests to capital domains (5 interests per capital quadrant)
    const interestSet = new Set(interests);
    const quadrantInterests = [[], [], [], []];
    ALL_INTERESTS.forEach((intName, ii) => {
      if (interestSet.has(intName)) {
        quadrantInterests[ii % 4].push(intName);
      }
    });

    for (let q = 0; q < 4; q++) {
      const value = capValues[q];
      if (value < 0.03) continue;
      const color = capColors[q];
      const angle = baseAngles[q];
      const tendrilLen = span * (0.35 + value * 0.55);
      const ox = polShift;
      const oy = 0;

      // Draw main tendril as organic curve
      _drawTendril(ctx, ox, oy, angle, tendrilLen, color, 1.4 + value * 1.2, rng, 5);

      // Capital label at tendril midpoint
      const midX = ox + Math.cos(angle) * tendrilLen * 0.5;
      const midY = oy + Math.sin(angle) * tendrilLen * 0.5;
      ctx.font = `300 3.5px ${FONT}`;
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.5;
      ctx.textAlign = "center";
      ctx.fillText(capLabels[q], midX + Math.cos(angle + Math.PI/2) * 5, midY + Math.sin(angle + Math.PI/2) * 5 + 1.2);
      ctx.globalAlpha = 1;
      ctx.textAlign = "left";

      // Fork branches at the tendril tip for each interest in this quadrant
      const qInterests = quadrantInterests[q];
      const tipX = ox + Math.cos(angle) * tendrilLen;
      const tipY = oy + Math.sin(angle) * tendrilLen;

      for (let fi = 0; fi < qInterests.length; fi++) {
        const forkSpread = 0.5 + fi * 0.35;
        const forkSign = (fi % 2 === 0) ? 1 : -1;
        const forkAngle = angle + forkSign * forkSpread;
        const forkLen = span * (0.12 + rng() * 0.14);
        _drawTendril(ctx, tipX, tipY, forkAngle, forkLen, color, 0.6, rng, 3);

        // Small node at fork tip
        const ftx = tipX + Math.cos(forkAngle) * forkLen;
        const fty = tipY + Math.sin(forkAngle) * forkLen;
        ctx.beginPath();
        ctx.arc(ftx, fty, 0.9, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
      }

      // If no interests in this quadrant, add a terminal node
      if (qInterests.length === 0) {
        ctx.beginPath();
        ctx.arc(tipX, tipY, 1.1, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
      }
    }

    // ── Institutional runners (dotted lateral connections) ─────
    if (nMemb > 0) {
      ctx.strokeStyle = OCHRE;
      ctx.globalAlpha = 0.5;
      ctx.setLineDash([1.5, 2]);
      for (let mi = 0; mi < Math.min(nMemb, 4); mi++) {
        const ra = baseAngles[mi % 4] + (rng() - 0.5) * 0.8;
        const rLen = span * (0.25 + rng() * 0.2);
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(polShift, 0);
        // Curved runner
        const cpx = polShift + Math.cos(ra) * rLen * 0.5 + (rng() - 0.5) * span * 0.15;
        const cpy = Math.sin(ra) * rLen * 0.5 + (rng() - 0.5) * span * 0.15;
        const ex = polShift + Math.cos(ra) * rLen;
        const ey = Math.sin(ra) * rLen;
        ctx.quadraticCurveTo(cpx, cpy, ex, ey);
        ctx.stroke();
        // Small square node at runner end
        ctx.fillStyle = OCHRE;
        ctx.fillRect(ex - 1, ey - 1, 2, 2);
      }
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    // ── Health / chronic condition: thorns ─────────────────────
    if (chronic) {
      // Draw small thorn marks near the root
      ctx.strokeStyle = OXIDE;
      ctx.lineWidth = 0.7;
      ctx.globalAlpha = 0.7;
      for (let ti = 0; ti < 3; ti++) {
        const ta = rng() * Math.PI * 2;
        const tr = rootR + 2 + rng() * 4;
        const tx = polShift + Math.cos(ta) * tr;
        const ty = Math.sin(ta) * tr;
        ctx.beginPath();
        ctx.moveTo(tx, ty);
        ctx.lineTo(tx + Math.cos(ta) * 3, ty + Math.sin(ta) * 3);
        ctx.stroke();
        // Cross at tip
        const etx = tx + Math.cos(ta) * 3;
        const ety = ty + Math.sin(ta) * 3;
        ctx.beginPath();
        ctx.moveTo(etx - 1, ety - 1); ctx.lineTo(etx + 1, ety + 1);
        ctx.moveTo(etx + 1, ety - 1); ctx.lineTo(etx - 1, ety + 1);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }

    // Health vitality: stipple density near root (healthy = dense, unhealthy = sparse)
    if (healthVal > 0.2) {
      const hDensity = healthVal * 0.5;
      const hColor = healthVal > 0.5 ? VERDIGRIS : OXIDE;
      stipple(ctx, polShift, 0, rootR + 3, hDensity, hColor + "25");
    }

    ctx.restore();
  }

  /**
   * Draw an organic tendril (curved line with slight wobble).
   * Pen-plotter compatible: pure strokes with Bezier segments.
   */
  function _drawTendril(ctx, x0, y0, angle, length, color, width, rng, segments) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.beginPath();
    ctx.moveTo(x0, y0);

    let px = x0, py = y0;
    const segLen = length / segments;
    for (let s = 0; s < segments; s++) {
      const t = (s + 1) / segments;
      // Slight angular drift per segment for organic feel
      const drift = (rng() - 0.5) * 0.3;
      const segAngle = angle + drift * (1 - t * 0.5); // less drift toward tip
      const nx = px + Math.cos(segAngle) * segLen;
      const ny = py + Math.sin(segAngle) * segLen;
      // Control point offset perpendicular to direction
      const perpAngle = segAngle + Math.PI / 2;
      const cpOff = (rng() - 0.5) * segLen * 0.6;
      const cpx = (px + nx) / 2 + Math.cos(perpAngle) * cpOff;
      const cpy = (py + ny) / 2 + Math.sin(perpAngle) * cpOff;
      ctx.quadraticCurveTo(cpx, cpy, nx, ny);
      // Taper: reduce width toward tip
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(nx, ny);
      ctx.lineWidth = width * (1 - t * 0.5);
      px = nx;
      py = ny;
    }
    ctx.stroke();
  }

  // ═══════════════════════════════════════════════════════════════════
  // 2. INTERLOCKING BOARDS — Institutional Power Network
  //    (replaces Influence Topography — more analytically interesting)
  //
  //    Visualizes shared institutional memberships (Mizruchi 1996):
  //    agents who sit on the same boards form power-concentrating ties.
  //    The plot shows institutions as large nodes, agents as smaller
  //    nodes, with lines connecting agents to their institutions.
  //    Board leaders are emphasized with larger marks.
  // ═══════════════════════════════════════════════════════════════════

  function renderTopography(nodes) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Interlocking Directorates",
      "Institutional membership network: shared boards concentrate power (Mizruchi 1996)",
      "02"
    );

    const margin = { top: 66, right: 40, bottom: 50, left: 40 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

    // Build institution → agent mapping
    const instMap = {};  // inst_name → { type, agents: [{name, id, leader, influence}] }
    const agentInsts = {}; // agent_id → [inst_names]

    for (const n of nodes) {
      if (!n.institutions || !n.institutions.memberships) continue;
      const memberships = n.institutions.memberships;
      agentInsts[n.id] = [];
      for (const m of memberships) {
        if (!instMap[m.name]) {
          instMap[m.name] = { type: m.type, agents: [] };
        }
        instMap[m.name].agents.push({
          name: n.name, id: n.id, leader: m.leadership,
          influence: n.influence, clan: n.clan,
        });
        agentInsts[n.id].push(m.name);
      }
    }

    // Filter to institutions with 2+ members (interlocking)
    const instEntries = Object.entries(instMap)
      .filter(([_, v]) => v.agents.length >= 2)
      .sort((a, b) => b[1].agents.length - a[1].agents.length);

    if (instEntries.length === 0) {
      ctx.fillStyle = SEPIA;
      ctx.font = `300 11px ${FONT}`;
      ctx.fillText("No shared institutional memberships detected.", 40, 100);
      setMeta("Generate agents with institutional memberships to see interlocking directorates.");
      return;
    }

    // Layout: institutions in a vertical list on the left, agents on the right
    // Connected by lines showing membership
    const instCount = Math.min(instEntries.length, 25);
    const instSpacing = ih / (instCount + 1);
    const instX = margin.left + iw * 0.25;
    const agentX = margin.left + iw * 0.75;

    // Collect all unique agents who appear in shown institutions
    const shownAgentIds = new Set();
    for (let i = 0; i < instCount; i++) {
      for (const a of instEntries[i][1].agents) shownAgentIds.add(a.id);
    }
    const uniqueAgents = [...shownAgentIds];
    const agentSpacing = ih / (uniqueAgents.length + 1);
    const agentPositions = {};
    uniqueAgents.forEach((id, i) => {
      agentPositions[id] = margin.top + (i + 1) * Math.min(agentSpacing, 14);
    });

    // Type colors
    const typeColors = {
      professional_board: INDIGO,
      civic_association: VERDIGRIS,
      cultural_club: "#6633aa",
      social_club: OCHRE,
      political_org: OXIDE,
      religious_community: SEPIA,
      industry_body: "#0077bb",
      alumni_network: "#883377",
    };

    // Draw connections (lines)
    for (let i = 0; i < instCount; i++) {
      const [name, data] = instEntries[i];
      const instY = margin.top + (i + 1) * instSpacing;
      const color = typeColors[data.type] || SLATE;

      for (const a of data.agents) {
        const ay = agentPositions[a.id];
        if (ay === undefined) continue;
        ctx.strokeStyle = color;
        ctx.lineWidth = a.leader ? 0.8 : 0.3;
        ctx.globalAlpha = a.leader ? 0.5 : 0.15;
        ctx.beginPath();
        ctx.moveTo(instX + 6, instY);
        ctx.lineTo(agentX - 6, ay);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;

    // Draw institution nodes (left column)
    for (let i = 0; i < instCount; i++) {
      const [name, data] = instEntries[i];
      const instY = margin.top + (i + 1) * instSpacing;
      const color = typeColors[data.type] || SLATE;
      const r = 3 + Math.sqrt(data.agents.length) * 1.5;

      // Open circle
      ctx.beginPath();
      ctx.arc(instX, instY, r, 0, Math.PI * 2);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Label
      ctx.fillStyle = color;
      ctx.font = `500 6.5px ${FONT}`;
      ctx.textAlign = "right";
      ctx.fillText(name.toUpperCase(), instX - r - 4, instY + 2);
      // Member count
      ctx.fillStyle = INK_FAINT;
      ctx.font = `300 5.5px ${FONT}`;
      ctx.fillText(`${data.agents.length}`, instX - r - 4, instY + 9);
    }

    // Draw agent nodes (right column)
    const clanSet = [...new Set(nodes.map(n => n.clan))].sort();
    const clanIdx = {};
    clanSet.forEach((c, i) => { clanIdx[c] = i; });

    for (const [id, y] of Object.entries(agentPositions)) {
      const node = nodes.find(n => n.id === id);
      if (!node) continue;
      const r = 1.5 + (node.influence || 0) * 3;
      const clan_ink = CLAN_INKS[clanIdx[node.clan] % CLAN_INKS.length];

      // Open circle
      ctx.beginPath();
      ctx.arc(agentX, y, r, 0, Math.PI * 2);
      ctx.strokeStyle = clan_ink;
      ctx.lineWidth = 0.6;
      ctx.stroke();
      // Center dot
      if (r > 2) {
        ctx.beginPath();
        ctx.arc(agentX, y, 0.5, 0, Math.PI * 2);
        ctx.fillStyle = clan_ink;
        ctx.fill();
      }

      // Label
      ctx.fillStyle = INK_LIGHT;
      ctx.font = `400 5.5px ${FONT}`;
      ctx.textAlign = "left";
      const surname = node.name.split(" ").slice(-1)[0];
      ctx.fillText(surname, agentX + r + 3, y + 2);
    }
    ctx.textAlign = "left";

    // Column headers
    ctx.fillStyle = INK_LIGHT;
    ctx.font = `600 8px ${FONT}`;
    ctx.textAlign = "center";
    ctx.fillText("INSTITUTIONS", instX, margin.top - 4);
    ctx.fillText("AGENTS", agentX, margin.top - 4);
    ctx.textAlign = "left";

    // Type legend at bottom
    const ly = h - 44;
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.3;
    ctx.beginPath(); ctx.moveTo(24, ly - 6); ctx.lineTo(w - 24, ly - 6); ctx.stroke();

    ctx.font = `300 7px ${FONT}`;
    let lx = 30;
    for (const [type, color] of Object.entries(typeColors)) {
      ctx.beginPath();
      ctx.arc(lx + 3, ly + 5, 2.5, 0, Math.PI * 2);
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.8;
      ctx.stroke();
      ctx.fillStyle = SEPIA;
      ctx.fillText(type.replace(/_/g, " "), lx + 9, ly + 7);
      lx += ctx.measureText(type.replace(/_/g, " ")).width + 18;
    }

    setMeta("Bipartite network: institutions (left) connected to agents (right) by membership. " +
      "Heavier lines = leadership roles. Circle size = membership count / influence.");
  }

  // ═══════════════════════════════════════════════════════════════════
  // 3. CLAN CONSTELLATIONS
  // ═══════════════════════════════════════════════════════════════════

  function renderConstellation(nodes) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Constellations of Clan",
      `${nodes.length} individuals — horizontal = political axis, vertical = influence`,
      "03"
    );

    const margin = { top: 66, right: 50, bottom: 55, left: 50 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

    // Ruled grid
    ctx.strokeStyle = GRID;
    ctx.lineWidth = 0.15;
    const gridStepX = iw / 7;
    for (let i = 0; i <= 7; i++) {
      const x = margin.left + i * gridStepX;
      ctx.beginPath(); ctx.moveTo(x, margin.top); ctx.lineTo(x, margin.top + ih); ctx.stroke();
    }
    for (let i = 0; i <= 10; i++) {
      const y = margin.top + (i / 10) * ih;
      ctx.beginPath(); ctx.moveTo(margin.left, y); ctx.lineTo(margin.left + iw, y); ctx.stroke();
    }
    // Heavier axes
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.4;
    ctx.beginPath(); ctx.moveTo(margin.left, margin.top + ih); ctx.lineTo(margin.left + iw, margin.top + ih); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(margin.left, margin.top); ctx.lineTo(margin.left, margin.top + ih); ctx.stroke();

    const clans = {};
    for (const n of nodes) {
      if (!clans[n.clan]) clans[n.clan] = [];
      clans[n.clan].push(n);
    }
    const clanNames = Object.keys(clans);

    function starPos(n, idx) {
      const pol = POL_NUM[n.politics] || 0;
      const jx = Math.sin(idx * 137.508) * 0.35;
      const jy = Math.cos(idx * 137.508) * 0.12;
      return {
        x: margin.left + ((pol + jx + 3.5) / 7) * iw,
        y: margin.top + ih - (n.influence + jy) * ih * 0.82 - ih * 0.1,
      };
    }

    for (const clan of clanNames) {
      const members = clans[clan];
      const ci = clanNames.indexOf(clan);
      const ink = CLAN_INKS[ci % CLAN_INKS.length];
      const positions = members.map((n, i) => ({ ...starPos(n, i), node: n }));

      // MST
      const used = new Set([0]);
      const mstEdges = [];
      while (used.size < positions.length) {
        let best = Infinity, bf = -1, bt = -1;
        for (const f of used) {
          for (let t = 0; t < positions.length; t++) {
            if (used.has(t)) continue;
            const dx = positions[f].x - positions[t].x;
            const dy = positions[f].y - positions[t].y;
            const d = dx * dx + dy * dy;
            if (d < best) { best = d; bf = f; bt = t; }
          }
        }
        if (bt >= 0) { used.add(bt); mstEdges.push([bf, bt]); }
        else break;
      }

      // MST lines
      ctx.strokeStyle = ink;
      ctx.globalAlpha = 0.25;
      ctx.lineWidth = 0.5;
      for (const [a, b] of mstEdges) {
        ctx.beginPath();
        ctx.moveTo(positions[a].x, positions[a].y);
        ctx.lineTo(positions[b].x, positions[b].y);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // Star marks
      for (const pos of positions) {
        const inf = pos.node.influence;
        const r = 1.0 + inf * 4;

        // Concentric target ring (replaces stipple halo — more technical)
        if (inf > 0.2) {
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, r * 2.0, 0, Math.PI * 2);
          ctx.strokeStyle = ink;
          ctx.lineWidth = 0.15;
          ctx.globalAlpha = 0.15;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }

        // Open circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
        ctx.strokeStyle = ink;
        ctx.lineWidth = 0.8 + inf;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, Math.max(0.5, r * 0.35), 0, Math.PI * 2);
        ctx.fillStyle = ink;
        ctx.fill();

        // Crosshair
        if (inf > 0.35) {
          ctx.strokeStyle = ink;
          ctx.lineWidth = 0.3;
          const fl = r * 2.2;
          ctx.beginPath();
          ctx.moveTo(pos.x - fl, pos.y); ctx.lineTo(pos.x + fl, pos.y);
          ctx.moveTo(pos.x, pos.y - fl); ctx.lineTo(pos.x, pos.y + fl);
          ctx.stroke();
          if (inf > 0.6) {
            const df = fl * 0.6;
            ctx.beginPath();
            ctx.moveTo(pos.x - df, pos.y - df); ctx.lineTo(pos.x + df, pos.y + df);
            ctx.moveTo(pos.x + df, pos.y - df); ctx.lineTo(pos.x - df, pos.y + df);
            ctx.stroke();
          }
        }
      }

      // Clan label
      const avg_x = positions.reduce((s, p) => s + p.x, 0) / positions.length;
      const avg_y = positions.reduce((s, p) => s + p.y, 0) / positions.length;
      ctx.fillStyle = ink;
      ctx.globalAlpha = 0.65;
      ctx.font = `600 6.5px ${FONT}`;
      ctx.textAlign = "center";
      ctx.fillText(clan.toUpperCase(), avg_x, avg_y - 12);
      ctx.globalAlpha = 1;
      ctx.textAlign = "left";
    }

    // Axis labels
    ctx.fillStyle = SEPIA;
    ctx.font = `500 7px ${FONT}`;
    ctx.textAlign = "center";
    const labels = ["FAR LEFT", "LEFT", "CENTRE-LEFT", "CENTRE", "CENTRE-RIGHT", "RIGHT", "FAR RIGHT"];
    for (let i = 0; i < 7; i++) {
      ctx.fillText(labels[i], margin.left + ((i + 0.5) / 7) * iw, h - margin.bottom + 16);
    }
    ctx.save();
    ctx.translate(margin.left - 18, margin.top + ih / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText("INFLUENCE", 0, 0);
    ctx.restore();
    ctx.textAlign = "left";

    // Bottom ticks
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.3;
    for (let i = 0; i <= 7; i++) {
      const x = margin.left + i * gridStepX;
      ctx.beginPath(); ctx.moveTo(x, margin.top + ih); ctx.lineTo(x, margin.top + ih + 4); ctx.stroke();
    }

    setMeta("Each constellation = one clan. Circle diameter = influence. " +
      "Cross-flares mark high-influence agents. MST lines connect within-clan members.");
  }

  // ═══════════════════════════════════════════════════════════════════
  // 4. OPINION FABRIC
  // ═══════════════════════════════════════════════════════════════════

  function renderHeatmap(nodes) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Fabric of Opinion",
      "Rows = clans, columns = topics. Hatching density = opinion strength.",
      "04"
    );

    const topicSet = new Set();
    for (const n of nodes) {
      if (n._opinions) for (const k of Object.keys(n._opinions)) topicSet.add(k);
    }
    const topics = [...topicSet];
    if (topics.length === 0) {
      ctx.fillStyle = SEPIA;
      ctx.font = `300 11px ${FONT}`;
      ctx.fillText("No opinions recorded yet. Fire some events first.", 40, 100);
      setMeta("Trigger events to generate opinion data.");
      return;
    }

    const clans = {};
    for (const n of nodes) { if (!clans[n.clan]) clans[n.clan] = []; clans[n.clan].push(n); }
    const clanNames = Object.keys(clans).sort();

    const margin = { top: 80, right: 40, bottom: 40, left: 110 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;
    const cellW = iw / topics.length;
    const cellH = ih / clanNames.length;

    for (let row = 0; row < clanNames.length; row++) {
      const clan = clanNames[row];
      const members = clans[clan];
      for (let col = 0; col < topics.length; col++) {
        const topic = topics[col];
        const opinions = members.map(n => (n._opinions && n._opinions[topic]) || 0).filter(v => v !== 0);
        const x = margin.left + col * cellW;
        const y = margin.top + row * cellH;

        ctx.strokeStyle = GRID;
        ctx.lineWidth = 0.3;
        ctx.strokeRect(x, y, cellW, cellH);

        if (opinions.length === 0) continue;

        const avg = opinions.reduce((s, v) => s + v, 0) / opinions.length;
        const variance = opinions.reduce((s, v) => s + (v - avg) ** 2, 0) / opinions.length;
        const strength = Math.abs(avg);

        const color = avg > 0 ? VERDIGRIS : OXIDE;
        const angle = avg > 0 ? Math.PI / 2 : 0;
        crosshatch(ctx, x + 1, y + 1, cellW - 2, cellH - 2, strength * 3, angle, color, strength * 0.6);

        if (variance > 0.04) {
          crosshatch(ctx, x + 1, y + 1, cellW - 2, cellH - 2,
            variance * 8, angle + Math.PI / 2, INK_LIGHT, variance * 0.5);
        }

        if (cellW > 28 && cellH > 12) {
          ctx.fillStyle = INK;
          ctx.globalAlpha = 0.4 + strength * 0.4;
          ctx.font = `300 ${Math.min(8, cellH * 0.4)}px ${FONT}`;
          ctx.textAlign = "center";
          ctx.fillText(avg.toFixed(2), x + cellW / 2, y + cellH / 2 + 3);
          ctx.textAlign = "left";
          ctx.globalAlpha = 1;
        }
      }
    }

    // Labels
    ctx.fillStyle = INK;
    ctx.font = `400 ${Math.min(8, cellH * 0.55)}px ${FONT}`;
    ctx.textAlign = "right";
    for (let i = 0; i < clanNames.length; i++) {
      ctx.fillText(clanNames[i].toUpperCase(), margin.left - 8, margin.top + i * cellH + cellH / 2 + 3);
    }
    ctx.textAlign = "left";
    ctx.font = `400 ${Math.min(7, cellW * 0.7)}px ${FONT}`;
    for (let i = 0; i < topics.length; i++) {
      ctx.save();
      ctx.translate(margin.left + i * cellW + cellW / 2, margin.top - 6);
      ctx.rotate(-Math.PI / 3);
      ctx.fillText(topics[i].toUpperCase(), 0, 0);
      ctx.restore();
    }

    setMeta("Vertical hatching (green) = support. Horizontal (red) = oppose. Cross-hatch (grey) = internal disagreement.");
  }

  // ═══════════════════════════════════════════════════════════════════
  // 5. EVENT SEISMOGRAPH
  // ═══════════════════════════════════════════════════════════════════

  function renderSeismograph(nodes, links, events) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Seismograph of Events",
      `${events.length} event${events.length !== 1 ? "s" : ""} recorded. Amplitude = cascade reach per step.`,
      "05"
    );

    if (events.length === 0) {
      ctx.fillStyle = SEPIA;
      ctx.font = `300 11px ${FONT}`;
      ctx.fillText("No events recorded. Fire some events first.", 40, 100);
      setMeta("Trigger events to see their seismograph traces.");
      return;
    }

    const margin = { top: 70, right: 40, bottom: 40, left: 170 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;
    const rowH = Math.min(70, ih / events.length);
    const maxSteps = Math.max(...events.map(e => e.propagation.length));

    for (let ei = 0; ei < events.length; ei++) {
      const event = events[ei];
      const baseY = margin.top + ei * rowH + rowH / 2;
      const ink = event.sentiment > 0.2 ? VERDIGRIS : event.sentiment < -0.2 ? OXIDE : SLATE;

      ctx.strokeStyle = GRID;
      ctx.lineWidth = 0.2;
      ctx.beginPath(); ctx.moveTo(margin.left, baseY); ctx.lineTo(margin.left + iw, baseY); ctx.stroke();

      const points = [{ x: margin.left, y: baseY }];
      const stepW = iw / (maxSteps + 1);
      let maxReach = 1;
      for (const s of event.propagation) if (s.results.length > maxReach) maxReach = s.results.length;

      for (let si = 0; si < event.propagation.length; si++) {
        const total = event.propagation[si].results.length;
        const amplitude = (total / maxReach) * (rowH * 0.38);
        const x = margin.left + (si + 1) * stepW;
        const subN = 14;
        for (let sp = 0; sp < subN; sp++) {
          const t = sp / subN;
          const subX = x - stepW + t * stepW;
          const envelope = Math.sin(t * Math.PI) * amplitude;
          const freq = 3 + si * 0.4;
          const osc = Math.sin(t * Math.PI * freq * 2) * envelope;
          points.push({ x: subX, y: baseY - osc });
        }
      }
      const lastX = margin.left + event.propagation.length * stepW;
      for (let t = 0; t < 20; t++) {
        const x = lastX + t * (stepW / 5);
        if (x > margin.left + iw) break;
        points.push({ x, y: baseY - Math.sin(t * 1.5) * 2.5 * Math.exp(-t * 0.3) });
      }
      points.push({ x: margin.left + iw, y: baseY });

      ctx.strokeStyle = ink;
      ctx.lineWidth = 0.9;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
      ctx.stroke();

      ctx.fillStyle = ink;
      ctx.font = `600 7.5px ${FONT}`;
      ctx.textAlign = "right";
      ctx.fillText(event.title.toUpperCase(), margin.left - 10, baseY + 3);
      ctx.fillStyle = INK_FAINT;
      ctx.font = `300 6px ${FONT}`;
      ctx.fillText(`${event.total_affected} affected`, margin.left - 10, baseY + 12);
      ctx.textAlign = "left";

      ctx.beginPath();
      ctx.arc(margin.left + 3, baseY, 2, 0, Math.PI * 2);
      ctx.fillStyle = ink;
      ctx.fill();
    }

    ctx.fillStyle = INK_FAINT;
    ctx.font = `300 6.5px ${FONT}`;
    ctx.textAlign = "center";
    const sw = iw / (maxSteps + 1);
    for (let i = 0; i <= maxSteps; i++) {
      ctx.fillText(`S${i}`, margin.left + i * sw, h - margin.bottom + 14);
    }
    ctx.textAlign = "left";

    setMeta("Each row = one event. Amplitude = agents reached per step. " +
      "Green = positive sentiment, red = negative, grey = neutral.");
  }

  // ═══════════════════════════════════════════════════════════════════
  // 6. CITY PULSE — 7-domain time-series
  // ═══════════════════════════════════════════════════════════════════

  function renderCityPulse(history, meta) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Pulse of the City",
      `${history.length} year${history.length !== 1 ? "s" : ""} of macro-environment evolution`,
      "06"
    );

    if (history.length < 2) {
      ctx.fillStyle = SEPIA;
      ctx.font = `300 11px ${FONT}`;
      ctx.fillText("Advance the simulation to see environment evolution.", 40, 100);
      setMeta("Use the tick button to advance years.");
      return;
    }

    const domains = meta.domains;
    const indicators = meta.indicators;
    const domainNames = Object.keys(domains);
    const margin = { top: 66, right: 40, bottom: 40, left: 100 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;
    const stripH = ih / domainNames.length;
    const years = history.length;

    const domainInks = [INDIGO, OCHRE, VERDIGRIS, "#6633aa", OXIDE, "#0077bb", SEPIA];

    for (let di = 0; di < domainNames.length; di++) {
      const domain = domainNames[di];
      const keys = domains[domain];
      const baseY = margin.top + di * stripH;
      const ink = domainInks[di % domainInks.length];

      ctx.fillStyle = ink;
      ctx.font = `600 8px ${FONT}`;
      ctx.textAlign = "right";
      ctx.fillText(domain.toUpperCase(), margin.left - 12, baseY + stripH / 2 + 3);
      ctx.textAlign = "left";

      ctx.strokeStyle = GRID;
      ctx.lineWidth = 0.2;
      ctx.beginPath(); ctx.moveTo(margin.left, baseY + stripH - 2); ctx.lineTo(margin.left + iw, baseY + stripH - 2); ctx.stroke();

      for (let ki = 0; ki < keys.length; ki++) {
        const key = keys[ki];
        const ind = indicators[key];
        if (!ind) continue;
        const lo = ind.min, hi = ind.max;
        const range = hi - lo || 1;

        const alpha = 0.7 - ki * 0.12;
        ctx.strokeStyle = ink;
        ctx.globalAlpha = Math.max(0.2, alpha);
        ctx.lineWidth = ki === 0 ? 1.2 : 0.7;

        const points = [];
        for (let yi = 0; yi < years; yi++) {
          const val = history[yi][key] || 0;
          const norm = (val - lo) / range;
          const x = margin.left + (yi / (years - 1)) * iw;
          const y = baseY + stripH - 4 - norm * (stripH - 8);
          points.push({ x, y });
        }

        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);
        for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
        ctx.stroke();

        // Crosshatch fill under lead trace
        if (ki === 0) {
          ctx.save();
          ctx.beginPath();
          ctx.moveTo(points[0].x, points[0].y);
          for (let pi = 1; pi < points.length; pi++) ctx.lineTo(points[pi].x, points[pi].y);
          ctx.lineTo(points[points.length - 1].x, baseY + stripH - 2);
          ctx.lineTo(points[0].x, baseY + stripH - 2);
          ctx.closePath();
          ctx.clip();
          ctx.strokeStyle = ink;
          ctx.lineWidth = 0.2;
          ctx.globalAlpha = 0.06;
          for (let hx = margin.left - ih; hx < margin.left + iw + ih; hx += 5) {
            ctx.beginPath(); ctx.moveTo(hx, baseY); ctx.lineTo(hx + ih, baseY + stripH); ctx.stroke();
          }
          ctx.restore();
          ctx.globalAlpha = 1;
        }

        if (points.length > 0) {
          const last = points[points.length - 1];
          ctx.globalAlpha = Math.max(0.3, alpha);
          ctx.font = `300 5px ${FONT}`;
          ctx.fillStyle = ink;
          const label = ind.label.split(" ").slice(-1)[0];
          ctx.fillText(label, last.x + 3, last.y + 2);
        }
        ctx.globalAlpha = 1;
      }
    }

    ctx.fillStyle = INK_FAINT;
    ctx.font = `300 6.5px ${FONT}`;
    ctx.textAlign = "center";
    const yearStep = Math.max(1, Math.floor(years / 10));
    for (let yi = 0; yi < years; yi += yearStep) {
      const x = margin.left + (yi / (years - 1 || 1)) * iw;
      ctx.fillText(`Y${history[yi].year}`, x, h - margin.bottom + 14);
    }
    ctx.textAlign = "left";

    setMeta("Seven domain strips. Each trace = one indicator. Diagonal hatching under lead trace. " +
      "Advance simulation years to see the city evolve.");
  }

  // ═══════════════════════════════════════════════════════════════════
  // 7. EMERGENCE OBSERVATORY
  // ═══════════════════════════════════════════════════════════════════

  const EMERGENCE_COLORS = {
    polarization: OXIDE,
    inequality: "#aa2200",
    collective_intelligence: VERDIGRIS,
    contagion_susceptibility: OCHRE,
    network_resilience: INDIGO,
    phase_transitions: "#cc4400",
    echo_chambers: "#6633aa",
    power_law: SLATE,
    institutional_trust: "#227755",
    cultural_convergence: "#997700",
    information_theoretic: "#0077bb",
    norm_emergence: "#887700",
    segregation: "#883377",
  };

  const EMERGENCE_LABELS = {
    polarization: "Polarization", inequality: "Inequality",
    collective_intelligence: "Coll. Intelligence", contagion_susceptibility: "Contagion Risk",
    network_resilience: "Network Resilience", phase_transitions: "Phase Transitions",
    echo_chambers: "Echo Chambers", power_law: "Power Law",
    institutional_trust: "Institutional Trust", cultural_convergence: "Cultural Convergence",
    information_theoretic: "Info Integration", norm_emergence: "Norm Emergence",
    segregation: "Segregation",
  };

  const EMERGENCE_ORDER = [
    "polarization", "inequality", "collective_intelligence",
    "contagion_susceptibility", "network_resilience", "phase_transitions",
    "echo_chambers", "power_law", "institutional_trust", "cultural_convergence",
    "information_theoretic", "norm_emergence", "segregation",
  ];

  function renderEmergence(emergenceData) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Observatory of Emergence",
      "Thirteen macro-phenomena arising from micro-level agent interaction",
      "07"
    );

    if (!emergenceData || !emergenceData.current) {
      ctx.fillStyle = INK_FAINT;
      ctx.font = `300 13px ${FONT}`;
      ctx.textAlign = "center";
      ctx.fillText("No emergence data. Advance the simulation to generate readings.", w / 2, h / 2);
      setMeta("Advance the simulation to compute emergent properties.");
      return;
    }

    const current = emergenceData.current;
    const composites = current.coupled_composites || current.composites || {};
    const rawComposites = current.composites || {};
    const dimensions = current.dimensions || {};
    const history = emergenceData.history || [];
    const trends = emergenceData.trends || {};
    const meta = current.meta || {};
    const earlyWarnings = current.early_warnings || {};
    const couplingMatrix = current.coupling_matrix || {};

    const margin = { top: 66, right: 30, bottom: 50, left: 30 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

    // Radar chart
    const radarCx = margin.left + iw * 0.5;
    const radarCy = margin.top + ih * 0.36;
    const radarR = Math.min(iw * 0.24, ih * 0.26);
    const dims = EMERGENCE_ORDER;
    const nDims = dims.length;

    // Concentric rings
    for (let ring = 1; ring <= 5; ring++) {
      const r = (ring / 5) * radarR;
      ctx.beginPath(); ctx.arc(radarCx, radarCy, r, 0, Math.PI * 2);
      ctx.strokeStyle = ring === 5 ? INK_FAINT : GRID;
      ctx.lineWidth = ring === 5 ? 0.4 : 0.2;
      ctx.stroke();
      if (ring % 2 === 0) {
        ctx.fillStyle = INK_FAINT;
        ctx.font = `300 5px ${FONT}`;
        ctx.textAlign = "left";
        ctx.fillText((ring * 20).toString(), radarCx + 2, radarCy - r + 3);
      }
    }

    // Axis lines and labels
    for (let i = 0; i < nDims; i++) {
      const angle = (i / nDims) * Math.PI * 2 - Math.PI / 2;
      const ex = radarCx + Math.cos(angle) * radarR;
      const ey = radarCy + Math.sin(angle) * radarR;

      ctx.beginPath(); ctx.moveTo(radarCx, radarCy); ctx.lineTo(ex, ey);
      ctx.strokeStyle = GRID;
      ctx.lineWidth = 0.3;
      ctx.stroke();

      const labelR = radarR + 10;
      const lx = radarCx + Math.cos(angle) * labelR;
      const ly = radarCy + Math.sin(angle) * labelR;
      ctx.fillStyle = EMERGENCE_COLORS[dims[i]] || INK;
      ctx.font = `600 5.5px ${FONT}`;
      if (Math.abs(angle + Math.PI / 2) < 0.2) ctx.textAlign = "center";
      else if (Math.cos(angle) < -0.1) ctx.textAlign = "right";
      else if (Math.cos(angle) > 0.1) ctx.textAlign = "left";
      else ctx.textAlign = "center";
      const SHORT = {
        polarization:"POLAR.",inequality:"INEQ.",collective_intelligence:"COLL.INT.",
        contagion_susceptibility:"CONTAG.",network_resilience:"RESIL.",
        phase_transitions:"TIPPING",echo_chambers:"ECHO CH.",
        power_law:"PWR LAW",institutional_trust:"TRUST",
        cultural_convergence:"CONV.",information_theoretic:"INFO",
        norm_emergence:"NORMS",segregation:"SEGREG.",
      };
      ctx.fillText(SHORT[dims[i]] || dims[i].toUpperCase(), lx, ly + 3);
    }

    // Radar polygon with crosshatch fill
    ctx.beginPath();
    for (let i = 0; i < nDims; i++) {
      const angle = (i / nDims) * Math.PI * 2 - Math.PI / 2;
      const val = composites[dims[i]] || 0;
      const r = val * radarR;
      const px = radarCx + Math.cos(angle) * r;
      const py = radarCy + Math.sin(angle) * r;
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.save();
    ctx.clip();
    ctx.strokeStyle = INK;
    ctx.lineWidth = 0.3;
    ctx.globalAlpha = 0.12;
    for (let d = -radarR * 2; d < radarR * 2; d += 4) {
      ctx.beginPath();
      ctx.moveTo(radarCx + d - radarR, radarCy - radarR);
      ctx.lineTo(radarCx + d + radarR, radarCy + radarR);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    ctx.restore();
    ctx.beginPath();
    for (let i = 0; i < nDims; i++) {
      const angle = (i / nDims) * Math.PI * 2 - Math.PI / 2;
      const val = composites[dims[i]] || 0;
      const r = val * radarR;
      const px = radarCx + Math.cos(angle) * r;
      const py = radarCy + Math.sin(angle) * r;
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.strokeStyle = INK;
    ctx.lineWidth = 1.2;
    ctx.stroke();

    // Data points
    for (let i = 0; i < nDims; i++) {
      const angle = (i / nDims) * Math.PI * 2 - Math.PI / 2;
      const val = composites[dims[i]] || 0;
      const r = val * radarR;
      const px = radarCx + Math.cos(angle) * r;
      const py = radarCy + Math.sin(angle) * r;
      ctx.beginPath(); ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fillStyle = EMERGENCE_COLORS[dims[i]] || INK;
      ctx.fill();
      ctx.fillStyle = INK;
      ctx.font = `600 6px ${FONT}`;
      ctx.textAlign = "center";
      ctx.fillText((val * 100).toFixed(0), px, py - 6);
    }

    // History overlay
    if (history.length > 1) {
      const older = history.slice(-Math.min(5, history.length), -1);
      older.forEach((snap, si) => {
        ctx.beginPath();
        for (let i = 0; i < nDims; i++) {
          const angle = (i / nDims) * Math.PI * 2 - Math.PI / 2;
          const val = (snap.composites || {})[dims[i]] || 0;
          const r = val * radarR;
          const px = radarCx + Math.cos(angle) * r;
          const py = radarCy + Math.sin(angle) * r;
          if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.strokeStyle = INK_FAINT;
        ctx.lineWidth = 0.4;
        ctx.globalAlpha = 0.15 + si * 0.05;
        ctx.stroke();
        ctx.globalAlpha = 1;
      });
    }

    // Detail panels (7 left, 6 right)
    const panelW = iw * 0.22;
    const panelH = ih * 0.085;
    const panelGap = 4;
    const leftCount = 7;

    for (let i = 0; i < nDims; i++) {
      const dim = dims[i];
      const isLeft = i < leftCount;
      const idx = isLeft ? i : i - leftCount;
      const px = isLeft ? margin.left + 8 : w - margin.right - panelW - 8;
      const py = margin.top + ih * 0.04 + idx * (panelH + panelGap);

      const color = EMERGENCE_COLORS[dim] || INK;
      const val = composites[dim] || 0;
      const dimData = dimensions[dim] || {};
      const trend = trends[dim] || 0;
      const dimMeta = meta[dim] || {};

      // Panel border
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.5;
      ctx.globalAlpha = 0.3;
      ctx.strokeRect(px, py, panelW, panelH);
      ctx.globalAlpha = 1;

      // Ruled fill
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.15;
      ctx.globalAlpha = 0.06;
      for (let ry = py + 2; ry < py + panelH; ry += 3) {
        ctx.beginPath(); ctx.moveTo(px, ry); ctx.lineTo(px + panelW, ry); ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // Name
      ctx.fillStyle = color;
      ctx.font = `600 7px ${FONT}`;
      ctx.textAlign = "left";
      ctx.fillText((EMERGENCE_LABELS[dim] || dim).toUpperCase(), px + 4, py + 10);

      // Bar (crosshatch instead of solid fill)
      const barX = px + 4, barY = py + 15, barW = panelW - 8, barH = 5;
      ctx.strokeStyle = GRID;
      ctx.lineWidth = 0.3;
      ctx.strokeRect(barX, barY, barW, barH);
      if (val > 0.01) {
        crosshatch(ctx, barX, barY, barW * val, barH, 2, 0, color, 0.5);
      }

      // Value
      ctx.fillStyle = INK;
      ctx.font = `600 7px ${FONT}`;
      ctx.textAlign = "right";
      ctx.fillText((val * 100).toFixed(0) + "%", px + panelW - 4, py + 10);

      // Trend
      if (Math.abs(trend) > 0.001) {
        ctx.fillStyle = trend > 0 ? VERDIGRIS : OXIDE;
        ctx.font = `500 8px ${FONT}`;
        ctx.textAlign = "center";
        ctx.fillText(trend > 0 ? "\u2191" : "\u2193", px + panelW - 20, py + 10);
      }

      // Sub-metrics
      ctx.font = `300 5.5px ${FONT}`;
      ctx.fillStyle = INK_LIGHT;
      ctx.textAlign = "left";
      let subY = py + 26;
      const subKeys = Object.keys(dimData).filter(k => k !== "composite" && typeof dimData[k] === "number");
      for (const key of subKeys.slice(0, 3)) {
        const v = dimData[key];
        ctx.fillText(`${key.replace(/_/g, " ")}: ${typeof v === "number" ? v.toFixed(3) : v}`, px + 4, subY);
        subY += 7;
      }

      // Citation
      if (dimMeta.research) {
        ctx.font = `300 4.5px ${FONT}`;
        ctx.fillStyle = INK_FAINT;
        ctx.fillText(dimMeta.research, px + 4, py + panelH - 3);
      }

      // Warning
      const warning = earlyWarnings[dim];
      if (warning && warning.warning_level > 0) {
        const wColors = ["", OCHRE, OXIDE, "#dc2626"];
        const wLabels = ["", "WATCH", "WARNING", "CRITICAL"];
        const wLevel = warning.warning_level;
        ctx.fillStyle = wColors[wLevel];
        ctx.font = `600 5px ${FONT}`;
        ctx.textAlign = "right";
        ctx.fillText(wLabels[wLevel], px + panelW - 4, py + panelH - 3);
        ctx.beginPath();
        ctx.arc(px + panelW - 4 - ctx.measureText(wLabels[wLevel]).width - 4, py + panelH - 5, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.textAlign = "left";
      }

      // Coupling delta
      const rawVal = rawComposites[dim] || 0;
      const couplingDelta = val - rawVal;
      if (Math.abs(couplingDelta) > 0.01) {
        ctx.font = `300 5px ${FONT}`;
        ctx.fillStyle = couplingDelta > 0 ? VERDIGRIS : OXIDE;
        ctx.textAlign = "left";
        ctx.fillText(`coupling ${couplingDelta > 0 ? "+" : ""}${(couplingDelta * 100).toFixed(0)}%`, px + 4, py + panelH - 10);
      }
    }

    // Coupling web
    if (Object.keys(couplingMatrix).length > 0) {
      const cwCx = radarCx;
      const cwCy = margin.top + ih * 0.68;
      const cwR = Math.min(iw * 0.12, ih * 0.08);

      ctx.fillStyle = INK_LIGHT;
      ctx.font = `600 7px ${FONT}`;
      ctx.textAlign = "center";
      ctx.fillText("COUPLING WEB", cwCx, cwCy - cwR - 6);

      const cwPositions = {};
      for (let i = 0; i < nDims; i++) {
        const a = (i / nDims) * Math.PI * 2 - Math.PI / 2;
        cwPositions[dims[i]] = { x: cwCx + Math.cos(a) * cwR, y: cwCy + Math.sin(a) * cwR };
      }

      for (const [source, targets] of Object.entries(couplingMatrix)) {
        const sp = cwPositions[source];
        if (!sp) continue;
        for (const [target, strength] of Object.entries(targets)) {
          const tp = cwPositions[target];
          if (!tp) continue;
          ctx.beginPath(); ctx.moveTo(sp.x, sp.y); ctx.lineTo(tp.x, tp.y);
          ctx.strokeStyle = strength > 0 ? VERDIGRIS : OXIDE;
          ctx.lineWidth = Math.abs(strength) * 6;
          ctx.globalAlpha = 0.25;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }

      for (let i = 0; i < nDims; i++) {
        const pos = cwPositions[dims[i]];
        const val = composites[dims[i]] || 0;
        const r = 2 + val * 3;
        ctx.beginPath(); ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
        ctx.fillStyle = EMERGENCE_COLORS[dims[i]] || INK;
        ctx.fill();
      }
    }

    // Sparklines
    if (history.length > 1) {
      const sparkY = margin.top + ih * 0.78;
      const sparkH = ih * 0.14;
      const sparkW = iw - 20;
      const sparkX = margin.left + 10;

      ctx.strokeStyle = INK_FAINT;
      ctx.lineWidth = 0.25;
      ctx.beginPath(); ctx.moveTo(sparkX, sparkY - 10); ctx.lineTo(sparkX + sparkW, sparkY - 10); ctx.stroke();
      ctx.fillStyle = INK_LIGHT;
      ctx.font = `600 7px ${FONT}`;
      ctx.textAlign = "left";
      ctx.fillText("TEMPORAL EVOLUTION", sparkX, sparkY - 2);

      ctx.font = `300 5px ${FONT}`;
      ctx.fillStyle = INK_FAINT;
      ctx.textAlign = "center";
      const maxPoints = history.length;
      for (let p = 0; p < maxPoints; p += Math.max(1, Math.floor(maxPoints / 8))) {
        const x = sparkX + (p / (maxPoints - 1)) * sparkW;
        ctx.fillText("Y" + (history[p].year || p), x, sparkY + sparkH + 10);
      }

      ctx.strokeStyle = GRID;
      ctx.lineWidth = 0.12;
      for (let g = 0; g <= 4; g++) {
        const gy = sparkY + (g / 4) * sparkH;
        ctx.beginPath(); ctx.moveTo(sparkX, gy); ctx.lineTo(sparkX + sparkW, gy); ctx.stroke();
      }

      for (let d = 0; d < nDims; d++) {
        const dim = dims[d];
        const color = EMERGENCE_COLORS[dim] || INK;
        ctx.strokeStyle = color;
        ctx.lineWidth = 0.8;
        ctx.globalAlpha = 0.6;
        ctx.beginPath();
        for (let p = 0; p < maxPoints; p++) {
          const val = (history[p].composites || {})[dim] || 0;
          const x = sparkX + (p / Math.max(1, maxPoints - 1)) * sparkW;
          const y = sparkY + sparkH - val * sparkH;
          if (p === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.stroke();
        ctx.globalAlpha = 1;

        const lastVal = (history[maxPoints - 1].composites || {})[dim] || 0;
        const lastX = sparkX + sparkW;
        const lastY = sparkY + sparkH - lastVal * sparkH;
        ctx.fillStyle = color;
        ctx.font = `300 5px ${FONT}`;
        ctx.textAlign = "left";
        ctx.fillText(EMERGENCE_LABELS[dim], lastX + 3, lastY + 2);
      }
    }

    // Bottom legend
    const ly = h - 42;
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.3;
    ctx.beginPath(); ctx.moveTo(24, ly - 6); ctx.lineTo(w - 24, ly - 6); ctx.stroke();

    ctx.fillStyle = INK_LIGHT;
    ctx.font = `600 7px ${FONT}`;
    ctx.textAlign = "left";
    ctx.fillText("READING THE OBSERVATORY", 30, ly + 4);
    ctx.font = `300 7px ${FONT}`;
    ctx.fillStyle = SEPIA;
    ctx.fillText(
      "Central radar: 13 emergent dimensions with inter-dimension coupling (0-100%). Faded polygons = previous states.",
      30, ly + 14
    );
    ctx.fillText(
      "Warning indicators from critical slowing down detection (Scheffer 2009). Sparklines track temporal evolution.",
      30, ly + 24
    );

    setMeta("Thirteen emergent properties with bidirectional coupling. Radar shows coupled composites. Hatched fill = pen-plotter compatible.");
  }

  // ── Meta / Export ─────────────────────────────────────────────────

  function setMeta(text) {
    document.getElementById("artifact-meta").textContent = text;
  }

  function exportPNG() {
    const canvas = document.getElementById("artifact-canvas");
    const link = document.createElement("a");
    link.download = `civgraph-${Date.now()}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  function exportPDF() {
    const canvas = document.getElementById("artifact-canvas");
    const { jsPDF } = window.jspdf;
    const aspect = canvas.width / canvas.height;
    const orientation = aspect > 1 ? "landscape" : "portrait";
    const pdf = new jsPDF({
      orientation, unit: "px",
      format: [canvas.width, canvas.height],
      hotfixes: ["px_scaling"],
    });
    pdf.addImage(canvas.toDataURL("image/png", 1.0), "PNG", 0, 0, canvas.width, canvas.height);
    pdf.save(`civgraph-${Date.now()}.pdf`);
  }

  return {
    renderAnatomies,
    renderTopography,
    renderConstellation,
    renderHeatmap,
    renderSeismograph,
    renderCityPulse,
    renderEmergence,
    exportPNG,
    exportPDF,
  };
})();
