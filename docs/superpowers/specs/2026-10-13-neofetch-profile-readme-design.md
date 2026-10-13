# Neofetch-style GitHub profile README — design

## Goal

A profile README for `github.com/Manushpm8` that looks like a `neofetch` screen: an ASCII
portrait of the profile photo on the left, system-style info lines on the right. It refreshes
daily through GitHub Actions and has light and dark variants that follow the viewer's theme.

## Decisions already made

- Identity: Manush Murali, AI Engineer at NVIDIA, Sunnyvale CA, focus on structured and graph
  foundation models.
- Left side is ASCII art generated from the GitHub avatar.
- Stats cover public personal repos only. No personal access token and no repo secret; the
  workflow's built-in `GITHUB_TOKEN` is enough.
- No uptime line. Contact line shows GitHub and LinkedIn; no email.
- Output is generated SVG, not markdown, because markdown cannot colour or align columns.

## Repository layout (`Manushpm8/Manushpm8`, public)

```
README.md                  picture element switching dark_mode.svg / light_mode.svg
dark_mode.svg              generated
light_mode.svg             generated
config.toml                static profile content (role, location, focus, languages, links)
data/ascii.txt             portrait, generated once, committed
data/stats.json            last good stats, committed by the workflow
data/loc_cache.json        per-repo LOC cache keyed by repo and pushed_at
src/profile_card/          package: stats.py, render.py, theme.py, ascii_art.py, cli.py
tests/
.github/workflows/update.yml
pyproject.toml
```

## Components

- `ascii_art.py`: converts an image to ASCII (luminance ramp, aspect-corrected for monospace
  cells, fixed column width). Run once by hand; its output is committed. Pillow is a dev
  dependency only.
- `stats.py`: fetches repos, stars, commit contributions, 30-day daily activity, and lines of
  code. Pure functions that take an injected HTTP session, so they test without the network.
  - Repos and stars: GraphQL, owned non-fork public repos, stars summed over them.
  - Commits: GraphQL `contributionsCollection` per calendar year since account creation,
    summed, plus the last 30 daily counts for the sparkline.
  - Lines of code: REST `stats/contributors` per owned public repo, additions and deletions
    for the user. Cached by `pushed_at` so unchanged repos are not re-queried. A 202
    (stats still computing) keeps the cached value.
  - Any failure keeps the previous `data/stats.json` value for that field and logs it. A
    failed run never writes blanks.
- `theme.py`: two palettes, light and dark, as plain dicts.
- `render.py`: builds the SVG from config, stats, ASCII and a theme. Escapes all text,
  aligns right-side columns by character width, and writes both variants.
- `cli.py`: `python -m profile_card refresh` (stats then render), `render` (render only),
  `ascii <image>` (portrait generation).

## What the card shows

```
manush@github
-------------
OS:         macOS
Role:       AI Engineer @ NVIDIA
Location:   Sunnyvale, CA
Focus:      Structured & graph foundation models
Languages:  Python, ...
Stack:      tables -> entities -> relations -> embeddings -> predictions
Device:     NVIDIA AI Engineer | compute capability: human+GPU
Repos: N   Stars: N   Commits: N   LOC: N (+adds / -dels)
Activity:   30-day sparkline of daily commits
Run:        epoch <day of year> | loss <deterministic decay> | curiosity up
Query:      MATCH (me)-[:BUILDS]->(models) RETURN graphs, tables, structure;
Contact:    GitHub | LinkedIn
```

Visual treatment: a faint node-and-edge graph motif behind the portrait, a blinking cursor
after the final line, a small colour-swatch row like neofetch. Animation is CSS inside the
SVG, which GitHub serves intact when the SVG is loaded as an image. The motif and cursor
animations honour `prefers-reduced-motion`.

Languages are listed in `config.toml` and are not computed.

## Light and dark mode

`README.md` uses `<picture>` with a `prefers-color-scheme: dark` source pointing at
`dark_mode.svg` and a default `<img>` of `light_mode.svg`. Both files are generated from the
same data, differing only by palette.

## Workflow (`update.yml`)

- Triggers: daily cron, `workflow_dispatch`, and push to `main` touching `config.toml` or
  `src/`.
- `permissions: contents: write`, nothing else.
- Steps: checkout, set up Python, install, run `refresh`, commit `dark_mode.svg`,
  `light_mode.svg` and `data/` only if `git diff` is non-empty, using the Actions bot
  identity. Actions are pinned to full commit SHAs.
- A concurrency group prevents overlapping runs.

## Error handling

- Network or API errors per field fall back to the last committed value.
- Missing `data/stats.json` on first run renders `n/a` for stats, not a crash.
- Rendering is deterministic for the same inputs, so unchanged days produce no commit.

## Testing

pytest, minimal and meaningful:
- Stats parsing from recorded GraphQL and REST fixtures, including the 202 case and a
  fork-exclusion case.
- Fallback: a failing fetch leaves the previous value in `stats.json`.
- LOC cache: unchanged `pushed_at` makes no REST call.
- Render: both variants produce valid XML, text is escaped, columns align, light and dark
  differ only in colour values, and rendering twice gives identical bytes.
- ASCII: output has the configured width and height for a fixture image.

## Out of scope

NVIDIA-org or private repo stats, a token or secrets, a research feed, repo dependency graph
statistics, and any auto-synced "now learning" line.

## Contact links

GitHub `https://github.com/Manushpm8` and LinkedIn `https://www.linkedin.com/in/manushmurali`, both in `config.toml`.
