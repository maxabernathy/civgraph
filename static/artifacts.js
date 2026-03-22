/**
 * CivGraph — Artifact Renderers
 *
 * Four unorthodox visualizations rendered to high-resolution canvas,
 * exportable as PNG or PDF.
 *
 * 1. Influence Topography  — contour elevation map of influence density
 * 2. Clan Constellations   — astronomical star chart of social structure
 * 3. Opinion Heatmap       — woven textile pattern of clan×topic opinions
 * 4. Event Seismograph     — layered waveforms of event impact over time
 */

const Artifacts = (() => {
  const BG = "#0a0a0f";
  const SURFACE = "#12121a";
  const ACCENT = "#4a9eff";
  const DIM = "#6b6b7b";
  const TEXT = "#c8c8d4";

  // ── Shared helpers ──────────────────────────────────────────────────────

  function getCanvasCtx(scale = 2) {
    const canvas = document.getElementById("artifact-canvas");
    // Size to fill the viewport at the given DPI scale
    const wrap = document.getElementById("artifact-canvas-wrap");
    const baseW = Math.min(wrap.clientWidth - 48, 1400);
    const baseH = Math.min(wrap.clientHeight - 48, 900);
    canvas.width = baseW * scale;
    canvas.height = baseH * scale;
    canvas.style.width = baseW + "px";
    canvas.style.height = baseH + "px";
    const ctx = canvas.getContext("2d");
    ctx.scale(scale, scale);
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, baseW, baseH);
    return { ctx, w: baseW, h: baseH, canvas, scale };
  }

  function drawTitle(ctx, w, title, subtitle) {
    ctx.fillStyle = ACCENT;
    ctx.font = "bold 14px 'SF Mono', 'Fira Code', monospace";
    ctx.textAlign = "left";
    ctx.fillText(title.toUpperCase(), 32, 36);
    ctx.fillStyle = DIM;
    ctx.font = "10px 'SF Mono', 'Fira Code', monospace";
    ctx.fillText(subtitle, 32, 52);

    ctx.fillStyle = DIM;
    ctx.font = "9px 'SF Mono', 'Fira Code', monospace";
    ctx.textAlign = "right";
    ctx.fillText("CIVGRAPH", w - 32, 36);
    ctx.fillText(new Date().toISOString().slice(0, 10), w - 32, 50);
    ctx.textAlign = "left";
  }

  // ── 1. Influence Topography ─────────────────────────────────────────────
  // Treats the force-layout positions as terrain. Agent influence becomes
  // elevation. Renders contour lines like a topographic map, with color
  // bands for altitude (influence density).

  function renderTopography(nodes, links) {
    const { ctx, w, h } = getCanvasCtx(parseInt(document.getElementById("res-select").value));
    drawTitle(ctx, w, "Influence Topography", `${nodes.length} agents · elevation = local influence density`);

    const margin = { top: 70, right: 32, bottom: 60, left: 32 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

    // Use force-layout positions, normalize to canvas
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

    // Build elevation field via kernel density estimation
    const gridRes = 120;
    const field = new Float64Array(gridRes * gridRes);
    const cellW = iw / gridRes;
    const cellH = ih / gridRes;
    const bandwidth = Math.max(iw, ih) * 0.08;

    for (const node of nodes) {
      const { cx, cy } = toCanvas(node);
      const inf = node.influence;
      const deg = node.degree || 1;
      const weight = inf * 2 + Math.sqrt(deg) * 0.3;

      // Gaussian splat
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
          const dist2 = dx * dx + dy * dy;
          const val = weight * Math.exp(-dist2 / (2 * bandwidth * bandwidth));
          field[jj * gridRes + ii] += val;
        }
      }
    }

    // Normalize field
    let maxVal = 0;
    for (let i = 0; i < field.length; i++) {
      if (field[i] > maxVal) maxVal = field[i];
    }
    if (maxVal > 0) {
      for (let i = 0; i < field.length; i++) field[i] /= maxVal;
    }

    // Color bands — topographic palette
    const topoColors = [
      [10, 20, 40],     // deep ocean
      [15, 45, 80],     // ocean
      [20, 80, 100],    // shallow
      [30, 110, 90],    // coastal
      [60, 140, 70],    // lowland
      [120, 170, 60],   // plains
      [180, 180, 50],   // hills
      [210, 160, 60],   // highlands
      [200, 120, 60],   // mountains
      [220, 100, 80],   // peaks
      [255, 200, 150],  // summit
    ];

    function topoColor(v) {
      const t = v * (topoColors.length - 1);
      const i = Math.min(Math.floor(t), topoColors.length - 2);
      const f = t - i;
      const a = topoColors[i];
      const b = topoColors[i + 1];
      return [
        Math.round(a[0] + (b[0] - a[0]) * f),
        Math.round(a[1] + (b[1] - a[1]) * f),
        Math.round(a[2] + (b[2] - a[2]) * f),
      ];
    }

    // Render elevation field
    for (let j = 0; j < gridRes; j++) {
      for (let i = 0; i < gridRes; i++) {
        const v = field[j * gridRes + i];
        const [r, g, b] = topoColor(v);
        ctx.fillStyle = `rgb(${r},${g},${b})`;
        ctx.fillRect(
          margin.left + i * cellW,
          margin.top + j * cellH,
          cellW + 0.5,
          cellH + 0.5
        );
      }
    }

    // Contour lines
    const contourLevels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9];
    ctx.strokeStyle = "rgba(255,255,255,0.15)";
    ctx.lineWidth = 0.5;

    for (const level of contourLevels) {
      // Marching squares (simplified — horizontal scan)
      for (let j = 0; j < gridRes - 1; j++) {
        for (let i = 0; i < gridRes - 1; i++) {
          const v00 = field[j * gridRes + i];
          const v10 = field[j * gridRes + i + 1];
          const v01 = field[(j + 1) * gridRes + i];
          const v11 = field[(j + 1) * gridRes + i + 1];

          const edges = [];
          // Top edge
          if ((v00 < level) !== (v10 < level)) {
            const t = (level - v00) / (v10 - v00);
            edges.push([margin.left + (i + t) * cellW, margin.top + j * cellH]);
          }
          // Bottom edge
          if ((v01 < level) !== (v11 < level)) {
            const t = (level - v01) / (v11 - v01);
            edges.push([margin.left + (i + t) * cellW, margin.top + (j + 1) * cellH]);
          }
          // Left edge
          if ((v00 < level) !== (v01 < level)) {
            const t = (level - v00) / (v01 - v00);
            edges.push([margin.left + i * cellW, margin.top + (j + t) * cellH]);
          }
          // Right edge
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
    }

    // Plot agents as dots on the terrain
    for (const node of nodes) {
      const { cx, cy } = toCanvas(node);
      const r = 1.2 + node.influence * 3;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${0.3 + node.influence * 0.5})`;
      ctx.fill();
    }

    // Label top influencers
    const top = [...nodes].sort((a, b) => b.influence - a.influence).slice(0, 12);
    ctx.font = "8px 'SF Mono', monospace";
    ctx.fillStyle = "rgba(255,255,255,0.7)";
    for (const node of top) {
      const { cx, cy } = toCanvas(node);
      ctx.fillText(node.name.split(" ")[1], cx + 5, cy - 4);
    }

    // Elevation legend
    const legendX = w - 60;
    const legendY = margin.top + 10;
    const legendH = ih * 0.4;
    for (let i = 0; i < legendH; i++) {
      const v = 1 - i / legendH;
      const [r, g, b] = topoColor(v);
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(legendX, legendY + i, 16, 1.5);
    }
    ctx.fillStyle = DIM;
    ctx.font = "8px 'SF Mono', monospace";
    ctx.fillText("HIGH", legendX, legendY - 4);
    ctx.fillText("LOW", legendX, legendY + legendH + 10);

    setMeta("Elevation = influence density kernel (Gaussian, bw=" +
      bandwidth.toFixed(0) + "px). Contour lines at 10% intervals. " +
      "Dots = agents, size = influence.");
  }

  // ── 2. Clan Constellations ──────────────────────────────────────────────
  // Each clan is a "constellation" — agents are stars, with brightness
  // proportional to influence. Lines connect clan members. The layout is
  // a political-axis spiral: x = political leaning, y = influence.

  function renderConstellation(nodes, links) {
    const { ctx, w, h } = getCanvasCtx(parseInt(document.getElementById("res-select").value));

    // Star field background
    for (let i = 0; i < 800; i++) {
      const x = Math.random() * w;
      const y = Math.random() * h;
      const r = Math.random() * 0.8;
      const a = Math.random() * 0.3 + 0.05;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200,200,230,${a})`;
      ctx.fill();
    }

    drawTitle(ctx, w, "Clan Constellations", `${nodes.length} stars · x = politics · y = influence`);

    const margin = { top: 70, right: 40, bottom: 60, left: 40 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

    const polMap = {
      far_left: -3, left: -2, center_left: -1, center: 0,
      center_right: 1, right: 2, far_right: 3,
    };

    // Group by clan
    const clans = {};
    for (const n of nodes) {
      if (!clans[n.clan]) clans[n.clan] = [];
      clans[n.clan].push(n);
    }
    const clanNames = Object.keys(clans);
    const clanColor = d3.scaleOrdinal(d3.schemeTableau10.concat(d3.schemePastel1));

    // Position: x = politics (jittered), y = influence (inverted so high = top)
    function starPos(n, idx, total) {
      const pol = polMap[n.politics] || 0;
      const jitterX = (Math.sin(idx * 137.508) * 0.4);  // golden angle scatter
      const jitterY = (Math.cos(idx * 137.508) * 0.15);
      const x = margin.left + ((pol + jitterX + 3.5) / 7) * iw;
      const y = margin.top + ih - (n.influence + jitterY) * ih * 0.85 - ih * 0.08;
      return { x, y };
    }

    // Draw constellation lines (connect clan members by nearest neighbor)
    for (const clan of clanNames) {
      const members = clans[clan];
      const positions = members.map((n, i) => ({ ...starPos(n, i, members.length), node: n }));
      const color = clanColor(clan);

      // Minimum spanning tree within clan (for clean constellation lines)
      const used = new Set();
      const mstEdges = [];
      if (positions.length > 1) {
        used.add(0);
        while (used.size < positions.length) {
          let bestDist = Infinity;
          let bestFrom = -1;
          let bestTo = -1;
          for (const from of used) {
            for (let to = 0; to < positions.length; to++) {
              if (used.has(to)) continue;
              const dx = positions[from].x - positions[to].x;
              const dy = positions[from].y - positions[to].y;
              const dist = dx * dx + dy * dy;
              if (dist < bestDist) {
                bestDist = dist;
                bestFrom = from;
                bestTo = to;
              }
            }
          }
          if (bestTo >= 0) {
            used.add(bestTo);
            mstEdges.push([bestFrom, bestTo]);
          }
        }
      }

      // Draw constellation lines
      ctx.strokeStyle = color;
      ctx.globalAlpha = 0.15;
      ctx.lineWidth = 0.8;
      for (const [a, b] of mstEdges) {
        ctx.beginPath();
        ctx.moveTo(positions[a].x, positions[a].y);
        ctx.lineTo(positions[b].x, positions[b].y);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // Draw stars
      for (const pos of positions) {
        const inf = pos.node.influence;
        const r = 1 + inf * 5;

        // Glow
        const grad = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, r * 4);
        grad.addColorStop(0, color);
        grad.addColorStop(0.3, color + "40");
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
        ctx.fillRect(pos.x - r * 4, pos.y - r * 4, r * 8, r * 8);

        // Star point
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        // Cross flare for top influencers
        if (inf > 0.5) {
          ctx.strokeStyle = color;
          ctx.globalAlpha = 0.4;
          ctx.lineWidth = 0.5;
          const flare = r * 3;
          ctx.beginPath();
          ctx.moveTo(pos.x - flare, pos.y);
          ctx.lineTo(pos.x + flare, pos.y);
          ctx.moveTo(pos.x, pos.y - flare);
          ctx.lineTo(pos.x, pos.y + flare);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }

      // Clan label at centroid
      const cx = positions.reduce((s, p) => s + p.x, 0) / positions.length;
      const cy = positions.reduce((s, p) => s + p.y, 0) / positions.length;
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.5;
      ctx.font = "bold 8px 'SF Mono', monospace";
      ctx.textAlign = "center";
      ctx.fillText(clan.toUpperCase(), cx, cy - 12);
      ctx.globalAlpha = 1;
      ctx.textAlign = "left";
    }

    // Political axis labels
    ctx.fillStyle = DIM;
    ctx.font = "9px 'SF Mono', monospace";
    ctx.textAlign = "center";
    const polLabels = ["FAR LEFT", "LEFT", "CTR-LEFT", "CENTER", "CTR-RIGHT", "RIGHT", "FAR RIGHT"];
    for (let i = 0; i < 7; i++) {
      const x = margin.left + ((i + 0.5) / 7) * iw;
      ctx.fillText(polLabels[i], x, h - margin.bottom + 20);
    }
    ctx.textAlign = "left";

    // Y-axis
    ctx.save();
    ctx.translate(16, margin.top + ih / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = DIM;
    ctx.font = "9px 'SF Mono', monospace";
    ctx.textAlign = "center";
    ctx.fillText("INFLUENCE", 0, 0);
    ctx.restore();

    setMeta("Each constellation = one clan. Star brightness = influence. " +
      "Horizontal axis = political leaning. Constellation lines = minimum spanning tree within clan.");
  }

  // ── 3. Opinion Heatmap ──────────────────────────────────────────────────
  // A woven-textile-inspired grid: rows = clans, columns = topics.
  // Cell color = average opinion. Cell texture = variance (smooth = consensus,
  // hatched = disagreement).

  function renderHeatmap(nodes, links) {
    const { ctx, w, h } = getCanvasCtx(parseInt(document.getElementById("res-select").value));
    drawTitle(ctx, w, "Opinion Heatmap", "rows = clans · columns = topics · texture = internal disagreement");

    // Gather all topics with opinions
    const topicSet = new Set();
    for (const n of nodes) {
      if (n._opinions) {
        for (const k of Object.keys(n._opinions)) topicSet.add(k);
      }
    }
    const topics = [...topicSet];
    if (topics.length === 0) {
      ctx.fillStyle = DIM;
      ctx.font = "12px 'SF Mono', monospace";
      ctx.fillText("No opinions yet — fire some events first.", 40, 100);
      setMeta("Trigger events to generate opinion data, then view this artifact.");
      return;
    }

    const clans = {};
    for (const n of nodes) {
      if (!clans[n.clan]) clans[n.clan] = [];
      clans[n.clan].push(n);
    }
    const clanNames = Object.keys(clans).sort();

    const margin = { top: 80, right: 40, bottom: 40, left: 120 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;
    const cellW = iw / topics.length;
    const cellH = ih / clanNames.length;

    // Draw cells
    for (let row = 0; row < clanNames.length; row++) {
      const clan = clanNames[row];
      const members = clans[clan];

      for (let col = 0; col < topics.length; col++) {
        const topic = topics[col];
        const opinions = members
          .map((n) => (n._opinions && n._opinions[topic]) || 0)
          .filter((v) => v !== 0);

        const x = margin.left + col * cellW;
        const y = margin.top + row * cellH;

        if (opinions.length === 0) {
          // No data — dark cell
          ctx.fillStyle = "#0d0d15";
          ctx.fillRect(x, y, cellW - 1, cellH - 1);
          continue;
        }

        const avg = opinions.reduce((s, v) => s + v, 0) / opinions.length;
        const variance = opinions.reduce((s, v) => s + (v - avg) ** 2, 0) / opinions.length;

        // Color: green = support, red = oppose, neutral = gray
        let r, g, b;
        if (avg > 0) {
          r = Math.round(20 + (1 - avg) * 60);
          g = Math.round(80 + avg * 140);
          b = Math.round(40 + (1 - avg) * 40);
        } else {
          r = Math.round(80 + Math.abs(avg) * 140);
          g = Math.round(30 + (1 - Math.abs(avg)) * 50);
          b = Math.round(30 + (1 - Math.abs(avg)) * 40);
        }
        const alpha = 0.3 + Math.abs(avg) * 0.7;

        ctx.fillStyle = `rgba(${r},${g},${b},${alpha})`;
        ctx.fillRect(x, y, cellW - 1, cellH - 1);

        // Hatching for high variance (disagreement)
        if (variance > 0.05) {
          ctx.strokeStyle = `rgba(255,255,255,${Math.min(0.3, variance)})`;
          ctx.lineWidth = 0.5;
          const density = Math.min(8, Math.ceil(variance * 20));
          const spacing = Math.max(3, (cellH - 1) / density);
          for (let i = 0; i < density; i++) {
            const ly = y + i * spacing;
            ctx.beginPath();
            ctx.moveTo(x, ly);
            ctx.lineTo(x + cellW - 1, ly + spacing * 0.5);
            ctx.stroke();
          }
        }

        // Value label in cell
        if (cellW > 30 && cellH > 14) {
          ctx.fillStyle = `rgba(255,255,255,${0.3 + Math.abs(avg) * 0.4})`;
          ctx.font = `${Math.min(9, cellH * 0.5)}px 'SF Mono', monospace`;
          ctx.textAlign = "center";
          ctx.fillText(avg.toFixed(2), x + cellW / 2, y + cellH / 2 + 3);
          ctx.textAlign = "left";
        }
      }
    }

    // Row labels (clans)
    ctx.fillStyle = TEXT;
    ctx.font = `${Math.min(10, cellH * 0.6)}px 'SF Mono', monospace`;
    ctx.textAlign = "right";
    for (let i = 0; i < clanNames.length; i++) {
      ctx.fillText(clanNames[i], margin.left - 8, margin.top + i * cellH + cellH / 2 + 3);
    }
    ctx.textAlign = "left";

    // Column labels (topics)
    ctx.fillStyle = TEXT;
    ctx.font = `${Math.min(9, cellW * 0.8)}px 'SF Mono', monospace`;
    for (let i = 0; i < topics.length; i++) {
      ctx.save();
      ctx.translate(margin.left + i * cellW + cellW / 2, margin.top - 8);
      ctx.rotate(-Math.PI / 4);
      ctx.fillText(topics[i], 0, 0);
      ctx.restore();
    }

    setMeta("Green = support, Red = oppose. Brightness = strength. " +
      "Diagonal hatching = internal clan disagreement (high variance). " +
      "Dark cells = no opinion data.");
  }

  // ── 4. Event Seismograph ────────────────────────────────────────────────
  // Each past event is a waveform. Amplitude = how many agents were
  // activated at each propagation step. Vertical stacking like
  // a seismograph strip chart.

  function renderSeismograph(nodes, links, events) {
    const { ctx, w, h } = getCanvasCtx(parseInt(document.getElementById("res-select").value));
    drawTitle(ctx, w, "Event Seismograph", `${events.length} events · amplitude = cascade reach per step`);

    if (events.length === 0) {
      ctx.fillStyle = DIM;
      ctx.font = "12px 'SF Mono', monospace";
      ctx.fillText("No events recorded — fire some events first.", 40, 100);
      setMeta("Trigger events to see their seismograph traces.");
      return;
    }

    const margin = { top: 70, right: 40, bottom: 40, left: 180 };
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;
    const rowH = Math.min(80, ih / events.length);
    const maxSteps = Math.max(...events.map((e) => e.propagation.length));

    // Sentiment color palette
    function sentColor(sentiment) {
      if (sentiment > 0.2) return "#4ade80";
      if (sentiment < -0.2) return "#f87171";
      return "#94a3b8";
    }

    for (let ei = 0; ei < events.length; ei++) {
      const event = events[ei];
      const baseY = margin.top + ei * rowH + rowH / 2;
      const color = sentColor(event.sentiment);

      // Baseline
      ctx.strokeStyle = SURFACE;
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(margin.left, baseY);
      ctx.lineTo(margin.left + iw, baseY);
      ctx.stroke();

      // Waveform: each step becomes a point. We interpolate a smooth wave.
      const points = [];
      const stepW = iw / (maxSteps + 1);

      // Origin pulse
      points.push({ x: margin.left, y: baseY });

      let maxReach = 0;
      for (const s of event.propagation) {
        if (s.results.length > maxReach) maxReach = s.results.length;
      }
      if (maxReach === 0) maxReach = 1;

      for (let si = 0; si < event.propagation.length; si++) {
        const step = event.propagation[si];
        const activated = step.results.filter((r) => r.activated).length;
        const total = step.results.length;
        const amplitude = (total / maxReach) * (rowH * 0.4);
        const x = margin.left + (si + 1) * stepW;

        // Create a wavelet: sharp attack, exponential decay
        const subPoints = 12;
        for (let sp = 0; sp < subPoints; sp++) {
          const t = sp / subPoints;
          const subX = x - stepW + t * stepW;
          const envelope = Math.sin(t * Math.PI) * amplitude;
          // High-frequency oscillation (seismic texture)
          const freq = 3 + si * 0.5;
          const osc = Math.sin(t * Math.PI * freq * 2) * envelope;
          points.push({ x: subX, y: baseY - osc });
        }
      }

      // Tail decay
      const lastX = margin.left + event.propagation.length * stepW;
      for (let t = 0; t < 20; t++) {
        const decay = Math.exp(-t * 0.3);
        const x = lastX + t * (stepW / 5);
        if (x > margin.left + iw) break;
        points.push({ x, y: baseY - Math.sin(t * 1.5) * 3 * decay });
      }
      points.push({ x: margin.left + iw, y: baseY });

      // Draw waveform
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.2;
      ctx.globalAlpha = 0.8;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i].x, points[i].y);
      }
      ctx.stroke();

      // Fill under wave (subtle)
      ctx.globalAlpha = 0.08;
      ctx.fillStyle = color;
      ctx.lineTo(points[points.length - 1].x, baseY);
      ctx.lineTo(points[0].x, baseY);
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = 1;

      // Event label
      ctx.fillStyle = color;
      ctx.font = "bold 9px 'SF Mono', monospace";
      ctx.textAlign = "right";
      ctx.fillText(event.title, margin.left - 10, baseY + 3);

      // Metadata
      ctx.fillStyle = DIM;
      ctx.font = "7px 'SF Mono', monospace";
      ctx.fillText(`${event.total_affected} affected`, margin.left - 10, baseY + 13);
      ctx.textAlign = "left";

      // Origin dot
      ctx.beginPath();
      ctx.arc(margin.left + 4, baseY, 3, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
    }

    // Step markers at bottom
    ctx.fillStyle = DIM;
    ctx.font = "8px 'SF Mono', monospace";
    ctx.textAlign = "center";
    const stepW2 = iw / (maxSteps + 1);
    for (let i = 0; i <= maxSteps; i++) {
      const x = margin.left + i * stepW2;
      ctx.fillText(`step ${i}`, x, h - margin.bottom + 16);
    }
    ctx.textAlign = "left";

    setMeta("Each row = one event. Waveform amplitude = number of agents reached at each propagation step. " +
      "Green = positive sentiment, red = negative, gray = neutral. " +
      "Oscillation frequency increases with propagation depth.");
  }

  // ── Meta helper ─────────────────────────────────────────────────────────

  function setMeta(text) {
    const el = document.getElementById("artifact-meta");
    el.textContent = text;
  }

  // ── Export ──────────────────────────────────────────────────────────────

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

    // Determine orientation from canvas aspect ratio
    const aspect = canvas.width / canvas.height;
    const orientation = aspect > 1 ? "landscape" : "portrait";
    const pdf = new jsPDF({
      orientation,
      unit: "px",
      format: [canvas.width, canvas.height],
      hotfixes: ["px_scaling"],
    });

    const imgData = canvas.toDataURL("image/png", 1.0);
    pdf.addImage(imgData, "PNG", 0, 0, canvas.width, canvas.height);
    pdf.save(`civgraph-artifact-${Date.now()}.pdf`);
  }

  // ── Public API ──────────────────────────────────────────────────────────

  return {
    renderTopography,
    renderConstellation,
    renderHeatmap,
    renderSeismograph,
    exportPNG,
    exportPDF,
  };
})();
