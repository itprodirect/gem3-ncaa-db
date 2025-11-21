# External Data (Manual Downloads)

This folder is for **manually downloaded** datasets that are not scraped directly
by the NCAA pipeline, starting with NBA / pro data.

## NBA (Basketball-Reference)

Expected location for first prototype:

- `data_external/nba/bref_players_2023_24.csv`

You can export this from Basketball-Reference (or similar public source) using
their CSV download button, then point the linker script at it.

These files are **local-only** inputs and are not meant to be committed to Git.
(If we ever need to, we will add explicit patterns to `.gitignore`.)
