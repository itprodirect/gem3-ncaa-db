import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import os
import plotly.express as px

# --- CONFIGURATION ---
st.set_page_config(page_title="GEM3 NCAA Scout", layout="wide")
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'ncaa-analytics',
                       'db', 'ncaa_d1_master.db')

# --- DATA LOADING (Cached for Speed) ---


@st.cache_data
def load_data():
    """Loads the player profiles view from SQLite."""
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found at {DB_PATH}")
        return pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM view_player_profiles WHERE g > 0"
    df = pd.read_sql(query, conn)
    conn.close()

    # Normalize Columns for Similarity
    features = ['pts', 'trb', 'ast', 'stl',
                'blk', 'fg_pct', 'three_p_pct', 'ts_pct']
    for f in features:
        df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0)
        # Calculate Z-Scores
        if df[f].std() != 0:
            df[f'{f}_z'] = (df[f] - df[f].mean()) / df[f].std()
        else:
            df[f'{f}_z'] = 0

    return df


df = load_data()

# --- SIDEBAR CONTROLS ---
st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/commons/d/dd/NCAA_logo.svg", width=100)
st.sidebar.title("GEM3 Scout")

if df.empty:
    st.warning("No data found. Run the scraper first!")
    st.stop()

# Filter: Season
seasons = sorted(df['season'].unique(), reverse=True)
selected_season = st.sidebar.selectbox("Select Season", seasons)

# Filter: Team
season_df = df[df['season'] == selected_season]
teams = sorted(season_df['team_slug'].unique())
selected_team = st.sidebar.selectbox("Select Team", teams)

# Filter: Player
team_players = season_df[season_df['team_slug'] == selected_team]
player_names = sorted(team_players['full_name'].unique())
selected_player_name = st.sidebar.selectbox("Select Player", player_names)

# --- MAIN CONTENT ---
# Get target player data
target = team_players[team_players['full_name']
                      == selected_player_name].iloc[0]

st.title(f"{target['full_name']}")
st.markdown(
    f"**{target['team_name']}** | {target['class_year']} | {target['pos']} | {target['height']}")

# 1. Top Level Stats
cols = st.columns(6)
cols[0].metric("PPG", f"{target['pts']:.1f}")
cols[1].metric("RPG", f"{target['trb']:.1f}")
cols[2].metric("APG", f"{target['ast']:.1f}")
cols[3].metric("TS%", f"{target['ts_pct']:.3f}")
cols[4].metric("FG%", f"{target['fg_pct']:.3f}")
cols[5].metric("3P%", f"{target['three_p_pct']:.3f}")

st.divider()

# 2. Similarity Engine
st.subheader("🤖 Similarity Engine")
st.caption(
    "Comparing statistical profile against all historical D1 players (2021-2025)")

# Run Calculation
features = ['pts', 'trb', 'ast', 'stl',
            'blk', 'fg_pct', 'three_p_pct', 'ts_pct']
dist_sq = 0
for f in features:
    dist_sq += (df[f'{f}_z'] - target[f'{f}_z']) ** 2

df['distance'] = np.sqrt(dist_sq)

# Exclude self and get top 5
matches = df[df['player_id'] != target['player_id']
             ].sort_values('distance').head(5)

# Display Comps
comp_cols = st.columns(5)
for i, (_, row) in enumerate(matches.iterrows()):
    with comp_cols[i]:
        st.info(f"**{row['full_name']}**")
        st.text(f"{row['team_slug']} '{row['season']}")
        st.markdown(f"**Sim Score:** {100 - (row['distance']*10):.1f}")
        st.markdown(f"""
        - **PPG:** {row['pts']:.1f}
        - **TS%:** {row['ts_pct']:.3f}
        """)

st.divider()

# 3. Context Plot
st.subheader("📊 Efficiency Context")
fig = px.scatter(
    season_df,
    x="mp",
    y="pts",
    color="pos",
    hover_data=["full_name", "team_slug"],
    title=f"Points vs Minutes ({selected_season})",
    color_discrete_sequence=px.colors.qualitative.Bold
)
# Highlight selected player
fig.add_scatter(
    x=[target['mp']],
    y=[target['pts']],
    mode='markers',
    marker=dict(size=15, color='red', line=dict(width=2, color='black')),
    name=target['full_name']
)
st.plotly_chart(fig, use_container_width=True)
