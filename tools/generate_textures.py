#!/usr/bin/env python3
"""Generate early-2000s web-aesthetic texture tiles for CivGraph UI.

Outputs small, tileable PNG textures into static/textures/.
These are designed to be layered via CSS background-image as subtle hints —
brushed metal, noise grain, micro grid, scanlines, and dot matrix.

Usage:
    python tools/generate_textures.py            # generate all textures
    python tools/generate_textures.py --list      # list available textures
    python tools/generate_textures.py noise grain # generate specific ones
"""

from __future__ import annotations

import argparse
import math
import random
import struct
import zlib
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "static" / "textures"


# ── Minimal PNG writer (no PIL dependency) ───────────────────────────────────

def _make_png(width: int, height: int, pixels: list[list[tuple[int, ...]]]) -> bytes:
    """Create a PNG file from RGBA pixel data. pixels[y][x] = (r, g, b, a)."""

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))

    raw = b""
    for row in pixels:
        raw += b"\x00"  # filter: none
        for r, g, b, a in row:
            raw += struct.pack("BBBB", r, g, b, a)

    idat = chunk(b"IDAT", zlib.compress(raw, 9))
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend


# ── Texture generators ──────────────────────────────────────────────────────

def gen_noise(width: int = 128, height: int = 128, opacity: int = 8) -> bytes:
    """Fine film-grain noise. Classic early-2000s texture overlay."""
    rng = random.Random(42)
    pixels = []
    for _ in range(height):
        row = []
        for _ in range(width):
            v = rng.randint(0, 255)
            row.append((v, v, v, opacity))
        pixels.append(row)
    return _make_png(width, height, pixels)


def gen_grain(width: int = 64, height: int = 64, opacity: int = 6) -> bytes:
    """Coarser photographic grain — slightly clustered noise."""
    rng = random.Random(7)
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            base = rng.gauss(128, 60)
            v = max(0, min(255, int(base)))
            a = opacity if rng.random() > 0.3 else 0
            row.append((v, v, v, a))
        pixels.append(row)
    return _make_png(width, height, pixels)


def gen_brushed_metal(width: int = 200, height: int = 4, opacity: int = 10) -> bytes:
    """Horizontal brushed-metal streaks. Tile vertically for the full effect."""
    rng = random.Random(99)
    pixels = []
    for y in range(height):
        # Each row is a continuous horizontal streak with gentle variation
        base = rng.randint(100, 160)
        row = []
        v = base
        for x in range(width):
            v += rng.randint(-3, 3)
            v = max(80, min(200, v))
            a = opacity + rng.randint(-2, 2)
            a = max(0, min(255, a))
            row.append((v, v, v, a))
        pixels.append(row)
    return _make_png(width, height, pixels)


def gen_grid(width: int = 24, height: int = 24, opacity: int = 10) -> bytes:
    """Subtle micro-grid / graph paper. Very Web 2.0 dashboard."""
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            on_line = (x == 0) or (y == 0)
            if on_line:
                row.append((180, 190, 210, opacity))
            else:
                row.append((0, 0, 0, 0))
        pixels.append(row)
    return _make_png(width, height, pixels)


def gen_scanlines(width: int = 2, height: int = 4, opacity: int = 10) -> bytes:
    """CRT scanline overlay — alternating transparent/dark rows."""
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            if y >= height // 2:
                row.append((0, 0, 0, opacity))
            else:
                row.append((0, 0, 0, 0))
        pixels.append(row)
    return _make_png(width, height, pixels)


def gen_dots(width: int = 8, height: int = 8, opacity: int = 12) -> bytes:
    """Halftone dot matrix pattern. Retro print aesthetic."""
    cx, cy = width // 2, height // 2
    r = 1.2
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist <= r:
                row.append((160, 170, 190, opacity))
            else:
                row.append((0, 0, 0, 0))
        pixels.append(row)
    return _make_png(width, height, pixels)


def gen_gradient_bg(width: int = 512, height: int = 512) -> bytes:
    """Colourful mesh gradient background — expressive purple/teal/rose aurora.
    Use as the master body background, stretched full-bleed."""
    pixels = []
    for y in range(height):
        ny = y / (height - 1)
        row = []
        for x in range(width):
            nx = x / (width - 1)

            # Top-left: vivid purple
            d1 = math.sqrt((nx - 0.10) ** 2 + (ny - 0.10) ** 2)
            f1 = max(0, 1 - d1 * 1.8)
            r1, g1, b1 = 90, 40, 150

            # Bottom-right: bright teal
            d2 = math.sqrt((nx - 0.90) ** 2 + (ny - 0.85) ** 2)
            f2 = max(0, 1 - d2 * 1.7)
            r2, g2, b2 = 20, 100, 130

            # Center-left: warm indigo
            d3 = math.sqrt((nx - 0.30) ** 2 + (ny - 0.55) ** 2)
            f3 = max(0, 1 - d3 * 1.9)
            r3, g3, b3 = 50, 30, 100

            # Top-right: rose / magenta
            d4 = math.sqrt((nx - 0.82) ** 2 + (ny - 0.15) ** 2)
            f4 = max(0, 1 - d4 * 2.2)
            r4, g4, b4 = 80, 30, 85

            # Bottom-left: deep ocean blue
            d5 = math.sqrt((nx - 0.15) ** 2 + (ny - 0.85) ** 2)
            f5 = max(0, 1 - d5 * 2.4)
            r5, g5, b5 = 20, 50, 110

            # Base: lighter dark slate
            rb, gb, bb = 22, 26, 42

            r = int(min(255, rb + r1 * f1 + r2 * f2 + r3 * f3 + r4 * f4 + r5 * f5))
            g = int(min(255, gb + g1 * f1 + g2 * f2 + g3 * f3 + g4 * f4 + g5 * f5))
            b = int(min(255, bb + b1 * f1 + b2 * f2 + b3 * f3 + b4 * f4 + b5 * f5))

            row.append((r, g, b, 255))
        pixels.append(row)
    return _make_png(width, height, pixels)


def gen_title_deco(width: int = 60, height: int = 48) -> bytes:
    """Decorative diagonal hatching for title bar — bold Y2K accent.
    Clearly visible as intentional decoration."""
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            # Diagonal stripes every 5px, 2px wide
            on_stripe = ((x + y) % 5) < 2
            # Soft fade at top/bottom 4px
            edge_fade = min(y, height - 1 - y) / 4.0
            edge_fade = min(1.0, edge_fade)
            if on_stripe:
                a = int(65 * edge_fade)
                row.append((120, 145, 210, a))
            else:
                row.append((0, 0, 0, 0))
        pixels.append(row)
    return _make_png(width, height, pixels)


def gen_diagonal(width: int = 6, height: int = 6, opacity: int = 8) -> bytes:
    """Diagonal pinstripe — subtle Y2K fabric texture."""
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            if (x + y) % height == 0:
                row.append((160, 170, 200, opacity))
            else:
                row.append((0, 0, 0, 0))
        pixels.append(row)
    return _make_png(width, height, pixels)


# ── Registry ─────────────────────────────────────────────────────────────────

TEXTURES: dict[str, tuple[callable, str]] = {
    "noise":         (gen_noise,         "Fine film-grain noise overlay"),
    "grain":         (gen_grain,         "Coarse photographic grain"),
    "brushed-metal": (gen_brushed_metal, "Horizontal brushed-metal streaks"),
    "grid":          (gen_grid,          "Micro graph-paper grid"),
    "scanlines":     (gen_scanlines,     "CRT scanline rows"),
    "dots":          (gen_dots,          "Halftone dot matrix"),
    "diagonal":      (gen_diagonal,      "Diagonal pinstripe"),
    "gradient-bg":   (gen_gradient_bg,   "Colourful aurora mesh gradient background"),
    "title-deco":    (gen_title_deco,    "Decorative title bar accent stripes"),
}


def generate(names: list[str] | None = None) -> list[Path]:
    """Generate textures. If names is None, generate all."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = names if names else list(TEXTURES.keys())
    created = []
    for name in targets:
        if name not in TEXTURES:
            print(f"  unknown texture: {name}")
            continue
        fn, desc = TEXTURES[name]
        path = OUTPUT_DIR / f"{name}.png"
        data = fn()
        path.write_bytes(data)
        print(f"  {path.name:20s} ({len(data):>5,} bytes)  {desc}")
        created.append(path)
    return created


def main():
    parser = argparse.ArgumentParser(description="Generate Y2K texture tiles")
    parser.add_argument("names", nargs="*", help="Texture names (omit for all)")
    parser.add_argument("--list", action="store_true", help="List available textures")
    args = parser.parse_args()

    if args.list:
        print("Available textures:")
        for name, (_, desc) in TEXTURES.items():
            print(f"  {name:20s} {desc}")
        return

    print(f"Generating textures -> {OUTPUT_DIR}/")
    created = generate(args.names if args.names else None)
    print(f"\n{len(created)} texture(s) written.")


if __name__ == "__main__":
    main()
