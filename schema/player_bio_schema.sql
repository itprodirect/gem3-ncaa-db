-- Player bio / physicals dimension for NCAA + future pro data

CREATE TABLE IF NOT EXISTS dim_player_bio (
    global_player_id    TEXT PRIMARY KEY,  -- FK to dim_player_global
    full_name           TEXT,             -- convenience copy
    class_year          TEXT,             -- FR/SO/JR/SR/etc. (latest seen)
    height              TEXT,             -- raw text as scraped (e.g. 6-5)
    weight              TEXT,             -- raw text as scraped (e.g. 205)
    primary_position    TEXT,
    secondary_position  TEXT,
    -- future fields:
    birthdate           TEXT,
    hometown_city       TEXT,
    hometown_state      TEXT,
    hometown_country    TEXT,
    high_school         TEXT,
    previous_schools    TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);