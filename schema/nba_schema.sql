-- NBA / Pro schema for career-graph layer

CREATE TABLE IF NOT EXISTS dim_player_global (
    global_player_id TEXT PRIMARY KEY,
    canonical_name   TEXT NOT NULL,
    birthdate        TEXT,
    height_cm        REAL,
    weight_kg        REAL,
    primary_position   TEXT,
    secondary_position TEXT,
    created_at       TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fact_nba_season (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    global_player_id TEXT NOT NULL,
    season          INTEGER NOT NULL,
    age             INTEGER,
    team            TEXT,
    league          TEXT,

    gp              INTEGER,
    gs              INTEGER,
    mp_per_g        REAL,
    pts_per_g       REAL,
    trb_per_g       REAL,
    ast_per_g       REAL,
    stl_per_g       REAL,
    blk_per_g       REAL,
    tov_per_g       REAL,

    fg_pct          REAL,
    threep_pct      REAL,
    ft_pct          REAL,
    ts_pct          REAL,

    per             REAL,
    ws              REAL,
    ws_per_48       REAL,
    bpm             REAL,
    vorp            REAL,

    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (global_player_id) REFERENCES dim_player_global(global_player_id)
);