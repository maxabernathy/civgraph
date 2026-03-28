"""
CivGraph -- Screenshot capture tool.

Captures all key views of the application using Playwright for
README documentation. Run after any significant code changes.

Usage:
    python screenshot.py              # default port 8420
    python screenshot.py --port 8421  # custom port
    python screenshot.py --no-tick    # skip event/tick (just capture current state)

Requires: pip install playwright && playwright install chromium
"""

import asyncio
import argparse
from playwright.async_api import async_playwright

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
    ("constellation", "10-constellation"),
    ("citypulse", "11-citypulse"),
    ("emergence", "13-emergence"),
]


async def capture_all(port: int = 8420, do_tick: bool = True):
    url = f"http://127.0.0.1:{port}"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport=VP_MAIN)

        print(f"Loading {url}...")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_selector("#graph-svg", timeout=30000)
        await asyncio.sleep(8)

        # ── Initial state ──────────────────────────────────────────
        print("01 - Main graph...")
        await page.screenshot(path=f"{DOCS}/01-main-graph.png")

        # ── Agent detail ───────────────────────────────────────────
        circles = await page.query_selector_all(".node circle")
        if len(circles) > 5:
            await circles[5].click()
            await asyncio.sleep(2)
            print("03 - Agent detail...")
            await page.screenshot(path=f"{DOCS}/03-agent-detail.png")

        if do_tick:
            # ── Fire event ─────────────────────────────────────────
            await page.fill("#event-title", "AI Revolution Hits City")
            await page.select_option("#event-type", "tech_boom")
            await page.select_option("#event-topic", "tech")
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

            # ── Advance 5 years ────────────────────────────────────
            print("07 - Environment tick (5y)...")
            await page.select_option("#tick-years", "5")
            await page.click("#btn-tick")
            await asyncio.sleep(6)
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
        if len(circles) > 10:
            await circles[10].click()
            await asyncio.sleep(2)
            print("14 - Agent detail post-ticks...")
            await page.screenshot(path=f"{DOCS}/14-agent-emergence-detail.png")

        if do_tick:
            # ── 10 more years ──────────────────────────────────────
            print("18 - After 10 more years...")
            await page.select_option("#tick-years", "10")
            await page.click("#btn-tick")
            await asyncio.sleep(8)
            await page.click('button[data-mode="displacement"]')
            await asyncio.sleep(1)
            await page.screenshot(path=f"{DOCS}/18-disruption-10yr.png")

        # ── Artifacts ──────────────────────────────────────────────
        for artifact, filename in ARTIFACTS:
            print(f"{filename}...")
            await page.click(f'[data-artifact="{artifact}"]')
            await asyncio.sleep(3)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture CivGraph screenshots")
    parser.add_argument("--port", type=int, default=8420, help="Server port")
    parser.add_argument("--no-tick", action="store_true", help="Skip event/tick steps")
    args = parser.parse_args()
    asyncio.run(capture_all(port=args.port, do_tick=not args.no_tick))
