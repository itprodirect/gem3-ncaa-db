# GEM3 NCAA Database & Analytics Engine

A full-stack sports analytics pipeline that scrapes, normalizes, and analyzes NCAA Division I Men's Basketball data (2021–2025). Features a proprietary **Player Similarity Engine** and an interactive **Streamlit Scout Dashboard**.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red)
![Database](https://img.shields.io/badge/Database-SQLite-green)

## 🚀 Features

- **Full D1 Coverage:** Scrapes stats and rosters for all 360+ Division I teams.
- **Historical Database:** 5-year historical archive (2021-2025) stored in a normalized SQLite database.
- **Similarity Engine:** Uses Z-Score normalization and Euclidean distance to find historical comparisons for any current player.
- **Interactive Dashboard:**
  - **Smart Search:** Omnibox search for Players or Teams.
  - **Radar Charts:** Visual percentile rankings against the entire league.
  - **Deep Linking:** Shareable URLs for specific player profiles.
  - **League Context:** Scatter plots comparing efficiency and volume across the NCAA.

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/itprodirect/gem3-ncaa-db.git
   cd gem3-ncaa-db
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # Windows Git Bash
   # source .venv/bin/activate    # Mac/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## 🔄 Data Pipeline Usage

The pipeline is designed to be modular. Run these scripts in order to build the database from scratch.

1. **Fetch Team List:**
   Gets the master list of active D1 schools.
   ```bash
   python scripts/00_fetch_team_slugs.py
   ```

2. **Scrape Raw Data:**
   Downloads HTML pages for all teams (2021-2025).
   *Note: Includes rate-limiting to prevent IP bans. This step takes several hours.*
   ```bash
   python scripts/01_scrape_all_d1.py
   ```

3. **Parse & Load Database:**
   Converts HTML to CSVs and loads the SQLite database (Fact/Dim tables).
   ```bash
   python scripts/02_parse_stats_and_roster.py
   python scripts/03_load_sqlite_master.py
   ```

4. **Run Analytics:**
   Generates SQL Views and runs the Similarity Engine logic.
   ```bash
   python scripts/04_create_analytics_views.py
   ```

## 📊 Launching the Dashboard

Once the database is built, launch the frontend:

```bash
streamlit run app.py
```

Open your browser to `http://localhost:8501`.

## 📂 Project Structure

```text
gem3-ncaa-db/
├── app.py                     # Main Streamlit Dashboard
├── configs/
│   └── d1_teams_master.json   # generated team config
├── ncaa-analytics/            # Data storage (Ignored by Git)
│   ├── data_raw/              # HTML files
│   ├── data_intermediate/     # CSV files
│   └── db/                    # SQLite Database
├── scripts/                   # ETL Pipeline
│   ├── 00_fetch_team_slugs.py
│   ├── 01_scrape_all_d1.py
│   ├── 02_parse_stats_and_roster.py
│   ├── 03_load_sqlite_master.py
│   └── 04_create_analytics_views.py
├── requirements.txt
└── README.md
```

## ⚠️ Data Note
The `ncaa-analytics/` folder containing raw data and the SQLite database is included in `.gitignore` to keep the repository lightweight. You must run the scraping scripts to populate the data locally.
