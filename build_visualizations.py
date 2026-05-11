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

    # Clean enc_nationality — keep only recognizable nations, label rest as "Other"
    main_nations = {"British", "Dutch", "French", "Spanish", "American", "Portuguese", "Danish", "Swedish"}
    enc["enc_nationality"] = enc["enc_nationality"].apply(
        lambda x: x if x in main_nations else "Other"
    )

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
    order = ["French", "Spanish", "Dutch", "British"]  # Bottom to top for stacking
    pivot = pivot.reindex(columns=order, fill_value=0)

    fig = go.Figure()

    def hex_to_rgba(hex_color, alpha=0.7):
        """Convert hex color to rgba string for Plotly."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    for nation in order:
        fig.add_trace(go.Scatter(
            x=pivot.index,
            y=pivot[nation],
            name=nation,
            stackgroup="one",
            mode="lines",
            line=dict(width=0.5, color=PALETTE[nation]),
            fillcolor=hex_to_rgba(PALETTE[nation], 0.7),
            hovertemplate=f"<b>{nation}</b><br>Year: %{{x}}<br>Entries: %{{y:,.0f}}<extra></extra>",
        ))

    # Add war period annotations as shapes
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
        fg = folium.FeatureGroup(name=f"<span style='color:{PALETTE[nation]}'> ■ </span>{nation}")

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
    """Build geographic encounter heatmap showing WHERE ships met."""
    print("  Building encounter heatmap...")

    # Separate same-nation vs cross-nation encounters
    enc_df = enc_df.copy()
    enc_df["cross_nation"] = enc_df["nationality"] != enc_df["enc_nationality"]

    # Build a Folium map with two layers: same-nation and cross-nation encounters
    m = folium.Map(
        location=[20, -20],
        zoom_start=3,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    # All encounters as heatmap
    all_heat_data = enc_df[["lat", "lon"]].values.tolist()
    fg_all = folium.FeatureGroup(name="All Encounters (density)")
    HeatMap(
        all_heat_data,
        radius=8,
        blur=12,
        max_zoom=6,
        gradient={0.2: "#440154", 0.4: "#31688e", 0.6: "#35b779", 0.8: "#fde725", 1.0: "#ffffff"},
    ).add_to(fg_all)
    fg_all.add_to(m)

    # Cross-nation encounters only (more interesting — where empires collided)
    cross = enc_df[enc_df["cross_nation"]]
    cross_heat = cross[["lat", "lon"]].values.tolist()
    fg_cross = folium.FeatureGroup(name="Cross-Nation Encounters", show=False)
    HeatMap(
        cross_heat,
        radius=10,
        blur=14,
        max_zoom=6,
        gradient={0.2: "#E63946", 0.4: "#FF6B00", 0.6: "#F1BF00", 0.8: "#ffffff", 1.0: "#ffffff"},
    ).add_to(fg_cross)
    fg_cross.add_to(m)

    # Top encounter hotspots as circle markers (aggregated to 2° grid)
    cross_grid = cross.copy()
    cross_grid["lat_bin"] = (cross_grid["lat"] / 2).round() * 2
    cross_grid["lon_bin"] = (cross_grid["lon"] / 2).round() * 2
    hotspots = cross_grid.groupby(["lat_bin", "lon_bin"]).size().reset_index(name="count")
    hotspots = hotspots.nlargest(30, "count")

    fg_hotspots = folium.FeatureGroup(name="Top Encounter Hotspots", show=False)
    for _, row in hotspots.iterrows():
        folium.CircleMarker(
            location=[row["lat_bin"], row["lon_bin"]],
            radius=max(4, min(20, row["count"] / 10)),
            color="#E63946",
            fill=True,
            fill_color="#E63946",
            fill_opacity=0.6,
            weight=1,
            tooltip=f"~{int(row['count'])} cross-nation encounters",
        ).add_to(fg_hotspots)
    fg_hotspots.add_to(m)

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

    # Step 2: Static figure
    build_static_rise_fall()

    # Step 3: Interactive Plotly
    build_interactive_rise_fall()

    # Step 4: Folium route map
    build_route_map()

    # Step 5: Encounter heatmap
    build_encounter_map(enc_df)

    print("\n" + "=" * 60)
    print("  ✓ All visualizations built successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
