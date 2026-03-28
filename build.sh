#!/bin/bash
# CivGraph — Build standalone binary for macOS/Linux
#
# Prerequisites:
#   pip install pyinstaller
#   pip install -r requirements.txt
#
# Usage:
#   chmod +x build.sh
#   ./build.sh
#
# Output: dist/civgraph (single executable)

set -e

echo "Building CivGraph standalone binary..."
echo ""

# Clean previous builds
rm -rf build/ dist/ __pycache__/

# Build
pyinstaller civgraph.spec

echo ""
echo "Build complete!"
echo "Binary: dist/civgraph"
echo ""
echo "Run with: ./dist/civgraph"
