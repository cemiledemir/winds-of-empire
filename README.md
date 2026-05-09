# Winds of Empire — 100 Years at Sea

A data-driven narrative website exploring how four European empires (British, Dutch, French, Spanish)
dominated the world's oceans between 1750 and 1850, built from the **CLIWOC 2.1** ship-logbook dataset.

**Course:** DTU 02806 Social Data Analysis & Visualization — Spring 2026

---

## Project Description

The CLIWOC dataset (Climatological Database for the World's Oceans) contains over 287,000 daily
logbook entries from hundreds of ships, originally digitised for pre-industrial climate research.
This project repurposes that data to tell the story of maritime empire — tracing the rise and fall of
four nations through their logbook counts, ocean routes, wind vocabularies, and ship encounters.

The deliverables are:
- **`index.html`** — A single-page scrollytelling website with four interactive visualizations
- **`explainer_notebook.ipynb`** — Jupyter notebook covering all analysis, cleaning decisions, and narrative design rationale
- **`data/pipeline.py`** — Reproducible data pipeline (raw TSV → cleaned CSV + JSON files)
- **`requirements.txt`** — Python dependencies

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/winds-of-empire.git
cd winds-of-empire
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Optional but recommended: use a virtual environment.

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the data pipeline

The pipeline is provided as a Jupyter Notebook for better visibility of the cleaning process.

Open data/pipeline.ipynb in VS Code or Jupyter.

Run all cells to process the raw TSV.

This generates the following files in `data/`:
- `cliwoc_clean.csv` — cleaned, filtered dataset (1750–1850, 4 nations)
- `nation_stats.json` — sailings per nation per year
- `routes_sample.geojson` — sampled voyage route segments (≤5,000)
- `wind_words_by_nation.json` — wind-term frequencies per nation
- `encounters.json` — ship encounter edge list

### 5. Open the website

Because the site uses `fetch()` calls to load JSON files, you need a local HTTP server
(not `file://` directly, due to browser CORS restrictions):

```bash
# Python built-in server
python3 -m http.server 8000
# Then open http://localhost:8000 in your browser
```

Or use the VS Code Live Server extension.

### 6. Run the explainer notebook

```bash
jupyter notebook explainer_notebook.ipynb
# or
jupyter lab
```

Run all cells in order (Kernel → Restart & Run All). The notebook reads `data/cliwoc_clean.csv`
and the JSON files produced by the pipeline.

To execute without opening the UI:

```bash
jupyter nbconvert --to notebook --execute explainer_notebook.ipynb
```

---

## GitHub Pages Deployment

### Option A: Deploy from `main` branch

1. Push the project to a GitHub repository.
2. In repository Settings → Pages → Source, select **`main` branch** and **`/ (root)`** folder.
3. GitHub will serve `index.html` as the site root.
4. Update the "GitHub Pages" link in `index.html` footer with your actual Pages URL.

### Option B: Deploy from `gh-pages` branch

```bash
git checkout -b gh-pages
git push origin gh-pages
# Then enable Pages on the gh-pages branch in repository settings
```

**Note:** The `data/cliwoc_clean.csv` file is ~50 MB and should be added to `.gitignore`. The
JSON files (`nation_stats.json`, `routes_sample.geojson`, etc.) are small and must be committed.

---

## File Structure

```
cliwoc-project/
├── index.html                  ← Main narrative website (4 acts + intro + conclusion)
├── style.css                   ← Nautical-historical design system (CSS variables, typography)
├── js/
│   ├── timeline.js             ← Plotly.js stacked area chart (Act I)
│   ├── globe.js                ← D3.js orthographic globe with drag rotation (Act II)
│   ├── wind_words.js           ← D3.js force-directed bubble chart (Act III)
│   └── encounters.js           ← D3.js force-directed network graph (Act IV)
├── data/
│   ├── pipeline.ipynb          ← Full data-cleaning & export pipeline
│   ├── CLIWOC21.tsv            ← Raw dataset 
│   ├── cliwoc_clean.csv        ← Cleaned dataset (output of pipeline)
│   ├── nation_stats.json       ← Aggregated stats per nation per year
│   ├── routes_sample.geojson   ← Voyage path segments (≤5,000 sampled)
│   ├── wind_words_by_nation.json ← Wind-term word frequencies per nation
│   ├── encounters.json         ← Ship encounter edge list
│   └── routes_folium.html      ← Interactive Folium map (from notebook)
├── explainer_notebook.ipynb    ← Jupyter explainer notebook
├── requirements.txt            ← Python dependencies
└── README.md                   ← This file
```

---

## Dataset Citation

**CLIWOC 2.1 — Climatological Database for the World's Oceans 1750–1850**

> Wheeler, D., García-Herrera, R., Wilkinson, C.W., Ward, C. (eds.) (2005).
> *Atmospheric circulation reconstructions over the Earth (ACRE): New datasets from old ships' logbooks*.
> EU project CLIWOC (EVK2-CT-2000-00090).
> Available at: https://www.historicalclimatology.com/cliwoc.html

---

## Data Limitations

- **File size:** The raw CLIWOC TSV is ~200 MB. The cleaned CSV is ~50 MB (gitignore recommended).
- **Coverage bias:** Dutch and British archives are over-represented (~80% of records).
  French and Spanish records are thinner, especially post-1789.
- **Language:** Wind descriptions are in Dutch, English, French, and Spanish — mixed-language
  entries and transcription inconsistencies are common.
- **Encounter data:** The `EncNat` column is populated for ~12% of rows only.
