/**
 * CivGraph - Artifact Renderers
 *
 * Five print-quality visualizations rendered to high-resolution canvas.
 * Aesthetic: scientific engraving / naturalist specimen plate.
 * Ivory backgrounds, fine ink lines, crosshatching, serif typography.
 *
 * 1. Agent Anatomies    - specimen plate of individual glyphs encoding
 *                         intention, constraint, and agency
 * 2. Influence Topography - cartographic survey with crosshatching
 * 3. Clan Constellations  - astronomical star chart
 * 4. Opinion Heatmap      - textile weave pattern
 * 5. Event Seismograph    - strip-chart waveforms
 */

const Artifacts = (() => {
  // ── Engraving palette (anti-zeitgeist: warm, muted, archival) ──────────
  const IVORY = "#f5f0e8";
  const INK = "#1a1a2e";
  const INK_LIGHT = "#3d3d5c";
  const INK_FAINT = "#8888a0";
  const SEPIA = "#6b5b4f";
  const INDIGO = "#2e4057";
  const OCHRE = "#b08f4a";
  const OXIDE = "#8b3a3a";
  const VERDIGRIS = "#3a7d6e";
  const SLATE = "#5a6575";

  const CLAN_INKS = [
    "#2e4057", "#8b3a3a", "#3a7d6e", "#b08f4a", "#5a4080",
    "#6b5b4f", "#2a6b4f", "#804040", "#40608b", "#7a6b30",
    "#4a3060", "#3a6b8b", "#8b6b3a", "#5b3a6b", "#3a8b5b",
    "#6b3a5b", "#4a7060", "#8b5a3a", "#3a4a7b", "#6b7a3a",
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

  // ── Shared drawing primitives ─────────────────────────────────────────

  // A2 at 300 DPI = 4961 x 7016 px (portrait) / 7016 x 4961 (landscape)
  const FORMAT_PRESETS = {
    "1":    { label: "1x screen",   scale: 1 },
    "2":    { label: "2x print",    scale: 2 },
    "4":    { label: "4x high-res", scale: 4 },
    "8":    { label: "8x poster",   scale: 8 },
    "a2":   { label: "A2 300dpi",   w: 7016, h: 4961 },  // landscape
    "a2p":  { label: "A2 portrait", w: 4961, h: 7016 },
  };

  function getCanvasCtx() {
    const fmt = document.getElementById("res-select").value;
    const preset = FORMAT_PRESETS[fmt] || FORMAT_PRESETS["2"];
    const canvas = document.getElementById("artifact-canvas");
    const wrap = document.getElementById("artifact-canvas-wrap");

    let baseW, baseH, scale;

    if (preset.w) {
      // Fixed pixel format (A2 etc) — compute base from target
      scale = 1;
      baseW = preset.w;
      baseH = preset.h;
      canvas.width = baseW;
      canvas.height = baseH;
      // Fit to screen for preview
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

    // Ivory paper background
    ctx.fillStyle = IVORY;
    ctx.fillRect(0, 0, baseW, baseH);

    // Subtle paper grain texture
    ctx.globalAlpha = 0.025;
    for (let i = 0; i < baseW * baseH * 0.003; i++) {
      const x = Math.random() * baseW;
      const y = Math.random() * baseH;
      ctx.fillStyle = Math.random() > 0.5 ? "#a09880" : "#d0c8b8";
      ctx.fillRect(x, y, Math.random() * 1.5, Math.random() * 1.5);
    }
    ctx.globalAlpha = 1;

    return { ctx, w: baseW, h: baseH, canvas, scale };
  }

  // Plate border: fine double rule + registration marks
  function drawRegistration(ctx, w, h) {
    // Outer rule
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.4;
    ctx.strokeRect(8, 8, w - 16, h - 16);
    // Inner rule (thinner)
    ctx.lineWidth = 0.15;
    ctx.strokeRect(12, 12, w - 24, h - 24);
    // Corner crosses
    const m = 8;
    const l = 6;
    [[m, m], [w - m, m], [m, h - m], [w - m, h - m]].forEach(([x, y]) => {
      ctx.lineWidth = 0.3;
      ctx.beginPath();
      ctx.moveTo(x - l, y); ctx.lineTo(x + l, y);
      ctx.moveTo(x, y - l); ctx.lineTo(x, y + l);
      ctx.stroke();
    });
  }

  function drawPlateTitle(ctx, w, title, subtitle, plateNum) {
    // Title
    ctx.fillStyle = INK;
    ctx.font = "italic 18px Georgia, 'Times New Roman', serif";
    ctx.textAlign = "center";
    ctx.fillText(title, w / 2, 34);
    // Subtitle
    ctx.font = "11px Georgia, serif";
    ctx.fillStyle = SEPIA;
    ctx.fillText(subtitle, w / 2, 50);
    // Plate number (left)
    ctx.font = "italic 9px Georgia, serif";
    ctx.fillStyle = INK_FAINT;
    ctx.textAlign = "left";
    ctx.fillText("Plate " + (plateNum || "I"), 20, 34);
    // Colophon (right)
    ctx.textAlign = "right";
    ctx.fillText("CivGraph", w - 20, 28);
    ctx.font = "8px Georgia, serif";
    ctx.fillText(new Date().toISOString().slice(0, 10), w - 20, 40);
    ctx.textAlign = "left";
    // Rule beneath title
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.25;
    ctx.beginPath();
    ctx.moveTo(20, 56);
    ctx.lineTo(w - 20, 56);
    ctx.stroke();
    // Faint decorative rule (double line)
    ctx.lineWidth = 0.12;
    ctx.beginPath();
    ctx.moveTo(20, 58);
    ctx.lineTo(w - 20, 58);
    ctx.stroke();
  }

  // Crosshatch a region (for engraving shading)
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

  // Stipple a circular region
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

  // ═══════════════════════════════════════════════════════════════════════
  // 1. AGENT ANATOMIES - Specimen Plate
  //
  // Each agent rendered as a unique radial glyph.
  //   Core (filled circle)    = AGENCY:     radius = influence x assertiveness
  //   Inner ring segments     = CONSTRAINT: loyalty fills clockwise, resources
  //                             counterclockwise; openness = ring gap width
  //   Outer spokes            = INTENTION:  one spoke per interest at fixed
  //                             angle, spoke weight = how much that domain
  //                             drives them; political lean rotates the whole
  //                             glyph
  //   Stipple density         = degree (connectedness)
  //
  // Top 80 agents arranged in a specimen grid with annotations.
  // ═══════════════════════════════════════════════════════════════════════

  function renderAnatomies(nodes) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Anatomies of Agency",
      "Specimen plate: intention, constraint, and agency of the city's most influential individuals",
      "I"
    );

    const sorted = [...nodes].sort((a, b) => b.influence - a.influence);
    const subjects = sorted.slice(0, 80);

    const cols = 10;
    const rows = 8;
    const margin = { top: 68, right: 30, bottom: 60, left: 30 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;
    const cellW = iw / cols;
    const cellH = ih / rows;
    const glyphR = Math.min(cellW, cellH) * 0.32;

    // Clan index for color
    const clanSet = [...new Set(nodes.map((n) => n.clan))].sort();
    const clanIdx = {};
    clanSet.forEach((c, i) => { clanIdx[c] = i; });

    for (let i = 0; i < subjects.length; i++) {
      const n = subjects[i];
      const col = i % cols;
      const row = Math.floor(i / cols);
      const cx = margin.left + col * cellW + cellW / 2;
      const cy = margin.top + row * cellH + cellH / 2 - 6;

      drawAgentGlyph(ctx, cx, cy, glyphR, n, clanIdx);

      // Name label beneath
      ctx.fillStyle = INK;
      ctx.font = "7px Georgia, serif";
      ctx.textAlign = "center";
      const surname = n.name.split(" ").slice(-1)[0];
      ctx.fillText(surname, cx, cy + glyphR + 11);
      // Rank number
      ctx.fillStyle = INK_FAINT;
      ctx.font = "italic 6px Georgia, serif";
      ctx.fillText((i + 1).toString(), cx, cy + glyphR + 19);
      ctx.textAlign = "left";
    }

    // ── Legend at bottom ──────────────────────────────────────────────
    const ly = h - 52;
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.3;
    ctx.beginPath();
    ctx.moveTo(24, ly - 6);
    ctx.lineTo(w - 24, ly - 6);
    ctx.stroke();

    ctx.fillStyle = SEPIA;
    ctx.font = "italic 9px Georgia, serif";
    ctx.textAlign = "left";
    ctx.fillText("Reading the glyph:", 30, ly + 6);
    ctx.font = "8px Georgia, serif";
    ctx.fillStyle = INK_LIGHT;
    ctx.fillText(
      "Core dot = agency (influence x assertiveness).  " +
      "Four ring arcs = capital: green = economic, purple = cultural, blue = social, ochre = symbolic.  " +
      "Arc length = capital volume.",
      30, ly + 18
    );
    ctx.fillText(
      "Spokes = intentions (interest domains at fixed angles).  Glyph rotation = political lean.  " +
      "Openness gap at top.  Stipple density = network degree.  Ink color = clan.",
      30, ly + 30
    );

    setMeta(
      "Top 80 agents by influence. Each glyph encodes: core = agency (influence x assertiveness), " +
      "four ring arcs = capital (economic/cultural/social/symbolic), spokes = interest domains, " +
      "rotation = political lean, stipple = network degree. Export at 4x or 8x for print."
    );
  }

  function drawAgentGlyph(ctx, cx, cy, maxR, agent, clanIdx) {
    const ink = CLAN_INKS[clanIdx[agent.clan] % CLAN_INKS.length];
    const pol = POL_NUM[agent.politics] || 0;
    const rotation = (pol / 3) * (Math.PI / 6);

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(rotation);

    const cap = agent.capital || {};
    const ec = cap.economic || 0;
    const cu = cap.cultural || 0;
    const so = cap.social || 0;
    const sy = cap.symbolic || 0;
    const influence = agent.influence || 0;
    const assertiveness = agent.assertiveness || 0.5;
    const openness = agent.openness || 0.5;
    const loyalty = agent.loyalty || 0.5;
    const degree = agent.degree || 1;
    const interests = agent.interests || [];

    // ── Outer spokes (INTENTION: interests) ─────────────────────────
    ctx.strokeStyle = ink;
    ctx.lineWidth = 0.6;
    const spokeR = maxR * 0.95;
    const innerSpokeR = maxR * 0.55;
    for (const interest of interests) {
      const angle = INTEREST_ANGLES[interest];
      if (angle === undefined) continue;
      ctx.beginPath();
      ctx.moveTo(Math.cos(angle) * innerSpokeR, Math.sin(angle) * innerSpokeR);
      ctx.lineTo(Math.cos(angle) * spokeR, Math.sin(angle) * spokeR);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(Math.cos(angle) * spokeR, Math.sin(angle) * spokeR, 1.2, 0, Math.PI * 2);
      ctx.fillStyle = ink;
      ctx.fill();
    }

    // ── Tick marks for interest positions ────────────────────────────
    ctx.strokeStyle = ink;
    ctx.globalAlpha = 0.12;
    ctx.lineWidth = 0.3;
    for (const key of ALL_INTERESTS) {
      const angle = INTEREST_ANGLES[key];
      ctx.beginPath();
      ctx.moveTo(Math.cos(angle) * maxR * 0.88, Math.sin(angle) * maxR * 0.88);
      ctx.lineTo(Math.cos(angle) * maxR * 0.96, Math.sin(angle) * maxR * 0.96);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // ── Four capital quadrant arcs (CONSTRAINT/CAPACITY) ────────────
    // Each capital type gets a quadrant arc; arc length = capital amount
    const ringR = maxR * 0.48;
    const capColors = ["#3a7d6e", "#5a4080", "#2e6090", "#b08f4a"]; // ec, cu, so, sy
    const capValues = [ec, cu, so, sy];
    const quadrants = [
      -Math.PI / 2,    // top: economic
      0,               // right: cultural
      Math.PI / 2,     // bottom: social
      Math.PI,         // left: symbolic
    ];

    // Faint full ring
    ctx.strokeStyle = ink;
    ctx.globalAlpha = 0.12;
    ctx.lineWidth = 0.4;
    ctx.beginPath();
    ctx.arc(0, 0, ringR, 0, Math.PI * 2);
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Capital arcs
    for (let q = 0; q < 4; q++) {
      const startAngle = quadrants[q] - (Math.PI / 4);
      const arcLength = capValues[q] * (Math.PI / 2); // max = full quadrant
      if (arcLength < 0.05) continue;
      ctx.strokeStyle = capColors[q];
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      ctx.arc(0, 0, ringR, startAngle, startAngle + arcLength);
      ctx.stroke();
    }

    // Small capital labels at quadrant midpoints
    ctx.font = "4px Georgia, serif";
    ctx.fillStyle = ink;
    ctx.globalAlpha = 0.35;
    ctx.textAlign = "center";
    const labelR = ringR + 6;
    const capLabels = ["Ec", "Cu", "So", "Sy"];
    for (let q = 0; q < 4; q++) {
      const a = quadrants[q];
      ctx.fillText(capLabels[q], Math.cos(a) * labelR, Math.sin(a) * labelR + 1.5);
    }
    ctx.globalAlpha = 1;
    ctx.textAlign = "left";

    // ── Openness gap marker ─────────────────────────────────────────
    const gapLen = openness * 6;
    ctx.strokeStyle = ink;
    ctx.lineWidth = 0.4;
    ctx.globalAlpha = 0.4;
    ctx.beginPath();
    ctx.moveTo(-gapLen, -(ringR + 4));
    ctx.lineTo(gapLen, -(ringR + 4));
    ctx.stroke();
    ctx.globalAlpha = 1;

    // ── Core dot (AGENCY: influence x assertiveness) ────────────────
    const coreR = 1.5 + influence * assertiveness * maxR * 0.32;
    ctx.beginPath();
    ctx.arc(0, 0, coreR, 0, Math.PI * 2);
    ctx.fillStyle = ink;
    ctx.fill();

    // ── Stipple (social connectedness) ──────────────────────────────
    const stippleDensity = Math.min(1, Math.sqrt(degree) / 6);
    if (stippleDensity > 0.1) {
      stipple(ctx, 0, 0, maxR * 0.35, stippleDensity * 0.7, ink + "30");
    }

    ctx.restore();
  }

  // ═══════════════════════════════════════════════════════════════════════
  // 2. INFLUENCE TOPOGRAPHY - Cartographic survey
  // ═══════════════════════════════════════════════════════════════════════

  function renderTopography(nodes) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Survey of Influence",
      "Topographic elevation map: influence density as terrain",
      "II"
    );

    const margin = { top: 66, right: 50, bottom: 50, left: 40 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

    const xs = nodes.map((n) => n.x || 0);
    const ys = nodes.map((n) => n.y || 0);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;

    function toCanvas(n) {
      return {
        cx: margin.left + ((n.x - minX) / rangeX) * iw,
        cy: margin.top + ((n.y - minY) / rangeY) * ih,
      };
    }

    // Grid lines (survey grid)
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.15;
    const gridStep = Math.min(iw, ih) / 20;
    for (let x = margin.left; x <= margin.left + iw; x += gridStep) {
      ctx.beginPath();
      ctx.moveTo(x, margin.top);
      ctx.lineTo(x, margin.top + ih);
      ctx.stroke();
    }
    for (let y = margin.top; y <= margin.top + ih; y += gridStep) {
      ctx.beginPath();
      ctx.moveTo(margin.left, y);
      ctx.lineTo(margin.left + iw, y);
      ctx.stroke();
    }

    // Build elevation field
    const gridRes = 100;
    const field = new Float64Array(gridRes * gridRes);
    const cellW = iw / gridRes;
    const cellH = ih / gridRes;
    const bandwidth = Math.max(iw, ih) * 0.07;

    for (const node of nodes) {
      const { cx, cy } = toCanvas(node);
      const weight = node.influence * 2 + Math.sqrt(node.degree || 1) * 0.3;
      const r = Math.ceil(bandwidth / cellW) + 1;
      const gi = Math.floor((cx - margin.left) / cellW);
      const gj = Math.floor((cy - margin.top) / cellH);
      for (let di = -r; di <= r; di++) {
        for (let dj = -r; dj <= r; dj++) {
          const ii = gi + di;
          const jj = gj + dj;
          if (ii < 0 || ii >= gridRes || jj < 0 || jj >= gridRes) continue;
          const px = margin.left + ii * cellW + cellW / 2;
          const py = margin.top + jj * cellH + cellH / 2;
          const dx = px - cx;
          const dy = py - cy;
          const val = weight * Math.exp(-(dx * dx + dy * dy) / (2 * bandwidth * bandwidth));
          field[jj * gridRes + ii] += val;
        }
      }
    }

    let maxVal = 0;
    for (let i = 0; i < field.length; i++) if (field[i] > maxVal) maxVal = field[i];
    if (maxVal > 0) for (let i = 0; i < field.length; i++) field[i] /= maxVal;

    // Render as crosshatched elevation bands
    const bands = 8;
    for (let b = 0; b < bands; b++) {
      const lo = b / bands;
      const hi = (b + 1) / bands;
      const density = (b + 1) / bands;
      const angle = Math.PI / 4 + b * 0.15;

      for (let j = 0; j < gridRes; j++) {
        for (let i = 0; i < gridRes; i++) {
          const v = field[j * gridRes + i];
          if (v >= lo && v < hi) {
            const x = margin.left + i * cellW;
            const y = margin.top + j * cellH;
            crosshatch(ctx, x, y, cellW + 0.5, cellH + 0.5, density * 2, angle, INDIGO, density * 0.35);
          }
        }
      }
    }

    // Contour lines (engraved)
    const contourLevels = [0.15, 0.3, 0.45, 0.6, 0.75, 0.9];
    contourLevels.forEach((level, li) => {
      ctx.strokeStyle = INK;
      ctx.lineWidth = li > 3 ? 0.8 : 0.4;
      ctx.globalAlpha = 0.5 + li * 0.08;

      for (let j = 0; j < gridRes - 1; j++) {
        for (let i = 0; i < gridRes - 1; i++) {
          const v00 = field[j * gridRes + i];
          const v10 = field[j * gridRes + i + 1];
          const v01 = field[(j + 1) * gridRes + i];
          const v11 = field[(j + 1) * gridRes + i + 1];
          const edges = [];
          if ((v00 < level) !== (v10 < level)) {
            const t = (level - v00) / (v10 - v00);
            edges.push([margin.left + (i + t) * cellW, margin.top + j * cellH]);
          }
          if ((v01 < level) !== (v11 < level)) {
            const t = (level - v01) / (v11 - v01);
            edges.push([margin.left + (i + t) * cellW, margin.top + (j + 1) * cellH]);
          }
          if ((v00 < level) !== (v01 < level)) {
            const t = (level - v00) / (v01 - v00);
            edges.push([margin.left + i * cellW, margin.top + (j + t) * cellH]);
          }
          if ((v10 < level) !== (v11 < level)) {
            const t = (level - v10) / (v11 - v10);
            edges.push([margin.left + (i + 1) * cellW, margin.top + (j + t) * cellH]);
          }
          if (edges.length >= 2) {
            ctx.beginPath();
            ctx.moveTo(edges[0][0], edges[0][1]);
            ctx.lineTo(edges[1][0], edges[1][1]);
            ctx.stroke();
          }
        }
      }
      ctx.globalAlpha = 1;
    });

    // Plot agents as small circles with crosshairs
    for (const node of nodes) {
      const { cx, cy } = toCanvas(node);
      const r = 1 + node.influence * 2.5;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fillStyle = OXIDE;
      ctx.globalAlpha = 0.4 + node.influence * 0.5;
      ctx.fill();
      ctx.globalAlpha = 1;
    }

    // Label top influencers
    const top = [...nodes].sort((a, b) => b.influence - a.influence).slice(0, 15);
    ctx.font = "italic 7px Georgia, serif";
    ctx.fillStyle = OXIDE;
    for (const node of top) {
      const { cx, cy } = toCanvas(node);
      ctx.fillText(node.name.split(" ").slice(-1)[0], cx + 4, cy - 3);
    }

    // Elevation legend
    const lx = w - 44;
    const ly = margin.top + 10;
    const lh = ih * 0.35;
    ctx.font = "italic 7px Georgia, serif";
    ctx.fillStyle = SEPIA;
    ctx.textAlign = "center";
    ctx.fillText("HIGH", lx + 6, ly - 4);
    for (let i = 0; i < lh; i++) {
      const v = 1 - i / lh;
      const density = v * 2;
      crosshatch(ctx, lx - 2, ly + i, 16, 1.5, density, Math.PI / 4, INDIGO, v * 0.4);
    }
    ctx.fillText("LOW", lx + 6, ly + lh + 12);
    ctx.textAlign = "left";

    setMeta("Crosshatch density = influence concentration. Contour lines at 15% intervals. " +
      "Red dots = agents, scaled by influence. Survey grid overlay.");
  }

  // ═══════════════════════════════════════════════════════════════════════
  // 3. CLAN CONSTELLATIONS
  // ═══════════════════════════════════════════════════════════════════════

  function renderConstellation(nodes) {
    const { ctx, w, h } = getCanvasCtx();

    // Deep paper background for star chart
    ctx.fillStyle = "#1a1a28";
    ctx.fillRect(0, 0, w, h);

    // Star field
    for (let i = 0; i < 600; i++) {
      const x = Math.random() * w;
      const y = Math.random() * h;
      const r = Math.random() * 0.6;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200,200,220,${Math.random() * 0.2 + 0.03})`;
      ctx.fill();
    }

    // Title in light ink
    ctx.fillStyle = "#c0b8a8";
    ctx.font = "italic 16px Georgia, 'Times New Roman', serif";
    ctx.textAlign = "center";
    ctx.fillText("Constellations of Clan", w / 2, 32);
    ctx.font = "10px Georgia, serif";
    ctx.fillStyle = "#807868";
    ctx.fillText(`${nodes.length} stars : horizontal = political axis : vertical = influence`, w / 2, 48);
    ctx.textAlign = "left";
    ctx.fillStyle = "#807868";
    ctx.font = "italic 9px Georgia, serif";
    ctx.fillText("Plate III", 24, 32);
    ctx.textAlign = "right";
    ctx.fillText("CivGraph", w - 24, 32);
    ctx.textAlign = "left";

    const margin = { top: 62, right: 40, bottom: 50, left: 40 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

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
      const color = CLAN_INKS[ci % CLAN_INKS.length];
      const positions = members.map((n, i) => ({ ...starPos(n, i), node: n }));

      // MST constellation lines
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

      // Draw lines with warm tint
      ctx.strokeStyle = color;
      ctx.globalAlpha = 0.2;
      ctx.lineWidth = 0.6;
      for (const [a, b] of mstEdges) {
        ctx.beginPath();
        ctx.moveTo(positions[a].x, positions[a].y);
        ctx.lineTo(positions[b].x, positions[b].y);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // Stars
      for (const pos of positions) {
        const inf = pos.node.influence;
        const r = 0.8 + inf * 4;

        // Soft glow
        const grad = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, r * 3);
        grad.addColorStop(0, color + "80");
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
        ctx.fillRect(pos.x - r * 3, pos.y - r * 3, r * 6, r * 6);

        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        // Cross flare for high influence
        if (inf > 0.5) {
          ctx.strokeStyle = color;
          ctx.globalAlpha = 0.3;
          ctx.lineWidth = 0.4;
          const fl = r * 2.5;
          ctx.beginPath();
          ctx.moveTo(pos.x - fl, pos.y); ctx.lineTo(pos.x + fl, pos.y);
          ctx.moveTo(pos.x, pos.y - fl); ctx.lineTo(pos.x, pos.y + fl);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }

      // Clan label
      const avg_x = positions.reduce((s, p) => s + p.x, 0) / positions.length;
      const avg_y = positions.reduce((s, p) => s + p.y, 0) / positions.length;
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.6;
      ctx.font = "italic 7px Georgia, serif";
      ctx.textAlign = "center";
      ctx.fillText(clan, avg_x, avg_y - 10);
      ctx.globalAlpha = 1;
      ctx.textAlign = "left";
    }

    // Axis labels
    ctx.fillStyle = "#807868";
    ctx.font = "8px Georgia, serif";
    ctx.textAlign = "center";
    const labels = ["Far Left", "Left", "Centre-Left", "Centre", "Centre-Right", "Right", "Far Right"];
    for (let i = 0; i < 7; i++) {
      ctx.fillText(labels[i], margin.left + ((i + 0.5) / 7) * iw, h - margin.bottom + 16);
    }
    ctx.textAlign = "left";

    setMeta("Each constellation = one clan. Star brightness = influence. " +
      "Horizontal = political lean. Lines = minimum spanning tree within clan.");
  }

  // ═══════════════════════════════════════════════════════════════════════
  // 4. OPINION HEATMAP
  // ═══════════════════════════════════════════════════════════════════════

  function renderHeatmap(nodes) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Fabric of Opinion",
      "Rows = clans, columns = topics. Hatching density = opinion strength. Cross-hatch = disagreement.",
      "IV"
    );

    const topicSet = new Set();
    for (const n of nodes) {
      if (n._opinions) for (const k of Object.keys(n._opinions)) topicSet.add(k);
    }
    const topics = [...topicSet];
    if (topics.length === 0) {
      ctx.fillStyle = SEPIA;
      ctx.font = "italic 12px Georgia, serif";
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
        const opinions = members.map((n) => (n._opinions && n._opinions[topic]) || 0).filter((v) => v !== 0);
        const x = margin.left + col * cellW;
        const y = margin.top + row * cellH;

        // Cell border
        ctx.strokeStyle = INK_FAINT;
        ctx.lineWidth = 0.2;
        ctx.strokeRect(x, y, cellW, cellH);

        if (opinions.length === 0) continue;

        const avg = opinions.reduce((s, v) => s + v, 0) / opinions.length;
        const variance = opinions.reduce((s, v) => s + (v - avg) ** 2, 0) / opinions.length;
        const strength = Math.abs(avg);

        // Direction: support = vertical hatching (VERDIGRIS), oppose = horizontal (OXIDE)
        const color = avg > 0 ? VERDIGRIS : OXIDE;
        const angle = avg > 0 ? Math.PI / 2 : 0;
        crosshatch(ctx, x + 1, y + 1, cellW - 2, cellH - 2, strength * 3, angle, color, strength * 0.6);

        // Variance = additional cross-hatching at perpendicular angle
        if (variance > 0.04) {
          crosshatch(ctx, x + 1, y + 1, cellW - 2, cellH - 2,
            variance * 8, angle + Math.PI / 2, SEPIA, variance * 0.5);
        }

        // Value
        if (cellW > 28 && cellH > 12) {
          ctx.fillStyle = INK;
          ctx.globalAlpha = 0.4 + strength * 0.4;
          ctx.font = `${Math.min(8, cellH * 0.4)}px Georgia, serif`;
          ctx.textAlign = "center";
          ctx.fillText(avg.toFixed(2), x + cellW / 2, y + cellH / 2 + 3);
          ctx.textAlign = "left";
          ctx.globalAlpha = 1;
        }
      }
    }

    // Row labels
    ctx.fillStyle = INK;
    ctx.font = `${Math.min(9, cellH * 0.55)}px Georgia, serif`;
    ctx.textAlign = "right";
    for (let i = 0; i < clanNames.length; i++) {
      ctx.fillText(clanNames[i], margin.left - 8, margin.top + i * cellH + cellH / 2 + 3);
    }
    ctx.textAlign = "left";

    // Column labels
    ctx.font = `${Math.min(8, cellW * 0.7)}px Georgia, serif`;
    ctx.fillStyle = INK;
    for (let i = 0; i < topics.length; i++) {
      ctx.save();
      ctx.translate(margin.left + i * cellW + cellW / 2, margin.top - 6);
      ctx.rotate(-Math.PI / 3);
      ctx.fillText(topics[i], 0, 0);
      ctx.restore();
    }

    setMeta("Vertical hatching (green ink) = support. Horizontal hatching (red ink) = oppose. " +
      "Perpendicular cross-hatch (sepia) = internal clan disagreement.");
  }

  // ═══════════════════════════════════════════════════════════════════════
  // 5. EVENT SEISMOGRAPH
  // ═══════════════════════════════════════════════════════════════════════

  function renderSeismograph(nodes, links, events) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Seismograph of Events",
      `${events.length} event${events.length !== 1 ? "s" : ""} recorded. Amplitude = cascade reach per propagation step.`,
      "V"
    );

    if (events.length === 0) {
      ctx.fillStyle = SEPIA;
      ctx.font = "italic 12px Georgia, serif";
      ctx.fillText("No events recorded. Fire some events first.", 40, 100);
      setMeta("Trigger events to see their seismograph traces.");
      return;
    }

    const margin = { top: 70, right: 40, bottom: 40, left: 170 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;
    const rowH = Math.min(70, ih / events.length);
    const maxSteps = Math.max(...events.map((e) => e.propagation.length));

    for (let ei = 0; ei < events.length; ei++) {
      const event = events[ei];
      const baseY = margin.top + ei * rowH + rowH / 2;
      const ink = event.sentiment > 0.2 ? VERDIGRIS : event.sentiment < -0.2 ? OXIDE : SLATE;

      // Baseline (fine rule)
      ctx.strokeStyle = INK_FAINT;
      ctx.lineWidth = 0.2;
      ctx.beginPath();
      ctx.moveTo(margin.left, baseY);
      ctx.lineTo(margin.left + iw, baseY);
      ctx.stroke();

      // Waveform
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
      // Decay tail
      const lastX = margin.left + event.propagation.length * stepW;
      for (let t = 0; t < 20; t++) {
        const x = lastX + t * (stepW / 5);
        if (x > margin.left + iw) break;
        points.push({ x, y: baseY - Math.sin(t * 1.5) * 2.5 * Math.exp(-t * 0.3) });
      }
      points.push({ x: margin.left + iw, y: baseY });

      // Draw
      ctx.strokeStyle = ink;
      ctx.lineWidth = 0.9;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
      ctx.stroke();

      // Labels
      ctx.fillStyle = ink;
      ctx.font = "bold 8px Georgia, serif";
      ctx.textAlign = "right";
      ctx.fillText(event.title, margin.left - 10, baseY + 3);
      ctx.fillStyle = INK_FAINT;
      ctx.font = "italic 6px Georgia, serif";
      ctx.fillText(`${event.total_affected} affected`, margin.left - 10, baseY + 12);
      ctx.textAlign = "left";

      // Origin mark
      ctx.beginPath();
      ctx.arc(margin.left + 3, baseY, 2, 0, Math.PI * 2);
      ctx.fillStyle = ink;
      ctx.fill();
    }

    // Step markers
    ctx.fillStyle = INK_FAINT;
    ctx.font = "7px Georgia, serif";
    ctx.textAlign = "center";
    const sw = iw / (maxSteps + 1);
    for (let i = 0; i <= maxSteps; i++) {
      ctx.fillText(`step ${i}`, margin.left + i * sw, h - margin.bottom + 14);
    }
    ctx.textAlign = "left";

    setMeta("Each row = one event. Amplitude = agents reached per step. " +
      "Green ink = positive sentiment, red = negative, gray = neutral.");
  }

  // ═══════════════════════════════════════════════════════════════════════
  // 6. CITY PULSE — layered time-series of macro-environment indicators
  //
  // Horizontal strips, one per domain (economy, housing, migration,
  // culture, governance). Each strip shows its indicators as overlapping
  // ink traces on ivory, with crosshatch fill below the trace.
  // ═══════════════════════════════════════════════════════════════════════

  function renderCityPulse(history, meta) {
    const { ctx, w, h } = getCanvasCtx();
    drawRegistration(ctx, w, h);
    drawPlateTitle(ctx, w,
      "Pulse of the City",
      `${history.length} year${history.length !== 1 ? "s" : ""} of macro-environment evolution`,
      "VI"
    );

    if (history.length < 2) {
      ctx.fillStyle = SEPIA;
      ctx.font = "italic 12px Georgia, serif";
      ctx.fillText("Advance the simulation (tick) to see environment evolution.", 40, 100);
      setMeta("Use the tick button to advance years and generate environment history.");
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

    const domainInks = [INDIGO, OCHRE, VERDIGRIS, "#5a4080", OXIDE];

    for (let di = 0; di < domainNames.length; di++) {
      const domain = domainNames[di];
      const keys = domains[domain];
      const baseY = margin.top + di * stripH;
      const ink = domainInks[di % domainInks.length];

      // Domain label
      ctx.fillStyle = ink;
      ctx.font = "italic 9px Georgia, serif";
      ctx.textAlign = "right";
      ctx.fillText(domain.charAt(0).toUpperCase() + domain.slice(1), margin.left - 12, baseY + stripH / 2 + 3);
      ctx.textAlign = "left";

      // Baseline
      ctx.strokeStyle = INK_FAINT;
      ctx.lineWidth = 0.2;
      ctx.beginPath();
      ctx.moveTo(margin.left, baseY + stripH - 2);
      ctx.lineTo(margin.left + iw, baseY + stripH - 2);
      ctx.stroke();

      // Each indicator as a trace
      for (let ki = 0; ki < keys.length; ki++) {
        const key = keys[ki];
        const ind = indicators[key];
        if (!ind) continue;
        const lo = ind.min, hi = ind.max;
        const range = hi - lo || 1;

        // Lighter ink for each subsequent indicator
        const alpha = 0.7 - ki * 0.12;
        ctx.strokeStyle = ink;
        ctx.globalAlpha = Math.max(0.2, alpha);
        ctx.lineWidth = ki === 0 ? 1.2 : 0.7;

        // Build trace points
        const points = [];
        for (let yi = 0; yi < years; yi++) {
          const val = history[yi][key] || 0;
          const norm = (val - lo) / range;
          const x = margin.left + (yi / (years - 1)) * iw;
          const y = baseY + stripH - 4 - norm * (stripH - 8);
          points.push({ x, y });
        }

        // Draw trace
        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);
        for (let i = 1; i < points.length; i++) {
          ctx.lineTo(points[i].x, points[i].y);
        }
        ctx.stroke();

        // Subtle fill below first trace only
        if (ki === 0) {
          ctx.globalAlpha = 0.04;
          ctx.fillStyle = ink;
          ctx.lineTo(points[points.length - 1].x, baseY + stripH - 2);
          ctx.lineTo(points[0].x, baseY + stripH - 2);
          ctx.closePath();
          ctx.fill();
        }

        // Label last value
        if (points.length > 0) {
          const last = points[points.length - 1];
          ctx.globalAlpha = Math.max(0.3, alpha);
          ctx.font = "5px Georgia, serif";
          ctx.fillStyle = ink;
          const label = ind.label.split(" ").slice(-1)[0];
          ctx.fillText(label, last.x + 3, last.y + 2);
        }

        ctx.globalAlpha = 1;
      }
    }

    // Year axis
    ctx.fillStyle = INK_FAINT;
    ctx.font = "7px Georgia, serif";
    ctx.textAlign = "center";
    const yearStep = Math.max(1, Math.floor(years / 10));
    for (let yi = 0; yi < years; yi += yearStep) {
      const x = margin.left + (yi / (years - 1 || 1)) * iw;
      ctx.fillText(`Y${history[yi].year}`, x, h - margin.bottom + 14);
    }
    ctx.textAlign = "left";

    setMeta("Five domain strips (economy, housing, migration, culture, governance). " +
      "Each trace = one indicator within the domain. " +
      "Advance simulation years to see the city's macro environment evolve.");
  }

  // ═══════════════════════════════════════════════════════════════════════
  // 7. EMERGENCE — Emergent Properties Observatory
  //
  // Scientific instrument panel showing 10 emergent dimensions as:
  //   - Central radar/spider chart (composite scores)
  //   - Surrounding detail panels for each dimension
  //   - Trend sparklines if history available
  //   - Research citation annotations
  // ═══════════════════════════════════════════════════════════════════════

  const EMERGENCE_COLORS = {
    polarization:             OXIDE,
    inequality:               "#8b3a3a",
    collective_intelligence:  VERDIGRIS,
    contagion_susceptibility: "#b08f4a",
    network_resilience:       INDIGO,
    phase_transitions:        "#804040",
    echo_chambers:            "#5a4080",
    power_law:                SLATE,
    institutional_trust:      "#2a6b4f",
    cultural_convergence:     SEPIA,
    information_theoretic:    "#4a6b8b",
    norm_emergence:           "#6b5b3a",
    segregation:              "#6b3a4a",
  };

  const EMERGENCE_LABELS = {
    polarization:             "Polarization",
    inequality:               "Inequality",
    collective_intelligence:  "Collective Intelligence",
    contagion_susceptibility: "Contagion Risk",
    network_resilience:       "Network Resilience",
    phase_transitions:        "Phase Transitions",
    echo_chambers:            "Echo Chambers",
    power_law:                "Power Law",
    institutional_trust:      "Institutional Trust",
    cultural_convergence:     "Cultural Convergence",
    information_theoretic:    "Information Integration",
    norm_emergence:           "Norm Emergence",
    segregation:              "Segregation",
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
      "Ten macro-phenomena arising from micro-level agent interaction",
      "VII"
    );

    if (!emergenceData || !emergenceData.current) {
      ctx.fillStyle = INK_FAINT;
      ctx.font = "14px Georgia, serif";
      ctx.textAlign = "center";
      ctx.fillText("No emergence data yet. Advance the simulation to generate readings.", w / 2, h / 2);
      setMeta("Advance the simulation (tick) to compute emergent properties.");
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

    // ── Central radar chart ──────────────────────────────────────────
    const radarCx = margin.left + iw * 0.5;
    const radarCy = margin.top + ih * 0.36;
    const radarR = Math.min(iw * 0.24, ih * 0.26);

    const dims = EMERGENCE_ORDER;
    const nDims = dims.length;

    // Draw concentric rings
    for (let ring = 1; ring <= 5; ring++) {
      const r = (ring / 5) * radarR;
      ctx.beginPath();
      ctx.arc(radarCx, radarCy, r, 0, Math.PI * 2);
      ctx.strokeStyle = INK_FAINT;
      ctx.lineWidth = ring === 5 ? 0.4 : 0.2;
      ctx.globalAlpha = 0.3;
      ctx.stroke();
      ctx.globalAlpha = 1;
      // Ring label
      if (ring % 2 === 0) {
        ctx.fillStyle = INK_FAINT;
        ctx.font = "5px Georgia, serif";
        ctx.textAlign = "left";
        ctx.fillText((ring * 20).toString(), radarCx + 2, radarCy - r + 3);
      }
    }

    // Draw axis lines and labels
    for (let i = 0; i < nDims; i++) {
      const angle = (i / nDims) * Math.PI * 2 - Math.PI / 2;
      const ex = radarCx + Math.cos(angle) * radarR;
      const ey = radarCy + Math.sin(angle) * radarR;

      ctx.beginPath();
      ctx.moveTo(radarCx, radarCy);
      ctx.lineTo(ex, ey);
      ctx.strokeStyle = INK_FAINT;
      ctx.lineWidth = 0.3;
      ctx.globalAlpha = 0.4;
      ctx.stroke();
      ctx.globalAlpha = 1;

      // Label (radial, no rotation for clarity with 13 spokes)
      const labelR = radarR + 10;
      const lx = radarCx + Math.cos(angle) * labelR;
      const ly = radarCy + Math.sin(angle) * labelR;
      ctx.fillStyle = EMERGENCE_COLORS[dims[i]] || INK;
      ctx.font = "bold 6px Georgia, serif";
      // Position text based on quadrant
      if (Math.abs(angle + Math.PI / 2) < 0.2) {
        ctx.textAlign = "center";  // top
      } else if (Math.cos(angle) < -0.1) {
        ctx.textAlign = "right";
      } else if (Math.cos(angle) > 0.1) {
        ctx.textAlign = "left";
      } else {
        ctx.textAlign = "center";
      }
      const SHORT_LABELS = {
        polarization: "Polar.", inequality: "Ineq.", collective_intelligence: "Coll.Int.",
        contagion_susceptibility: "Contag.", network_resilience: "Resil.",
        phase_transitions: "Tipping", echo_chambers: "Echo Ch.",
        power_law: "Pwr Law", institutional_trust: "Trust",
        cultural_convergence: "Conv.", information_theoretic: "Info",
        norm_emergence: "Norms", segregation: "Segreg.",
      };
      ctx.fillText(SHORT_LABELS[dims[i]] || dims[i], lx, ly + 3);
    }

    // Draw filled radar polygon
    ctx.beginPath();
    for (let i = 0; i < nDims; i++) {
      const angle = (i / nDims) * Math.PI * 2 - Math.PI / 2;
      const val = composites[dims[i]] || 0;
      const r = val * radarR;
      const px = radarCx + Math.cos(angle) * r;
      const py = radarCy + Math.sin(angle) * r;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fillStyle = INDIGO;
    ctx.globalAlpha = 0.12;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.strokeStyle = INDIGO;
    ctx.lineWidth = 1.2;
    ctx.stroke();

    // Data points on radar
    for (let i = 0; i < nDims; i++) {
      const angle = (i / nDims) * Math.PI * 2 - Math.PI / 2;
      const val = composites[dims[i]] || 0;
      const r = val * radarR;
      const px = radarCx + Math.cos(angle) * r;
      const py = radarCy + Math.sin(angle) * r;
      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fillStyle = EMERGENCE_COLORS[dims[i]] || INK;
      ctx.fill();
      // Value label
      ctx.fillStyle = INK;
      ctx.font = "bold 6px Georgia, serif";
      ctx.textAlign = "center";
      ctx.fillText((val * 100).toFixed(0), px, py - 6);
    }

    // Draw history overlay (previous snapshots as faded polygons)
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
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.strokeStyle = INK_FAINT;
        ctx.lineWidth = 0.4;
        ctx.globalAlpha = 0.15 + si * 0.05;
        ctx.stroke();
        ctx.globalAlpha = 1;
      });
    }

    // ── Detail panels: 7 left, 6 right ─────────────────────────────
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

      // Light fill
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.04;
      ctx.fillRect(px, py, panelW, panelH);
      ctx.globalAlpha = 1;

      // Dimension name
      ctx.fillStyle = color;
      ctx.font = "bold 7px Georgia, serif";
      ctx.textAlign = "left";
      ctx.fillText(EMERGENCE_LABELS[dim] || dim, px + 4, py + 10);

      // Composite bar
      const barX = px + 4;
      const barY = py + 15;
      const barW = panelW - 8;
      const barH = 5;
      ctx.fillStyle = INK_FAINT;
      ctx.globalAlpha = 0.15;
      ctx.fillRect(barX, barY, barW, barH);
      ctx.globalAlpha = 1;
      ctx.fillStyle = color;
      ctx.fillRect(barX, barY, barW * val, barH);

      // Value text
      ctx.fillStyle = INK;
      ctx.font = "bold 7px Georgia, serif";
      ctx.textAlign = "right";
      ctx.fillText((val * 100).toFixed(0) + "%", px + panelW - 4, py + 10);

      // Trend arrow
      if (Math.abs(trend) > 0.001) {
        const arrowX = px + panelW - 20;
        const arrowY = py + 10;
        ctx.fillStyle = trend > 0 ? VERDIGRIS : OXIDE;
        ctx.font = "8px Georgia, serif";
        ctx.textAlign = "center";
        ctx.fillText(trend > 0 ? "\u2191" : "\u2193", arrowX, arrowY);
      }

      // Sub-metrics (pick 2-3 key ones)
      ctx.font = "5.5px Georgia, serif";
      ctx.fillStyle = INK_LIGHT;
      ctx.textAlign = "left";
      let subY = py + 26;
      const subKeys = Object.keys(dimData).filter(k => k !== "composite" && typeof dimData[k] === "number");
      const showKeys = subKeys.slice(0, 3);
      for (const key of showKeys) {
        const label = key.replace(/_/g, " ");
        const v = dimData[key];
        ctx.fillText(`${label}: ${typeof v === "number" ? v.toFixed(3) : v}`, px + 4, subY);
        subY += 7;
      }

      // Research citation (tiny)
      if (dimMeta.research) {
        ctx.font = "italic 4.5px Georgia, serif";
        ctx.fillStyle = INK_FAINT;
        ctx.fillText(dimMeta.research, px + 4, py + panelH - 3);
      }

      // Early warning indicator
      const warning = earlyWarnings[dim];
      if (warning && warning.warning_level > 0) {
        const wColors = ["", OCHRE, OXIDE, "#dc2626"];
        const wLabels = ["", "WATCH", "WARNING", "CRITICAL"];
        const wLevel = warning.warning_level;
        ctx.fillStyle = wColors[wLevel];
        ctx.font = "bold 5px Georgia, serif";
        ctx.textAlign = "right";
        ctx.fillText(wLabels[wLevel], px + panelW - 4, py + panelH - 3);
        // Warning dot
        ctx.beginPath();
        ctx.arc(px + panelW - 4 - ctx.measureText(wLabels[wLevel]).width - 4,
                py + panelH - 5, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.textAlign = "left";
      }

      // Coupling indicator: show raw vs coupled delta
      const rawVal = rawComposites[dim] || 0;
      const couplingDelta = val - rawVal;
      if (Math.abs(couplingDelta) > 0.01) {
        ctx.font = "5px Georgia, serif";
        ctx.fillStyle = couplingDelta > 0 ? VERDIGRIS : OXIDE;
        ctx.textAlign = "left";
        ctx.fillText(`coupling ${couplingDelta > 0 ? "+" : ""}${(couplingDelta * 100).toFixed(0)}%`,
                     px + 4, py + panelH - 10);
      }
    }

    // ── Coupling web: small network of feedback loops ──────────────
    if (Object.keys(couplingMatrix).length > 0) {
      const cwCx = radarCx;
      const cwCy = margin.top + ih * 0.68;
      const cwR = Math.min(iw * 0.12, ih * 0.08);

      ctx.fillStyle = SEPIA;
      ctx.font = "italic 7px Georgia, serif";
      ctx.textAlign = "center";
      ctx.fillText("Coupling Web", cwCx, cwCy - cwR - 6);

      // Place dimensions in a circle
      const cwPositions = {};
      for (let i = 0; i < nDims; i++) {
        const a = (i / nDims) * Math.PI * 2 - Math.PI / 2;
        cwPositions[dims[i]] = {
          x: cwCx + Math.cos(a) * cwR,
          y: cwCy + Math.sin(a) * cwR,
        };
      }

      // Draw coupling edges
      for (const [source, targets] of Object.entries(couplingMatrix)) {
        const sp = cwPositions[source];
        if (!sp) continue;
        for (const [target, strength] of Object.entries(targets)) {
          const tp = cwPositions[target];
          if (!tp) continue;
          ctx.beginPath();
          ctx.moveTo(sp.x, sp.y);
          ctx.lineTo(tp.x, tp.y);
          ctx.strokeStyle = strength > 0 ? VERDIGRIS : OXIDE;
          ctx.lineWidth = Math.abs(strength) * 6;
          ctx.globalAlpha = 0.25;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }

      // Draw dimension nodes
      for (let i = 0; i < nDims; i++) {
        const pos = cwPositions[dims[i]];
        const val = composites[dims[i]] || 0;
        const r = 2 + val * 3;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
        ctx.fillStyle = EMERGENCE_COLORS[dims[i]] || INK;
        ctx.fill();
      }
    }

    // ── Bottom: sparkline history for all dimensions ──────────────────
    if (history.length > 1) {
      const sparkY = margin.top + ih * 0.78;
      const sparkH = ih * 0.14;
      const sparkW = iw - 20;
      const sparkX = margin.left + 10;

      // Section header
      ctx.strokeStyle = INK_FAINT;
      ctx.lineWidth = 0.25;
      ctx.beginPath();
      ctx.moveTo(sparkX, sparkY - 10);
      ctx.lineTo(sparkX + sparkW, sparkY - 10);
      ctx.stroke();
      ctx.fillStyle = SEPIA;
      ctx.font = "italic 8px Georgia, serif";
      ctx.textAlign = "left";
      ctx.fillText("Temporal Evolution", sparkX, sparkY - 2);

      // Year labels
      ctx.font = "5px Georgia, serif";
      ctx.fillStyle = INK_FAINT;
      ctx.textAlign = "center";
      const maxPoints = history.length;
      for (let p = 0; p < maxPoints; p += Math.max(1, Math.floor(maxPoints / 8))) {
        const x = sparkX + (p / (maxPoints - 1)) * sparkW;
        ctx.fillText("Y" + (history[p].year || p), x, sparkY + sparkH + 10);
      }

      // Grid lines
      ctx.strokeStyle = INK_FAINT;
      ctx.lineWidth = 0.12;
      for (let g = 0; g <= 4; g++) {
        const gy = sparkY + (g / 4) * sparkH;
        ctx.beginPath();
        ctx.moveTo(sparkX, gy);
        ctx.lineTo(sparkX + sparkW, gy);
        ctx.stroke();
      }

      // Sparklines per dimension
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
          if (p === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
        ctx.globalAlpha = 1;

        // End label
        const lastVal = (history[maxPoints - 1].composites || {})[dim] || 0;
        const lastX = sparkX + sparkW;
        const lastY = sparkY + sparkH - lastVal * sparkH;
        ctx.fillStyle = color;
        ctx.font = "5px Georgia, serif";
        ctx.textAlign = "left";
        ctx.fillText(EMERGENCE_LABELS[dim], lastX + 3, lastY + 2);
      }
    }

    // ── Bottom legend ────────────────────────────────────────────────
    const ly = h - 42;
    ctx.strokeStyle = INK_FAINT;
    ctx.lineWidth = 0.3;
    ctx.beginPath();
    ctx.moveTo(24, ly - 6);
    ctx.lineTo(w - 24, ly - 6);
    ctx.stroke();

    ctx.fillStyle = SEPIA;
    ctx.font = "italic 8px Georgia, serif";
    ctx.textAlign = "left";
    ctx.fillText("Reading the observatory:", 30, ly + 4);
    ctx.font = "7px Georgia, serif";
    ctx.fillStyle = INK_LIGHT;
    ctx.fillText(
      "Central radar: 13 emergent dimensions with inter-dimension coupling (0-100%). " +
      "Faded polygons = previous states. Side panels: sub-metrics, research citations, early warnings.",
      30, ly + 14
    );
    ctx.fillText(
      "Coupling effects shown as % delta from raw scores. Warning indicators (WATCH/WARNING/CRITICAL) " +
      "from Scheffer critical slowing down detection. Sparklines track temporal evolution.",
      30, ly + 24
    );

    setMeta(
      "Thirteen emergent properties with bidirectional coupling, downward causation, " +
      "adaptive rewiring, norm emergence, and Schelling segregation. " +
      "Radar shows coupled composites. Early warnings detect approaching tipping points (Scheffer 2009). " +
      "Advance ticks to see emergence dynamics unfold."
    );
  }

  // ── Meta / Export ─────────────────────────────────────────────────────

  function setMeta(text) {
    document.getElementById("artifact-meta").textContent = text;
  }

  function exportPNG() {
    const canvas = document.getElementById("artifact-canvas");
    const link = document.createElement("a");
    link.download = `civgraph-artifact-${Date.now()}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  function exportPDF() {
    const canvas = document.getElementById("artifact-canvas");
    const { jsPDF } = window.jspdf;
    const aspect = canvas.width / canvas.height;
    const orientation = aspect > 1 ? "landscape" : "portrait";
    const pdf = new jsPDF({
      orientation,
      unit: "px",
      format: [canvas.width, canvas.height],
      hotfixes: ["px_scaling"],
    });
    pdf.addImage(canvas.toDataURL("image/png", 1.0), "PNG", 0, 0, canvas.width, canvas.height);
    pdf.save(`civgraph-artifact-${Date.now()}.pdf`);
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
