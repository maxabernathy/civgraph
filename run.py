#!/usr/bin/env python3
"""Launch CivGraph server."""

import uvicorn

if __name__ == "__main__":
    print("\n  CivGraph — Agent-Based City Modeling")
    print("  ─────────────────────────────────────")
    print("  Open http://localhost:8420 in your browser\n")
    uvicorn.run("server:app", host="0.0.0.0", port=8420, reload=True)
