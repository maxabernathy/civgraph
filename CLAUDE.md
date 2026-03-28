# CivGraph — Project Instructions

## Screenshot & README Workflow

After any changes to Python model files, `static/` frontend files, or artifacts, update the documentation:

1. Start server: `python run.py &` (wait 4s for startup)
2. Write a temporary `screenshot.py` using Playwright (`async_playwright`, chromium, 1920x1080)
3. Capture: main graph, all color modes, agent detail, events, tick results, all 7 artifacts
4. Run `python screenshot.py`, verify key screenshots visually
5. Clean up: `rm screenshot.py`, stop server
6. Update `README.md` to reflect all current systems, screenshots, and API endpoints
7. Commit screenshots + README together with code changes

This is a standard part of the development workflow — do it proactively when pushing changes.

## Architecture Overview

- `model.py` — Agent dataclass, city generator (1,000 agents, 9 edge types)
- `capital.py` — Bourdieu's four capitals, habitus, lifecycle, intergenerational transmission
- `economy.py` — Task-based economic model, 4 tech waves, Autor framework
- `media.py` — Print/mass/social media ecosystems, echo chambers, algorithmic bubbles
- `health.py` — Social determinants of health, chronic conditions, mental health
- `institutions.py` — Boards, associations, clubs, skill currency, interlocking directorates
- `emergence.py` — 13 emergent dimensions, coupling, downward causation, adaptive rewiring
- `environment.py` — 26 indicators across 7 domains, bidirectional agent coupling
- `events.py` — Event propagation with media amplification
- `server.py` — FastAPI REST + WebSocket, 35+ endpoints
- `static/` — D3.js frontend, 14 color modes, 7 pen-plotter artifacts

## Key Design Principles

- Artifacts must be pen-plotter compatible: strokes, stipple, crosshatch only. No gradients, no solid fills, no alpha blending.
- Western European calibration (FR/DE/NL averages)
- README has marketing value — keep it polished with current screenshots
