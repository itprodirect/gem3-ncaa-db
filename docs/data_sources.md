## Data Sources & Roadmap

This project is designed to grow from an NCAA-only database into a full career graph that links college and pro outcomes.

For current and planned data layers (NCAA core, bio/age, context, and NBA integration), see:

- [Data sources & roadmap](docs/data_sources.md)

# Data Sources & Roadmap (NCAA → NBA Career Graph)

This document tracks what data we use now and what we plan to add as the project evolves from an NCAA-only database into a full _career graph_ from college → pro.

The focus is:

- Start with **public, scrape-friendly data**
- Keep the schema **extensible** (NCAA today, NBA/pro later)
- Prioritize fields that matter for **scouting, NIL, and long-term outcomes** (age, size, context, archetype)

---

## 1. Summary Table

| Layer               | Source(s)                            | Status  | Notes                                                                                |
| ------------------- | ------------------------------------ | ------- | ------------------------------------------------------------------------------------ |
| NCAA core stats     | Sports-Reference CBB (public pages)  | ACTIVE  | Teams, rosters, per-game + season stats, box scores for D-I.                         |
| NCAA bio + age      | Sports-Reference CBB, RealGM         | PLANNED | Height, weight, position, DOB, high school, hometown, prior schools.                 |
| NCAA context        | Sports-Reference CBB, NCAA/RealGM    | PLANNED | Team/offensive/defensive efficiency, pace, opponent strength.                        |
| Recruiting pedigree | 247Sports, On3, Rivals (public info) | BACKLOG | Star rating, class rank, composite tier. Used carefully re: TOS.                     |
| NBA core stats      | Basketball-Reference (NBA/ABA)       | PLANNED | Per-season and advanced stats for NBA players; mapping players back to NCAA careers. |
| Other pro leagues   | RealGM, Basketball-Reference (G/L)   | BACKLOG | G League, EuroLeague, overseas – later “pro outcome” expansion.                      |

---

## 2. NCAA Core (Current Pipeline)

**Goal:** Reliable, repeatable ingestion of Division I men’s basketball data for 2021+ seasons.

**Primary source:**

- Sports-Reference College Basketball (public HTML pages).

**What we pull now (MVP):**

- **Teams & conferences**
- **Rosters**:
  - Player name
  - Class (FR/SO/JR/SR/etc.)
  - Basic roster info directly visible on team pages
- **Box score / per-game stats**:
  - Minutes, points, rebounds, assists, steals, blocks, turnovers, fouls
  - Shooting splits (FG, 3P, FT attempts and makes)
- **Season aggregates**:
  - Per-game averages
  - Simple totals by season

**Storage:**

- Loaded into the project’s SQLite database (under `ncaa-analytics/`).
- Used as the base for similarity search, scouting views, and dashboards.

This is the “spine” that everything else hooks into.

---

## 3. NCAA Bio & Age Layer (Planned)

**Goal:** Turn anonymous stat lines into **scouting profiles** by adding physicals and age.

**Planned fields:**

- Height, weight
- Primary/secondary position
- Dominant hand (where available)
- Birthdate
- Hometown / country
- High school / prep school
- Prior colleges / JUCO stops

**Planned sources:**

- Sports-Reference CBB player pages (height, weight, position, DOB where available).
- RealGM player pages (DOB, height, position, high school, birthplace for many players).

**Planned schema:**

- `dim_player_bio` (linked via internal `player_id`):
  - `player_id`
  - `global_player_id` (future proof: NCAA + NBA identity)
  - `full_name`
  - `birthdate`
  - `height_cm`, `weight_kg`
  - `primary_position`, `secondary_position`
  - `hometown_city`, `hometown_state`, `hometown_country`
  - `high_school`
  - `previous_schools`
  - `created_at`, `updated_at`

**Derived features (computed later):**

- Age at season start
- Age at each game
- Age relative to conference/position medians (z-scores)
- “Young for level” / “old for level” flags

This layer powers the age-weighted evaluation that is core to our scouting philosophy.

---

## 4. NCAA Context & Team Strength (Planned)

**Goal:** Put box score production into context. A 58% TS on high usage in the Big 12 ≠ the same line in a low-major.

**Planned fields (by team/season):**

- Offensive rating, defensive rating
- Pace (possessions per game)
- Strength index (simple normalized rank across D-I)
- Conference, division, level (high/mid/low major tags)

**Planned fields (by opponent):**

- Opponent conference and level
- Opponent defensive strength bucket (e.g., top-25, 26–100, 101+)

**Planned sources:**

- Sports-Reference CBB team pages for efficiency and pace.
- NCAA/RealGM where needed for cross-checks.

**Planned schema:**

- `dim_team_season`:
  - `team_id`, `season`
  - `conference`, `level_tag`
  - `off_eff`, `def_eff`, `pace`
  - `strength_index` (0–100 scaled)
- Join back into:
  - Player game logs and season summaries for “production vs context” metrics.

---

## 5. Recruiting & Pedigree (Backlog)

**Goal:** Capture “incoming expectation” to compare against actual development.

**Potential fields:**

- Star rating (e.g., 5★, 4★, 3★, unranked)
- National rank, position rank
- Composite tier (e.g., Tier 1: top-25, Tier 2: 26–100, etc.)

**Potential sources (public-facing pages only):**

- 247Sports, On3, Rivals.

**Notes:**

- This layer is **nice-to-have**, not required for early versions.
- Needs careful handling of sites’ terms of service and rate limits.
- Likely implemented first for a subset of players (e.g., SEC/ACC top prospects).

---

## 6. NBA Core (Planned Career Graph Layer)

**Goal:** Connect NCAA careers to NBA outcomes to build a **full career graph** and validate our proprietary metrics.

**Primary source:**

- Basketball-Reference NBA player pages (NBA/ABA historical data).

**Planned fields:**

- Per-season NBA stats:
  - Games, minutes, points, rebounds, assists, steals, blocks
  - Shooting efficiency (FG/3P/FT, TS%)
- Advanced metrics:
  - PER, WS/48, BPM, VORP (where available)
- Meta:
  - Team, league, season
  - Age
  - Role / outcome labels (derived later: rotation player, starter, All-Star, etc.)

**Planned schema (separate “pro” star schema):**

- `dim_player_global`:
  - `global_player_id` (PK)
  - `canonical_name`
  - `birthdate`
  - `height_cm`, `weight_kg`
  - `primary_position`
  - Links to NCAA and NBA IDs.
- `fact_nba_season`:
  - `global_player_id` (FK)
  - `season`
  - `age`
  - `team`, `league`
  - Core per-game & advanced stats.

**Linkage logic (NCAA → NBA):**

- High-confidence matches:
  - Exact match on `name + birthdate` between CBB SR and NBA Basketball-Reference.
- Secondary checks:
  - College name, height, position, overlapping years.
- Edge cases handled manually (for now).

This unlocks long-term questions like:

- “Which college archetypes age into real NBA roles?”
- “What does a 19-year-old with X profile typically become by age 25?”

---

## 7. Design Principles

1. **Public-first:**  
   Start with data that is clearly public and scrape-friendly. No paid APIs or TOS gray areas in v0.

2. **Extensible schema:**  
   Keep NCAA and NBA in separate but linkable schemas via a `global_player_id`.

3. **Age & context as first-class citizens:**  
   Age, league strength, and role are core features, not afterthoughts.

4. **Incremental ingestion:**  
   Start with a few conferences/seasons and a small NBA subset, then widen coverage once the pipeline is stable.

5. **Transparent provenance:**  
   Every table that comes from an external site should be traceable back to a specific source, date, and script.

This document will evolve as we add new layers, sources, and leagues.
