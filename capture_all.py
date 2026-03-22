"""Capture all screenshots for README with refined visuals."""

import asyncio
import json
from playwright.async_api import async_playwright

URL = "http://localhost:8422"
OUT = "docs"
VP = {"width": 1920, "height": 1080}


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport=VP, device_scale_factor=2)

        # ── Load app and let graph settle ────────────────────────────
        print("Loading CivGraph...")
        await page.goto(URL)
        await page.wait_for_selector("#graph-svg .node", timeout=15000)
        await asyncio.sleep(5)

        # ── 01: Main graph (clan coloring) ───────────────────────────
        print("01  Main graph view...")
        await page.screenshot(path=f"{OUT}/01-main-graph.png")

        # ── 02: Class color mode ─────────────────────────────────────
        print("02  Class coloring...")
        await click_color_mode(page, "Class")
        await asyncio.sleep(1)
        await page.screenshot(path=f"{OUT}/02-class-view.png")

        # ── 03: Agent detail with capital bars ───────────────────────
        print("03  Agent detail...")
        await click_color_mode(page, "Clan")
        await asyncio.sleep(0.5)
        # Click a node near center
        nodes = await page.query_selector_all(".node circle")
        if len(nodes) > 15:
            await nodes[15].dispatch_event("click")
        await asyncio.sleep(1.5)
        await page.screenshot(path=f"{OUT}/03-agent-detail.png")

        # ── 04: Fire event and capture mid-propagation ───────────────
        print("04  Event propagation...")
        await page.select_option("#event-type", "housing_crisis")
        await page.fill("#event-title", "Riverside Housing Boom")
        await page.select_option("#event-topic", "real_estate")
        await page.evaluate("document.getElementById('event-sentiment').value = -0.7; document.getElementById('event-sentiment').dispatchEvent(new Event('input'))")
        await page.evaluate("document.getElementById('event-intensity').value = 0.9; document.getElementById('event-intensity').dispatchEvent(new Event('input'))")
        await page.click("#btn-fire-event")
        await asyncio.sleep(1.5)
        await page.screenshot(path=f"{OUT}/04-event-propagation.png")
        await asyncio.sleep(6)

        # ── 05: Post-event with log + environment gauges ─────────────
        print("05  Post-event state...")
        await asyncio.sleep(1)
        await page.screenshot(path=f"{OUT}/05-post-event.png")

        # ── 06: Bridge agents ────────────────────────────────────────
        print("06  Bridge agents...")
        await page.click("#btn-bridges")
        await asyncio.sleep(2)
        await page.screenshot(path=f"{OUT}/06-bridge-agents.png")

        # ── 07: Advance time and show environment + emergence ────────
        print("07  Environment + emergence after tick...")
        await page.select_option("#tick-years", "5")
        await page.click("#btn-tick")
        await asyncio.sleep(3)
        # Switch to capital color mode to show how capitals changed
        await click_color_mode(page, "Capital")
        await asyncio.sleep(1)
        await page.screenshot(path=f"{OUT}/07-environment-tick.png")

        # ── 08: Agent Anatomies artifact ─────────────────────────────
        print("08  Agent Anatomies artifact...")
        await click_color_mode(page, "Clan")
        await asyncio.sleep(0.5)
        btn = await page.query_selector('[data-artifact="anatomies"]')
        await btn.click()
        await asyncio.sleep(2)
        await page.screenshot(path=f"{OUT}/08-anatomies.png")
        await page.click("#btn-close-artifact")
        await asyncio.sleep(0.5)

        # ── 09: Influence Survey artifact ────────────────────────────
        print("09  Influence Survey artifact...")
        btn = await page.query_selector('[data-artifact="topography"]')
        await btn.click()
        await asyncio.sleep(2)
        await page.screenshot(path=f"{OUT}/09-topography.png")
        await page.click("#btn-close-artifact")
        await asyncio.sleep(0.5)

        # ── 10: Clan Constellations artifact ─────────────────────────
        print("10  Clan Constellations artifact...")
        btn = await page.query_selector('[data-artifact="constellation"]')
        await btn.click()
        await asyncio.sleep(2)
        await page.screenshot(path=f"{OUT}/10-constellations.png")
        await page.click("#btn-close-artifact")
        await asyncio.sleep(0.5)

        # ── 11: City Pulse artifact ──────────────────────────────────
        print("11  City Pulse artifact...")
        btn = await page.query_selector('[data-artifact="citypulse"]')
        await btn.click()
        await asyncio.sleep(2)
        await page.screenshot(path=f"{OUT}/11-citypulse.png")
        await page.click("#btn-close-artifact")
        await asyncio.sleep(0.5)

        # ── 12: Emergence color mode ─────────────────────────────────
        print("12  Emergence color mode...")
        await click_color_mode(page, "Emergence")
        await asyncio.sleep(1)
        await page.screenshot(path=f"{OUT}/12-emergence-color.png")

        # ── 13: Emergence artifact ───────────────────────────────────
        print("13  Emergence Observatory artifact...")
        # Advance a few more years to build emergence history
        await page.select_option("#tick-years", "5")
        await page.click("#btn-tick")
        await asyncio.sleep(3)
        btn = await page.query_selector('[data-artifact="emergence"]')
        await btn.click()
        await asyncio.sleep(2)
        await page.screenshot(path=f"{OUT}/13-emergence-observatory.png")
        await page.click("#btn-close-artifact")
        await asyncio.sleep(0.5)

        # ── 14: Agent detail with emergence scores ───────────────────
        print("14  Agent detail with emergence scores...")
        await click_color_mode(page, "Clan")
        nodes = await page.query_selector_all(".node circle")
        if len(nodes) > 20:
            await nodes[20].dispatch_event("click")
        await asyncio.sleep(1.5)
        await page.screenshot(path=f"{OUT}/14-agent-emergence-detail.png")

        await browser.close()
        print("\nAll 14 screenshots captured.")


async def click_color_mode(page, label):
    btns = await page.query_selector_all(".color-modes .btn")
    for btn in btns:
        text = await btn.inner_text()
        if label in text:
            await btn.click()
            return


if __name__ == "__main__":
    asyncio.run(main())
