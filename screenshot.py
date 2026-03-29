"""
CivGraph -- Screenshot capture tool.

Captures all key views of the application using Playwright for
README documentation.  Every artifact is fully populated: events
are fired through the UI (populating the browser's eventHistory),
ticks are advanced via the step button, and data accumulates in
staggered waves so all panels have rich content.

Usage:
    python screenshot.py                    # default port 8420
    python screenshot.py --port 8421        # custom port
    python screenshot.py --no-tick          # skip event/tick steps
    python screenshot.py --artifacts-only   # only capture artifact plates

Requires: pip install playwright && playwright install chromium
"""

import asyncio
import argparse
from playwright.async_api import async_playwright, Page

DOCS = "docs"
VP_MAIN = {"width": 1920, "height": 1080}
VP_MICRO = {"width": 1200, "height": 700}

# All color modes to capture
COLOR_MODES = [
    ("clan", "01-main-graph"),
    ("class", "02-class-view"),
    ("emergence", "12-emergence-color"),
    ("income", "15-income-color"),
    ("displacement", "16-displacement-color"),
    ("media", "17-media-color"),
    ("health", "19-health-color"),
    ("institutions", "20-institutions-color"),
    ("agency", "21-agency-color"),
]

# Artifacts to capture
ARTIFACTS = [
    ("anatomies", "08-anatomies"),
    ("topography", "09-topography"),
    ("heatmap", "heatmap"),
    ("seismograph", "seismograph"),
    ("constellation", "10-constellation"),
    ("citypulse", "11-citypulse"),
    ("emergence", "13-emergence"),
]

# ── Event waves: diverse events to fire at different simulation stages ───────
# Each wave is fired after a tick phase.  We spread event types, topics,
# sentiments, intensities, and political biases so every artifact panel
# has rich, varied data to render.

EVENT_WAVES = [
    # Wave 1 — early shocks (fired at ~year 5)
    [
        {"type": "tech_boom",       "topic": "tech",        "title": "AI Revolution Hits City",        "sentiment": 0.7,  "intensity": 0.8, "bias": 0.5},
        {"type": "housing_crisis",  "topic": "real_estate",  "title": "Rent Crisis Deepens",            "sentiment": -0.6, "intensity": 0.7, "bias": -1.0},
        {"type": "protest",         "topic": "environment",  "title": "Climate March Fills Streets",     "sentiment": 0.4,  "intensity": 0.6, "bias": -2.0},
    ],
    # Wave 2 — political upheaval (fired at ~year 15)
    [
        {"type": "scandal",         "topic": "governance",   "title": "Board Corruption Exposed",       "sentiment": -0.8, "intensity": 0.9, "bias": 0.0},
        {"type": "election",        "topic": "governance",   "title": "City Election 2032",             "sentiment": 0.3,  "intensity": 0.7, "bias": 1.0},
        {"type": "policy_change",   "topic": "law",          "title": "New Zoning Laws Passed",         "sentiment": -0.3, "intensity": 0.6, "bias": -0.5},
        {"type": "welfare_reform",  "topic": "finance",      "title": "Safety Net Overhaul",            "sentiment": -0.4, "intensity": 0.7, "bias": -1.5},
    ],
    # Wave 3 — cultural & economic (fired at ~year 25)
    [
        {"type": "cultural_event",  "topic": "arts",         "title": "New Arts Quarter Opens",         "sentiment": 0.6,  "intensity": 0.5, "bias": 0.0},
        {"type": "festival",        "topic": "hospitality",  "title": "International Food Festival",    "sentiment": 0.8,  "intensity": 0.4, "bias": 0.0},
        {"type": "crisis",          "topic": "finance",      "title": "Economic Downturn Bites",        "sentiment": -0.5, "intensity": 0.6, "bias": 0.5},
    ],
    # Wave 4 — late-game disruption (fired at ~year 35)
    [
        {"type": "education_reform","topic": "education",    "title": "University Reform Act",          "sentiment": 0.5,  "intensity": 0.6, "bias": -1.0},
        {"type": "development",     "topic": "real_estate",  "title": "Waterfront Mega-Project",        "sentiment": 0.2,  "intensity": 0.8, "bias": 1.5},
        {"type": "tech_boom",       "topic": "manufacturing","title": "Robotics Factory Announced",     "sentiment": 0.6,  "intensity": 0.7, "bias": 0.0},
    ],
]

# Tick schedule: years to advance before each event wave and at the end.
# len(TICK_SCHEDULE) == len(EVENT_WAVES) + 1
TICK_PHASES = [5, 10, 10, 10, 5]   # total 40 years


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _set_slider(page: Page, selector: str, value: float):
    """Set an <input type=range> value and dispatch its input event."""
    await page.evaluate(f"""(() => {{
        const el = document.querySelector('{selector}');
        if (!el) return;
        el.value = {value};
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }})()""")


async def _advance_ticks(page: Page, years: int, step_size: int = 5):
    """Advance simulation via the UI step button, step_size years at a time."""
    remaining = years
    while remaining > 0:
        chunk = min(step_size, remaining)
        await page.select_option("#tick-years", str(chunk))
        await page.click("#btn-step")
        await asyncio.sleep(6)  # wait for tick + render
        remaining -= chunk
    print(f"    ticked {years}y")


async def _fire_events_ui(page: Page, events: list[dict]):
    """Fire a batch of events through the UI form.

    Selects different nodes as origins to spread events across the graph.
    Each event populates the browser's eventHistory (needed for seismograph)
    and triggers opinion updates (needed for heatmap).
    """
    circles = await page.query_selector_all(".node circle")
    n_circles = len(circles)
    if n_circles == 0:
        print("    WARNING: no circles found, skipping events")
        return

    for i, evt in enumerate(events):
        # Pick a spread-out node as origin; force=True bypasses bottom-panel overlap
        idx = int((i + 1) * n_circles / (len(events) + 1)) % n_circles
        await circles[idx].click(force=True)
        await asyncio.sleep(0.5)

        # Fill the event form
        await page.select_option("#event-type", evt["type"])
        # Topic select may not have all values; try/except
        try:
            await page.select_option("#event-topic", evt["topic"])
        except Exception:
            pass  # keep whatever topic is selected
        await page.fill("#event-title", evt["title"])
        await _set_slider(page, "#event-sentiment", evt.get("sentiment", 0.5))
        await _set_slider(page, "#event-intensity", evt.get("intensity", 0.7))
        await _set_slider(page, "#event-bias", evt.get("bias", 0.0))
        await page.click("#btn-fire-event")
        await asyncio.sleep(4)  # wait for propagation animation
        print(f"    fired: {evt['title']}")


async def _warmup_simulation(page: Page):
    """Run the full warmup: interleaved ticks and event waves.

    After warmup every artifact has rich data:
      - Seismograph: 13 events in eventHistory
      - Heatmap: opinions shaped by events
      - City Pulse: 40 years of environment history
      - Emergence: 40 years of emergence snapshots
      - Anatomies/Topography/Constellation: evolved agents
    """
    for phase_idx in range(len(EVENT_WAVES)):
        tick_years = TICK_PHASES[phase_idx]
        print(f"  Phase {phase_idx + 1}: tick {tick_years}y, then fire events...")
        await _advance_ticks(page, tick_years)
        await _fire_events_ui(page, EVENT_WAVES[phase_idx])

    # Final tick phase (no events after)
    final_years = TICK_PHASES[-1]
    print(f"  Final phase: tick {final_years}y...")
    await _advance_ticks(page, final_years)


# ── Capture routines ─────────────────────────────────────────────────────────

async def capture_all(port: int = 8420, do_tick: bool = True):
    url = f"http://127.0.0.1:{port}"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport=VP_MAIN)

        print(f"Loading {url}...")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_selector("#graph-svg", timeout=60000)
        await asyncio.sleep(8)

        # ── Simulation warmup ──────────────────────────────────────
        if do_tick:
            print("Warming up simulation...")
            await _warmup_simulation(page)
            await asyncio.sleep(2)

        # ── Initial state ──────────────────────────────────────────
        await page.click('button[data-mode="clan"]')
        await asyncio.sleep(1)
        print("01 - Main graph...")
        await page.screenshot(path=f"{DOCS}/01-main-graph.png")

        # ── Agent detail ───────────────────────────────────────────
        circles = await page.query_selector_all(".node circle")
        if len(circles) > 5:
            await circles[5].click(force=True)
            await asyncio.sleep(2)
            print("03 - Agent detail...")
            await page.screenshot(path=f"{DOCS}/03-agent-detail.png")

        if do_tick:
            # ── Fire one more event via UI for propagation screenshot ─
            if len(circles) > 20:
                await circles[20].click(force=True)
                await asyncio.sleep(0.5)
            await page.fill("#event-title", "Education Reform Protest")
            await page.select_option("#event-type", "education_reform")
            try:
                await page.select_option("#event-topic", "education")
            except Exception:
                pass
            await page.click("#btn-fire-event")
            await asyncio.sleep(6)
            print("04 - Event propagation...")
            await page.screenshot(path=f"{DOCS}/04-event-propagation.png")
            await asyncio.sleep(2)
            print("05 - Post event...")
            await page.screenshot(path=f"{DOCS}/05-post-event.png")

            # ── Bridge agents ──────────────────────────────────────
            print("06 - Bridge agents...")
            await page.click("#btn-bridges")
            await asyncio.sleep(3)
            await page.screenshot(path=f"{DOCS}/06-bridge-agents.png")

            # ── Advance 5 more years ──────────────────────────────
            print("07 - Environment tick (5y)...")
            await _advance_ticks(page, 5)
            await page.click('button[data-mode="capital"]')
            await asyncio.sleep(1)
            await page.screenshot(path=f"{DOCS}/07-environment-tick.png")

        # ── Color modes ────────────────────────────────────────────
        for mode, filename in COLOR_MODES:
            print(f"{filename}...")
            await page.click(f'button[data-mode="{mode}"]')
            await asyncio.sleep(1)
            await page.screenshot(path=f"{DOCS}/{filename}.png")

        # ── Agent detail after ticks ───────────────────────────────
        await page.click('button[data-mode="clan"]')
        await asyncio.sleep(0.5)
        circles = await page.query_selector_all(".node circle")
        if len(circles) > 10:
            await circles[10].click(force=True)
            await asyncio.sleep(2)
            print("14 - Agent detail post-ticks...")
            await page.screenshot(path=f"{DOCS}/14-agent-emergence-detail.png")

        if do_tick:
            # ── 10 more years ──────────────────────────────────────
            print("18 - After 10 more years...")
            await _advance_ticks(page, 10)
            await page.click('button[data-mode="displacement"]')
            await asyncio.sleep(1)
            await page.screenshot(path=f"{DOCS}/18-disruption-10yr.png")

        # ── Artifacts ──────────────────────────────────────────────
        for artifact, filename in ARTIFACTS:
            print(f"{filename}...")
            await page.click(f'[data-artifact="{artifact}"]')
            await asyncio.sleep(4)
            await page.screenshot(path=f"{DOCS}/{filename}.png")
            await page.click("#btn-close-artifact")
            await asyncio.sleep(0.5)

        # ── Microscope ─────────────────────────────────────────────
        if do_tick:
            print("22 - Microscope...")
            micro = await browser.new_page(viewport=VP_MICRO)
            await micro.goto(f"{url}/static/microscope.html", wait_until="networkidle")
            await asyncio.sleep(2)
            await micro.click("#btn-refresh")
            await asyncio.sleep(2)
            await micro.screenshot(path=f"{DOCS}/22-microscope.png")

        await browser.close()
        print(f"\nAll screenshots saved to {DOCS}/")


async def capture_artifacts_only(port: int = 8420):
    """Capture only artifact screenshots with full data warmup."""
    url = f"http://127.0.0.1:{port}"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport=VP_MAIN)

        print(f"Loading {url}...")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_selector("#graph-svg", timeout=60000)
        await asyncio.sleep(8)

        print("Warming up simulation for artifacts...")
        await _warmup_simulation(page)
        await asyncio.sleep(2)

        for artifact, filename in ARTIFACTS:
            print(f"{filename}...")
            await page.click(f'[data-artifact="{artifact}"]')
            await asyncio.sleep(4)
            await page.screenshot(path=f"{DOCS}/{filename}.png")
            await page.click("#btn-close-artifact")
            await asyncio.sleep(0.5)

        await browser.close()
        print(f"\nArtifact screenshots saved to {DOCS}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture CivGraph screenshots")
    parser.add_argument("--port", type=int, default=8420, help="Server port")
    parser.add_argument("--no-tick", action="store_true", help="Skip event/tick steps")
    parser.add_argument("--artifacts-only", action="store_true",
                        help="Only capture artifact plates (with warmup)")
    args = parser.parse_args()
    if args.artifacts_only:
        asyncio.run(capture_artifacts_only(port=args.port))
    else:
        asyncio.run(capture_all(port=args.port, do_tick=not args.no_tick))
