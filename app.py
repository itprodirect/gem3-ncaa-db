import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import os
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(
    page_title="GEM3 NCAA Scout",
    layout="wide",
    initial_sidebar_state="expanded"
)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, 'ncaa-analytics',
                       'db', 'ncaa_d1_master.db')

# --- DATA LOADING ---


@st.cache_data
def load_data():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found at {DB_PATH}")
        return pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT 
        player_id, full_name, team_slug, team_name, conference, season, 
        class_year, height, pos,
        g, mp, pts, trb, ast, stl, blk, 
        fg_pct, three_p_pct, ft_pct, ts_pct
    FROM view_player_profiles 
    WHERE g > 5
    """
    df = pd.read_sql(query, conn)
    conn.close()

    # --- PRE-CALCULATIONS ---
    features = ['pts', 'trb', 'ast', 'stl',
                'blk', 'fg_pct', 'three_p_pct', 'ts_pct']

    # 1. Normalize for Similarity (Z-Scores)
    for f in features:
        df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0)
        if df[f].std() != 0:
            df[f'{f}_z'] = (df[f] - df[f].mean()) / df[f].std()
        else:
            df[f'{f}_z'] = 0

    # 2. Calculate Percentiles (0-100 scale)
    for f in features:
        df[f'{f}_pct_rank'] = df[f].rank(pct=True) * 100

    # 3. Create a "Search Index" column for easier filtering
    # This allows us to search "Duke Smith" and find matches
    df['search_index'] = df['full_name'] + " " + \
        df['team_name'] + " " + df['team_slug']

    return df


df = load_data()

if df.empty:
    st.warning("No data found. Please run the scraper scripts first.")
    st.stop()

# --- STATE MANAGEMENT (URL & DEEP LINKING) ---
query_params = st.query_params
default_pid = None
default_season_idx = 0

if "player_id" in query_params:
    try:
        pid_param = int(query_params["player_id"])
        player_record = df[df['player_id'] == pid_param]
        if not player_record.empty:
            default_pid = pid_param
            target_season = player_record.iloc[0]['season']
            seasons_list = sorted(df['season'].unique(), reverse=True)
            if target_season in seasons_list:
                default_season_idx = seasons_list.index(target_season)
    except:
        pass

# --- SIDEBAR: SUPER SEARCH ---
st.sidebar.title("🏀 GEM3 Scout")

# 1. Season Filter
seasons = sorted(df['season'].unique(), reverse=True)
sel_season = st.sidebar.selectbox("Season", seasons, index=default_season_idx)
season_df = df[df['season'] == sel_season]

st.sidebar.divider()

# 2. THE SUPER SEARCH BAR
st.sidebar.markdown("### 🔎 Smart Search")
st.sidebar.caption("Type a Player Name OR Team Name")

# This text input filters the list below it
search_query = st.sidebar.text_input(
    "Search", placeholder="e.g. 'Duke', 'Smith', 'Akron'")

filtered_players = season_df
if search_query:
    # Case-insensitive search across Name and Team
    # We use the pre-built 'search_index' column for speed
    filtered_players = season_df[season_df['search_index'].str.contains(
        search_query, case=False)]

# 3. Results Dropdown (Autocomplete Style)
# Map ID -> Display String
player_map = dict(zip(
    filtered_players['player_id'], filtered_players['full_name'] + " (" + filtered_players['team_slug'] + ")"))

# Handle Selection Logic
dropdown_index = 0
if default_pid and default_pid in player_map:
    dropdown_index = list(player_map.keys()).index(default_pid)

selected_player_id = st.sidebar.selectbox(
    "Select Player",
    options=player_map.keys(),
    format_func=lambda x: player_map[x],
    index=dropdown_index,
    help="Select a player from the filtered list."
)

# Update URL if changed
if selected_player_id and selected_player_id != default_pid:
    st.query_params["player_id"] = str(selected_player_id)
    st.rerun()

# Handle empty search/selection
if not selected_player_id:
    st.info("👈 Use the sidebar to search for a player or team.")
    st.stop()

# --- MAIN PAGE ---
target = df[df['player_id'] == selected_player_id].iloc[0]

tab1, tab2, tab3 = st.tabs(
    ["👤 Player Profile", "📊 League Context", "📘 Glossary"])

# ==========================================
# TAB 1: PLAYER PROFILE
# ==========================================
with tab1:
    # Header
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title(target['full_name'])
        st.markdown(f"**{target['team_name']}** | {target['conference']}")
        st.caption(
            f"Season: {target['season']} | Class: {target['class_year']} | Pos: {target['pos']}")
    with c2:
        st.metric("True Shooting %",
                  f"{target['ts_pct']:.3f}", help="Points per shooting possession.")

    st.divider()

    col_viz, col_stats = st.columns([1, 1])

    with col_viz:
        # Radar Chart
        categories = ['Points', 'Rebounds', 'Assists',
                      'Steals', 'Blocks', 'FG%', '3P%', 'TS%']
        values = [
            target['pts_pct_rank'], target['trb_pct_rank'], target['ast_pct_rank'],
            target['stl_pct_rank'], target['blk_pct_rank'], target['fg_pct_pct_rank'],
            target['three_p_pct_pct_rank'], target['ts_pct_pct_rank']
        ]

        fig = go.Figure(data=go.Scatterpolar(
            r=values, theta=categories, fill='toself', name=target['full_name'], line_color='#ff4b4b'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            title="Percentile Rank (vs All D1)",
            height=350,
            margin=dict(t=30, b=30, l=40, r=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_stats:
        st.subheader("Season Stats")
        m1, m2, m3 = st.columns(3)
        m1.metric("PPG", f"{target['pts']:.1f}")
        m2.metric("RPG", f"{target['trb']:.1f}")
        m3.metric("APG", f"{target['ast']:.1f}")

        m4, m5, m6 = st.columns(3)
        m4.metric("STL", f"{target['stl']:.1f}")
        m5.metric("BLK", f"{target['blk']:.1f}")
        m6.metric("MPG", f"{target['mp']:.1f}")

        st.markdown("---")
        st.caption("Shooting Splits")
        s1, s2, s3 = st.columns(3)
        s1.metric("FG%", f"{target['fg_pct']:.3f}")
        s2.metric("3P%", f"{target['three_p_pct']:.3f}")
        s3.metric("FT%", f"{target['ft_pct']:.3f}")

    # Similarity Section
    st.subheader("🧬 Similarity Engine")
    st.caption(
        f"Identifying historical players with similar statistical footprints to {target['full_name']}.")

    # Calculate Distance
    features_z = [f'{f}_z' for f in ['pts', 'trb', 'ast',
                                     'stl', 'blk', 'fg_pct', 'three_p_pct', 'ts_pct']]
    t_vec = target[features_z].values.astype(float)
    all_vec = df[features_z].values.astype(float)

    diff = all_vec - t_vec
    dists = np.sqrt(np.sum(diff**2, axis=1))
    df['distance'] = dists

    # Get Top matches
    matches = df[df['player_id'] != target['player_id']
                 ].sort_values('distance').head(4)

    cols = st.columns(4)
    for i, (idx, row) in enumerate(matches.iterrows()):
        with cols[i]:
            sim_score = max(0, 100 - (row['distance'] * 12))
            with st.container(border=True):
                st.markdown(f"**{row['full_name']}**")
                st.text(f"{row['team_slug']} '{str(row['season'])[2:]}")
                st.progress(int(sim_score), text=f"Match: {int(sim_score)}%")

                # CLICKABLE BUTTON FOR PROFILE NAVIGATION
                if st.button(f"View Profile", key=f"btn_{idx}"):
                    st.query_params["player_id"] = str(row['player_id'])
                    st.rerun()

# ==========================================
# TAB 2: LEAGUE CONTEXT
# ==========================================
with tab2:
    st.header("📊 League Context")
    st.caption("Compare the selected player against the entire NCAA D1.")

    analysis_mode = st.selectbox(
        "Choose Analysis View",
        [
            "Scoring Volume (PTS vs Minutes)",
            "Shooting Efficiency (TS% vs PTS)",
            "Playmaking (AST vs PTS)",
            "Defensive Activity (STL vs BLK)",
            "Three Point Specialist (3P% vs PTS)"
        ]
    )

    if analysis_mode == "Scoring Volume (PTS vs Minutes)":
        x_col, y_col = "mp", "pts"
    elif analysis_mode == "Shooting Efficiency (TS% vs PTS)":
        x_col, y_col = "pts", "ts_pct"
    elif analysis_mode == "Playmaking (AST vs PTS)":
        x_col, y_col = "pts", "ast"
    elif analysis_mode == "Defensive Activity (STL vs BLK)":
        x_col, y_col = "stl", "blk"
    else:
        x_col, y_col = "pts", "three_p_pct"

    fig_scatter = px.scatter(
        season_df,
        x=x_col,
        y=y_col,
        color='pos',
        hover_data=['full_name', 'team_name'],
        title=f"{analysis_mode}",
        opacity=0.4,
        height=600
    )

    # Highlight Target
    fig_scatter.add_scatter(
        x=[target[x_col]],
        y=[target[y_col]],
        mode='markers',
        marker=dict(size=20, color='red', line=dict(width=2, color='white')),
        name=target['full_name']
    )

    st.plotly_chart(fig_scatter, use_container_width=True)

# ==========================================
# TAB 3: GLOSSARY
# ==========================================
with tab3:
    st.header("📘 Analytics Glossary")
    st.markdown("""
    ### Why these metrics matter
    
    **TS% (True Shooting Percentage)**
    > A measure of shooting efficiency that takes into account 2-point field goals, 3-point field goals, and free throws. 
    > *Formula: PTS / (2 * (FGA + 0.44 * FTA))*
    
    **Similarity Score**
    > Our proprietary algorithm that calculates the Euclidean distance between two players' statistical profiles (Z-scored). 
    
    **Percentile Rank**
    > How a player compares to the rest of Division I. If a player is in the **90th Percentile** for Points, they score more than 90% of all other D1 players.
    """)
