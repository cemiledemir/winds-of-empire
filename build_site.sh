#!/usr/bin/env bash
# ─── Winds of Empire — Build Script ──────────────────────────────────────────
# Generates all visualizations and prepares the site for GitHub Pages deployment.
# Usage: bash build_site.sh
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail
cd "$(dirname "$0")"

echo "═══════════════════════════════════════════════════════════"
echo "  Winds of Empire — Site Build"
echo "═══════════════════════════════════════════════════════════"

# 1. Ensure output directories exist
mkdir -p images visualizations

# 2. Build all visualizations
echo ""
echo "  [1/2] Building visualizations..."
python build_visualizations.py

# 3. Verify all required files exist
echo ""
echo "  [2/2] Verifying outputs..."
REQUIRED_FILES=(
    "index.html"
    "images/rise_fall_empires.png"
    "visualizations/viz1_rise_fall.html"
    "visualizations/viz2_routes.html"
    "visualizations/viz3_encounters.html"
)

ALL_OK=true
for f in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$f" ]]; then
        echo "    ✓ $f"
    else
        echo "    ✗ MISSING: $f"
        ALL_OK=false
    fi
done

echo ""
if $ALL_OK; then
    echo "  ✓ Build complete! All files present."
    echo ""
    echo "  Preview locally:"
    echo "    python3 -m http.server 8000"
    echo "    → http://localhost:8000"
else
    echo "  ✗ Build incomplete — some files are missing."
    exit 1
fi
