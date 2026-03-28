# CivGraph -- Project Instructions

## Screenshot & README Workflow

After any changes to Python model files, `static/` frontend files, or artifacts, update the documentation:

1. Start server: `python run.py &` (wait 4s for startup)
2. Run `python screenshot.py` (or `python screenshot.py --port 8421` if port is busy)
   - Captures all views: main graph, 9 color modes, agent detail, events, ticks, 5 artifacts, microscope
   - Use `--no-tick` to skip event/tick steps (just capture current state)
   - Use `--artifacts-only` to only recapture the 7 artifact plates (faster)
3. Verify key screenshots visually (Read the PNG files)
4. Stop server
5. Update `README.md` to reflect all current systems, screenshots, and API endpoints
6. Commit screenshots + README together with code changes

The `screenshot.py` is a permanent part of the repo -- don't delete it. Extend it when adding new views or artifacts.

## Architecture Overview

- `model.py` -- Agent dataclass, city generator (1,000 agents, 9 edge types)
- `capital.py` -- Bourdieu's four capitals, habitus, lifecycle, intergenerational transmission
- `economy.py` -- Task-based economic model, 4 tech waves, Autor framework
- `media.py` -- Print/mass/social media ecosystems, echo chambers, algorithmic bubbles
- `health.py` -- Social determinants of health, chronic conditions, mental health
- `institutions.py` -- Boards, associations, clubs, skill currency, interlocking directorates
- `agency.py` -- STS agency dynamics: Latour, Callon, Law, Castells, Burt
- `transactions.py` -- Atomic transaction ledger for Microscope view
- `emergence.py` -- 13 emergent dimensions, coupling, downward causation, adaptive rewiring
- `environment.py` -- 26 indicators across 7 domains, bidirectional agent coupling
- `events.py` -- Event propagation with media amplification
- `server.py` -- FastAPI REST + WebSocket, 40+ endpoints
- `static/` -- D3.js frontend, 15 color modes, 7 pen-plotter artifacts, Microscope
- `screenshot.py` -- Playwright screenshot capture tool (permanent, extend when adding views)

## Key Design Principles

- Artifacts must be pen-plotter compatible: strokes, stipple, crosshatch only. No gradients, no solid fills, no alpha blending.
- Western European calibration (FR/DE/NL averages)
- README has marketing value -- keep it polished with current screenshots
- Non-human actants (technologies, media, institutions) have computed agency (Latour)
