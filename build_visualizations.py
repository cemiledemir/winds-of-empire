"""
Build all visualizations for the Winds of Empire website.

Outputs:
    images/rise_fall_empires.png       — polished static stacked area chart
    visualizations/viz1_rise_fall.html — interactive Plotly stacked area chart
    visualizations/viz2_routes.html    — enhanced Folium route map
    visualizations/viz3_encounters.html— geographic encounter heatmap
    data/encounters_geo.json           — encounter coordinates (intermediate)
"""

import json
import pathlib

import folium
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from folium.plugins import HeatMap

# ─── Configuration ───────────────────────────────────────────────────────────

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "data"

PALETTE = {
    "British": "#C8102E",
    "Dutch": "#FF6B00",
    "Spanish": "#F1BF00",
    "French": "#002395",
}

# Historical event annotations for the Rise & Fall chart
EVENTS = [
    (1756, 1763, "Seven Years' War"),
    (1775, 1783, "American Revolution"),
    (1789, 1799, "French Revolution"),
    (1803, 1815, "Napoleonic Wars"),
]

EVENT_MARKERS = [
    (1778, "Spain peaks\n(silver trade)"),
    (1795, "VOC dissolved"),
    (1805, "Trafalgar"),
    (1815, "Waterloo"),
]

# Plot etiquette constants
FONT_SIZE_TITLE = 16
FONT_SIZE_AXIS_LABEL = 13
FONT_SIZE_TICK = 11
FONT_SIZE_LEGEND = 11
FONT_SIZE_ANNOTATION = 9


# ─── 1. Extract Encounter Geo Data ──────────────────────────────────────────

def extract_encounter_geo():
    """Extract encounter rows with coordinates from cliwoc_clean.csv."""
    print("  Extracting encounter coordinates...")
    df = pd.read_csv(
        DATA / "cliwoc_clean.csv",
        usecols=["Lat", "Lon", "Year", "Nationality", "EncNat"],
        low_memory=False,
    )
    # Filter to rows with encounter data and valid coordinates
    enc = df[df["EncNat"].notna() & df["Lat"].notna() & df["Lon"].notna()].copy()
    enc = enc.rename(columns={"Year": "year", "Nationality": "nationality", "EncNat": "enc_nationality"})
    enc["lat"] = enc["Lat"].astype(float)
    enc["lon"] = enc["Lon"].astype(float)
    enc = enc[["lat", "lon", "year", "nationality", "enc_nationality"]]

    # Clean enc_nationality — raw values are uppercase, often typo'd, and
    # sometimes compound (e.g. "BRITISH AND DUTCH"). Normalize singles, drop compounds.
    name_map = {
        "BRITISH": "British", "ENGLISH": "British",
        "BRITITSH": "British", "BRISTISH": "British",
        "DUTCH": "Dutch",
        "FRENCH": "French",
        "SPANISH": "Spanish",
        "AMERICAN": "American",
        "PORTUGUESE": "Portuguese",
        "DANISH": "Danish",
        "SWEDISH": "Swedish",
    }

    def normalize_enc_nat(x):
        if not isinstance(x, str):
            return "Unknown"
        s = x.strip().upper()
        # Strip uncertainty markers like (?) so "BRITISH(?)" recovers as British
        s = s.replace("(?)", "").replace("(", "").replace(")", "").rstrip("?").strip()
        # Compound entries (multiple ships of different nations) → "Other"
        if " AND " in s or "," in s or "/" in s:
            return "Other"
        # Genuinely unidentified partner
        if s == "UNKNOWN":
            return "Unknown"
        # Recognized nation (incl. recovered misspellings) or obscure single name → "Other"
        return name_map.get(s, "Other")

    enc["enc_nationality"] = enc["enc_nationality"].apply(normalize_enc_nat)

    # Filter out unrealistic coordinates
    enc = enc[(enc["lat"].between(-80, 80)) & (enc["lon"].between(-180, 180))]

    out_path = DATA / "encounters_geo.json"
    enc.to_json(out_path, orient="records")
    print(f"  → {len(enc)} encounter records saved to {out_path.name}")
    return enc


# ─── 2. Static Rise & Fall Chart (PNG) ──────────────────────────────────────

def build_static_rise_fall():
    """Build publication-quality stacked area chart."""
    print("  Building static Rise & Fall chart...")

    with open(DATA / "nation_stats.json") as f:
        stats = json.load(f)

    df = pd.DataFrame(stats)
    pivot = df.pivot_table(index="year", columns="nation", values="count", fill_value=0)
    # Ensure consistent order: British, Dutch, Spanish, French
    order = ["British", "Dutch", "Spanish", "French"]
    pivot = pivot.reindex(columns=order, fill_value=0)

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.stackplot(
        pivot.index,
        [pivot[n] for n in order],
        labels=order,
        colors=[PALETTE[n] for n in order],
        alpha=0.85,
    )

    # War period shading
    for start, end, label in EVENTS:
        ax.axvspan(start, end, alpha=0.08, color="#333333", zorder=0)
        mid = (start + end) / 2
        ax.text(
            mid, ax.get_ylim()[1] * 0.97, label,
            ha="center", va="top", fontsize=FONT_SIZE_ANNOTATION,
            color="#555555", style="italic",
        )

    # Event markers
    for year, label in EVENT_MARKERS:
        ax.axvline(year, color="#666666", linewidth=0.8, linestyle="--", alpha=0.6)

    # Styling — plot etiquette
    ax.set_xlabel("Year", fontsize=FONT_SIZE_AXIS_LABEL, labelpad=8)
    ax.set_ylabel("Logbook Entries per Year", fontsize=FONT_SIZE_AXIS_LABEL, labelpad=8)
    ax.set_title(
        "Rise & Fall of Maritime Empires (1750–1850)",
        fontsize=FONT_SIZE_TITLE, fontweight="bold", pad=16,
    )
    ax.tick_params(axis="both", labelsize=FONT_SIZE_TICK)
    ax.set_xlim(1750, 1850)
    ax.set_ylim(0, None)

    # Remove top/right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Grid
    ax.yaxis.grid(True, alpha=0.25, linestyle="-")
    ax.set_axisbelow(True)

    # Legend
    ax.legend(
        loc="upper left", fontsize=FONT_SIZE_LEGEND, framealpha=0.9,
        edgecolor="none",
    )

    # Thousands separator on y-axis
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))

    fig.tight_layout()
    out_path = ROOT / "images" / "rise_fall_empires.png"
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  → Saved {out_path.name}")


# ─── 3. Interactive Plotly Rise & Fall ───────────────────────────────────────

def build_interactive_rise_fall():
    """Build interactive Plotly stacked area chart."""
    print("  Building interactive Plotly Rise & Fall...")

    with open(DATA / "nation_stats.json") as f:
        stats = json.load(f)

    df = pd.DataFrame(stats)
    pivot = df.pivot_table(index="year", columns="nation", values="count", fill_value=0)
    # Draw largest first so smaller nations' lines render on top of the fills
    order = ["British", "Dutch", "Spanish", "French"]
    pivot = pivot.reindex(columns=order, fill_value=0)

    def hex_to_rgba(hex_color, alpha=0.35):
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    fig = go.Figure()

    for nation in order:
        fig.add_trace(go.Scatter(
            x=pivot.index,
            y=pivot[nation],
            name=nation,
            mode="lines",
            fill="tozeroy",
            fillcolor=hex_to_rgba(PALETTE[nation], 0.35),
            line=dict(width=1.6, color=PALETTE[nation]),
            hovertemplate=f"<b>{nation}</b><br>Year: %{{x}}<br>Entries: %{{y:,.0f}}<extra></extra>",
        ))

    for start, end, label in EVENTS:
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor="gray", opacity=0.08,
            layer="below", line_width=0,
            annotation_text=label,
            annotation_position="top",
            annotation_font_size=10,
            annotation_font_color="#666",
        )

    fig.update_layout(
        title=dict(
            text="Rise & Fall of Maritime Empires (1750–1850)",
            font=dict(size=18, family="Georgia, serif"),
            x=0.5,
        ),
        xaxis=dict(
            title=dict(text="Year", font=dict(size=14)),
            tickfont=dict(size=12),
            range=[1750, 1850],
            dtick=10,
        ),
        yaxis=dict(
            title=dict(text="Logbook Entries per Year", font=dict(size=14)),
            tickfont=dict(size=12),
            separatethousands=True,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="center", x=0.5,
            font=dict(size=12),
        ),
        hovermode="x unified",
        template="plotly_white",
        margin=dict(t=100, b=60, l=70, r=30),
        height=500,
    )

    out_path = ROOT / "visualizations" / "viz1_rise_fall.html"
    fig.write_html(
        str(out_path),
        include_plotlyjs="cdn",
        full_html=True,
        config={"displayModeBar": True, "responsive": True},
    )
    print(f"  → Saved {out_path.name}")


# ─── 4. Enhanced Folium Route Map ────────────────────────────────────────────

def build_route_map():
    """Build enhanced Folium map with nation-togglable routes."""
    print("  Building Folium route map...")

    with open(DATA / "routes_sample.geojson") as f:
        geojson = json.load(f)

    # Create map centered on Atlantic
    m = folium.Map(
        location=[20, -20],
        zoom_start=3,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    # Group features by nationality
    nation_groups = {}
    for feature in geojson["features"]:
        props = feature.get("properties", {})
        nation = props.get("nationality", "Unknown")
        if nation not in nation_groups:
            nation_groups[nation] = []
        nation_groups[nation].append(feature)

    # Add each nation as a separate FeatureGroup for LayerControl
    for nation in ["British", "Dutch", "Spanish", "French"]:
        if nation not in nation_groups:
            continue
        fg = folium.FeatureGroup(
            name=f"<span style='color:{PALETTE[nation]}'> ■ </span>{nation}",
            show=False,
        )

        for feature in nation_groups[nation]:
            coords = feature["geometry"]["coordinates"]
            # GeoJSON is [lon, lat], Folium needs [lat, lon]
            latlon = [[c[1], c[0]] for c in coords]
            year = feature["properties"].get("year", "?")
            folium.PolyLine(
                latlon,
                color=PALETTE[nation],
                weight=1.2,
                opacity=0.4,
                tooltip=f"{nation} ({year})",
            ).add_to(fg)

        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Add a title
    title_html = """
    <div style="position:fixed; top:10px; left:50%; transform:translateX(-50%);
                z-index:9999; background:rgba(0,0,0,0.7); padding:10px 20px;
                border-radius:4px; font-family:Georgia,serif;">
        <span style="color:white; font-size:16px; font-weight:bold;">
            Highways of the Sea — Ship Routes 1750–1850
        </span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    out_path = ROOT / "visualizations" / "viz2_routes.html"
    m.save(str(out_path))
    print(f"  → Saved {out_path.name}")


# ─── 5. Geographic Encounter Heatmap ────────────────────────────────────────

def build_encounter_map(enc_df):
    """Encounter map: pick one nation at a time, see its encounters coloured by partner."""
    print("  Building encounter map...")

    enc_df = enc_df.copy()
    main_order = ["British", "Dutch", "Spanish", "French"]
    main = set(main_order)

    # Cross-nation encounters between the four key nations only
    enc_main = enc_df[
        enc_df["nationality"].isin(main)
        & enc_df["enc_nationality"].isin(main)
        & (enc_df["nationality"] != enc_df["enc_nationality"])
    ].copy()

    # Build the map with no auto-tile so we can add the basemap with control=False
    # (otherwise it joins the radio group with the nation FGs and gets deselected).
    m = folium.Map(
        location=[20, -20],
        zoom_start=3,
        tiles=None,
        prefer_canvas=True,
    )
    folium.TileLayer("CartoDB dark_matter", control=False).add_to(m)

    # One radio FG per nation; markers in nation X's layer are coloured by the
    # *other* nation in the pair.
    for nation in main_order:
        involved = enc_main[
            (enc_main["nationality"] == nation) | (enc_main["enc_nationality"] == nation)
        ]
        if involved.empty:
            continue

        fg = folium.FeatureGroup(
            name=f"<span style='color:{PALETTE[nation]}'> ■ </span>{nation}",
            overlay=False,
            control=True,
            show=False,
        )
        for _, row in involved.iterrows():
            partner = (
                row["enc_nationality"] if row["nationality"] == nation
                else row["nationality"]
            )
            color = PALETTE[partner]
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=3.5,
                color=color,
                weight=0,
                fill=True,
                fill_color=color,
                fill_opacity=0.6,
                tooltip=f"{row['nationality']} × {row['enc_nationality']} ({int(row['year'])})",
            ).add_to(fg)
        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Title
    title_html = """
    <div style="position:fixed; top:10px; left:50%; transform:translateX(-50%);
                z-index:9999; background:rgba(0,0,0,0.7); padding:10px 20px;
                border-radius:4px; font-family:Georgia,serif;">
        <span style="color:white; font-size:16px; font-weight:bold;">
            Encounters at Sea — Where Ships Met (1750–1850)
        </span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    out_path = ROOT / "visualizations" / "viz3_encounters.html"
    m.save(str(out_path))
    print(f"  → Saved {out_path.name}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  WINDS OF EMPIRE — Building Visualizations")
    print("=" * 60)

    # Step 1: Extract encounter data with coordinates
    enc_df = extract_encounter_geo()

    # Step 2: Interactive Plotly area chart
    build_interactive_rise_fall()

    # Step 3: Folium route map
    build_route_map()

    # Step 4: Encounter map
    build_encounter_map(enc_df)

    print("\n" + "=" * 60)
    print("  ✓ All visualizations built successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
