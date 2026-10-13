# Neofetch Profile README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `Manushpm8/Manushpm8`, a neofetch-style GitHub profile README rendered as light and dark SVGs, with an ASCII portrait of the avatar and public-repo stats refreshed daily by GitHub Actions.

**Architecture:** A small Python package (`profile_card`) with four pure units: config loader, stats fetcher (injected HTTP session, per-field fallback to last good value), ASCII converter, and SVG renderer. A CLI wires them together; a scheduled workflow runs `refresh` and commits changed outputs. `README.md` switches SVGs with `<picture>`.

**Tech Stack:** Python 3.11+, `requests`, Pillow (dev only, portrait generation), pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-13-neofetch-profile-readme-design.md`

## Global Constraints

- Public personal repos only: owned, non-fork, public. No personal access token, no repo secret; the workflow uses the built-in `GITHUB_TOKEN` with `permissions: contents: write`.
- Identity: handle `manush`, GitHub `Manushpm8`, role `AI Engineer @ NVIDIA`, location `Sunnyvale, CA`, focus `Structured & graph foundation models`, OS `macOS`, languages `Python`.
- Contact: `https://github.com/Manushpm8` and `https://www.linkedin.com/in/manushmurali`. No email. No uptime line.
- Output files: `light_mode.svg`, `dark_mode.svg`; README uses `<picture>` with `prefers-color-scheme: dark`.
- Rendering is deterministic: same inputs, byte-identical output.
- Animations are CSS inside the SVG and are disabled under `prefers-reduced-motion: reduce`.
- Commit identity for this repo: `Manush Murali <91221099+Manushpm8@users.noreply.github.com>` (already set locally). Commit messages end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Code style: no inline comments, no docstring noise, minimal parametrized tests that fail before the fix.
- Stage files by explicit path. Never `git add -A`.
- Nothing is pushed or published without the user's explicit yes (Task 7).

## Review Focus

- Account with zero public repos or a brand-new account: totals are 0, no division by zero, flat sparkline renders.
- Stats endpoint returns HTTP 202 on first LOC run: partial total, no crash, retried next day.
- GraphQL returns HTTP 200 with an `errors` body: treated as a failure, previous values kept.
- `data/stats.json` missing or corrupt: renders `n/a`, no crash.
- Text containing XML-special characters (the focus line contains `&`) and very large numbers: output stays valid XML and the canvas widens instead of clipping.

---

### Task 1: Scaffold and config loader

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `config.toml`, `src/profile_card/__init__.py`, `src/profile_card/config.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `Config` frozen dataclass with fields `handle, username, host, os, role, location, focus: str`, `languages: tuple[str, ...]`, `github_url, linkedin_url: str`; `load_config(path: Path) -> Config`.

- [ ] **Step 1: Create the environment and scaffold**

```bash
cd /Users/manushm/Documents/Projects/Manushpm8
python3 -m venv .venv
mkdir -p src/profile_card tests data
touch src/profile_card/__init__.py
```

`pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "profile-card"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["requests>=2.31"]

[project.optional-dependencies]
dev = ["pytest>=8", "pillow>=10"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["tests"]
testpaths = ["tests"]
```

`.gitignore`:
```
.venv/
__pycache__/
*.egg-info/
.pytest_cache/
.tmp/
```

`config.toml`:
```toml
handle = "manush"
username = "Manushpm8"
host = "github"
os = "macOS"
role = "AI Engineer @ NVIDIA"
location = "Sunnyvale, CA"
focus = "Structured & graph foundation models"
languages = ["Python"]
github_url = "https://github.com/Manushpm8"
linkedin_url = "https://www.linkedin.com/in/manushmurali"
```

Run: `.venv/bin/pip install -e ".[dev]"`

- [ ] **Step 2: Write the failing test**

`tests/test_config.py`:
```python
from profile_card.config import Config, load_config


def test_load_config_reads_every_field(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        'handle = "manush"\nusername = "Manushpm8"\nhost = "github"\nos = "macOS"\n'
        'role = "AI Engineer @ NVIDIA"\nlocation = "Sunnyvale, CA"\n'
        'focus = "Structured & graph foundation models"\nlanguages = ["Python", "SQL"]\n'
        'github_url = "https://github.com/Manushpm8"\n'
        'linkedin_url = "https://www.linkedin.com/in/manushmurali"\n'
    )
    config = load_config(path)
    assert config == Config(
        handle="manush",
        username="Manushpm8",
        host="github",
        os="macOS",
        role="AI Engineer @ NVIDIA",
        location="Sunnyvale, CA",
        focus="Structured & graph foundation models",
        languages=("Python", "SQL"),
        github_url="https://github.com/Manushpm8",
        linkedin_url="https://www.linkedin.com/in/manushmurali",
    )
```

- [ ] **Step 3: Run it to verify it fails**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: FAIL, `ModuleNotFoundError: profile_card.config`

- [ ] **Step 4: Implement**

`src/profile_card/config.py`:
```python
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    handle: str
    username: str
    host: str
    os: str
    role: str
    location: str
    focus: str
    languages: tuple[str, ...]
    github_url: str
    linkedin_url: str


def load_config(path: Path) -> Config:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    raw["languages"] = tuple(raw["languages"])
    return Config(**raw)
```

- [ ] **Step 5: Run it to verify it passes**

Run: `.venv/bin/pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore config.toml src/profile_card/__init__.py src/profile_card/config.py tests/test_config.py
git commit -m "Scaffold profile_card package and config loader

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: ASCII portrait

**Files:**
- Create: `src/profile_card/ascii_art.py`, `tests/test_ascii_art.py`, `data/ascii_dark.txt`, `data/ascii_light.txt` (generated)

**Interfaces:**
- Produces: `ASCII_COLUMNS = 70`; `image_to_ascii(image: PIL.Image.Image, columns: int, invert: bool) -> list[str]` returning lines of exactly `columns` characters; `write_portraits(image_path: Path, data_dir: Path) -> None` writing `ascii_dark.txt` (bright pixels dense) and `ascii_light.txt` (dark pixels dense).

- [ ] **Step 1: Write the failing tests**

`tests/test_ascii_art.py`:
```python
from PIL import Image

from profile_card.ascii_art import image_to_ascii


def half_black_half_white():
    image = Image.new("L", (40, 20), 0)
    image.paste(255, (20, 0, 40, 20))
    return image


def test_lines_have_requested_width_and_aspect_corrected_height():
    lines = image_to_ascii(half_black_half_white(), columns=10, invert=False)
    assert len(lines) == 5
    assert {len(line) for line in lines} == {10}


def test_dark_variant_is_dense_where_bright_and_light_variant_is_inverse():
    dark = image_to_ascii(half_black_half_white(), columns=10, invert=False)[0]
    light = image_to_ascii(half_black_half_white(), columns=10, invert=True)[0]
    assert dark[0] == " " and dark[-1] == "@"
    assert light[0] == "@" and light[-1] == " "
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_ascii_art.py -v`
Expected: FAIL, `ModuleNotFoundError: profile_card.ascii_art`

- [ ] **Step 3: Implement**

`src/profile_card/ascii_art.py`:
```python
from pathlib import Path

from PIL import Image, ImageOps

RAMP = " .:-=+*#%@"
CELL_ASPECT = 0.5
ASCII_COLUMNS = 70


def image_to_ascii(image: Image.Image, columns: int, invert: bool) -> list[str]:
    rows = max(1, round(columns * image.height / image.width * CELL_ASPECT))
    gray = ImageOps.autocontrast(
        image.convert("L").resize((columns, rows), Image.Resampling.LANCZOS)
    )
    last = len(RAMP) - 1
    lines = []
    for y in range(rows):
        line = []
        for x in range(columns):
            level = gray.getpixel((x, y)) / 255
            if invert:
                level = 1 - level
            line.append(RAMP[round(level * last)])
        lines.append("".join(line))
    return lines


def write_portraits(image_path: Path, data_dir: Path) -> None:
    with Image.open(image_path) as image:
        for name, invert in (("ascii_dark.txt", False), ("ascii_light.txt", True)):
            lines = image_to_ascii(image, ASCII_COLUMNS, invert)
            (data_dir / name).write_text("\n".join(lines) + "\n")
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_ascii_art.py -v`
Expected: PASS

- [ ] **Step 5: Generate the real portrait from the avatar and inspect it**

```bash
curl -sL -o .tmp/avatar.png https://github.com/Manushpm8.png
.venv/bin/python -c "from pathlib import Path; from profile_card.ascii_art import write_portraits; write_portraits(Path('.tmp/avatar.png'), Path('data'))"
cat data/ascii_dark.txt
```
Expected: a recognisable face-shaped portrait, 70 columns wide. If the result is muddy, tune only `RAMP` and rerun; do not hand-edit the output files. (`.tmp/` is git-ignored; create it with `mkdir -p .tmp` first.)

- [ ] **Step 6: Commit**

```bash
git add src/profile_card/ascii_art.py tests/test_ascii_art.py data/ascii_dark.txt data/ascii_light.txt
git commit -m "Add ASCII portrait generator and generated portraits

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Stats fetching (GraphQL)

**Files:**
- Create: `src/profile_card/stats.py`, `tests/fakes.py`, `tests/test_stats_graphql.py`

**Interfaces:**
- Produces in `stats.py`:
  - `StatsError(Exception)`
  - `Repo(name: str, stars: int, pushed_at: str)`, `Account(created: date, repos: tuple[Repo, ...])` (frozen dataclasses)
  - `fetch_account(session, user: str) -> Account`
  - `fetch_commit_total(session, user: str, created: date, today: date) -> int`
  - `fetch_daily(session, user: str, today: date) -> tuple[int, ...]` (length `DAILY_DAYS = 30`, oldest first)
- `session` is anything with `post(url, json, timeout)` and `get(url, timeout)` returning an object with `status_code`, `json()`, `raise_for_status()`.

- [ ] **Step 1: Write the test fakes and failing tests**

`tests/fakes.py`:
```python
import requests


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class FakeSession:
    def __init__(self, graphql=(), rest=None):
        self.graphql = list(graphql)
        self.rest = dict(rest or {})
        self.posts = []
        self.gets = []

    def post(self, url, json, timeout):
        self.posts.append(json["variables"])
        item = self.graphql.pop(0)
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, FakeResponse) else FakeResponse(item)

    def get(self, url, timeout):
        self.gets.append(url)
        item = self.rest[url]
        if isinstance(item, Exception):
            raise item
        return item
```

`tests/test_stats_graphql.py`:
```python
from datetime import date

import pytest

from fakes import FakeSession
from profile_card.stats import (
    Account,
    Repo,
    StatsError,
    fetch_account,
    fetch_commit_total,
    fetch_daily,
)


def account_page(nodes, has_next, cursor=None):
    return {
        "data": {
            "user": {
                "createdAt": "2024-06-10T12:00:00Z",
                "repositories": {
                    "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                    "nodes": nodes,
                },
            }
        }
    }


def node(name, stars):
    return {"name": name, "stargazerCount": stars, "pushedAt": "2026-01-01T00:00:00Z"}


def test_fetch_account_follows_pagination():
    session = FakeSession(
        graphql=[
            account_page([node("a", 1)], True, "c1"),
            account_page([node("b", 2)], False),
        ]
    )
    account = fetch_account(session, "me")
    assert account == Account(
        created=date(2024, 6, 10),
        repos=(
            Repo("a", 1, "2026-01-01T00:00:00Z"),
            Repo("b", 2, "2026-01-01T00:00:00Z"),
        ),
    )
    assert session.posts[1]["cursor"] == "c1"


def test_account_with_no_repositories_is_empty_not_an_error():
    session = FakeSession(graphql=[account_page([], False)])
    assert fetch_account(session, "me").repos == ()


def test_graphql_errors_in_a_200_response_raise():
    session = FakeSession(graphql=[{"errors": [{"message": "boom"}], "data": None}])
    with pytest.raises(StatsError):
        fetch_account(session, "me")


def test_unknown_user_raises():
    session = FakeSession(graphql=[{"data": {"user": None}}])
    with pytest.raises(StatsError):
        fetch_account(session, "ghost")


def commits(total):
    return {"data": {"user": {"contributionsCollection": {"totalCommitContributions": total}}}}


def test_commit_total_sums_one_query_per_calendar_year():
    session = FakeSession(graphql=[commits(10), commits(20), commits(5)])
    total = fetch_commit_total(session, "me", date(2024, 6, 10), date(2026, 3, 1))
    assert total == 35
    assert [p["from"] for p in session.posts] == [
        "2024-06-10T00:00:00Z",
        "2025-01-01T00:00:00Z",
        "2026-01-01T00:00:00Z",
    ]
    assert session.posts[-1]["to"] == "2026-03-01T23:59:59Z"


def test_daily_pads_missing_days_with_zero_and_is_oldest_first():
    days = [
        {"date": "2026-02-28", "contributionCount": 4},
        {"date": "2026-03-01", "contributionCount": 7},
    ]
    payload = {
        "data": {
            "user": {
                "contributionsCollection": {
                    "contributionCalendar": {"weeks": [{"contributionDays": days}]}
                }
            }
        }
    }
    daily = fetch_daily(FakeSession(graphql=[payload]), "me", date(2026, 3, 1))
    assert len(daily) == 30
    assert daily[-2:] == (4, 7)
    assert sum(daily) == 11
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_stats_graphql.py -v`
Expected: FAIL, `ModuleNotFoundError: profile_card.stats`

- [ ] **Step 3: Implement**

`src/profile_card/stats.py`:
```python
from dataclasses import dataclass
from datetime import date, timedelta

GRAPHQL_URL = "https://api.github.com/graphql"
TIMEOUT = 30
DAILY_DAYS = 30

ACCOUNT_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    createdAt
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      pageInfo { hasNextPage endCursor }
      nodes { name stargazerCount pushedAt }
    }
  }
}
"""

COMMITS_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) { totalCommitContributions }
  }
}
"""

DAILY_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


class StatsError(Exception):
    pass


@dataclass(frozen=True)
class Repo:
    name: str
    stars: int
    pushed_at: str


@dataclass(frozen=True)
class Account:
    created: date
    repos: tuple[Repo, ...]


def _graphql(session, query, variables):
    response = session.post(
        GRAPHQL_URL, json={"query": query, "variables": variables}, timeout=TIMEOUT
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        raise StatsError(str(body["errors"]))
    user = body["data"]["user"]
    if user is None:
        raise StatsError("user not found")
    return user


def fetch_account(session, user):
    repos = []
    cursor = None
    created = None
    while True:
        page = _graphql(session, ACCOUNT_QUERY, {"login": user, "cursor": cursor})
        created = date.fromisoformat(page["createdAt"][:10])
        listing = page["repositories"]
        repos.extend(
            Repo(n["name"], n["stargazerCount"], n["pushedAt"]) for n in listing["nodes"]
        )
        if not listing["pageInfo"]["hasNextPage"]:
            return Account(created=created, repos=tuple(repos))
        cursor = listing["pageInfo"]["endCursor"]


def _year_windows(created, today):
    for year in range(created.year, today.year + 1):
        yield max(created, date(year, 1, 1)), min(today, date(year, 12, 31))


def fetch_commit_total(session, user, created, today):
    total = 0
    for start, end in _year_windows(created, today):
        page = _graphql(
            session,
            COMMITS_QUERY,
            {"login": user, "from": f"{start}T00:00:00Z", "to": f"{end}T23:59:59Z"},
        )
        total += page["contributionsCollection"]["totalCommitContributions"]
    return total


def fetch_daily(session, user, today):
    start = today - timedelta(days=DAILY_DAYS - 1)
    page = _graphql(
        session,
        DAILY_QUERY,
        {"login": user, "from": f"{start}T00:00:00Z", "to": f"{today}T23:59:59Z"},
    )
    weeks = page["contributionsCollection"]["contributionCalendar"]["weeks"]
    counts = {
        day["date"]: day["contributionCount"]
        for week in weeks
        for day in week["contributionDays"]
    }
    return tuple(
        counts.get((start + timedelta(days=i)).isoformat(), 0) for i in range(DAILY_DAYS)
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest tests/test_stats_graphql.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/profile_card/stats.py tests/fakes.py tests/test_stats_graphql.py
git commit -m "Fetch account, commit totals and daily activity via GraphQL

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Lines of code, persistence and refresh fallback

**Files:**
- Modify: `src/profile_card/stats.py` (append; add imports)
- Create: `tests/test_stats_refresh.py`

**Interfaces:**
- Consumes: `fetch_account`, `fetch_commit_total`, `fetch_daily`, `Repo`, `StatsError`, `TIMEOUT` from Task 3.
- Produces in `stats.py`:
  - `Stats` frozen dataclass: `repos, stars, commits, additions, deletions: int | None = None`, `daily: tuple[int, ...] = ()`; `to_json() -> dict`, `Stats.from_json(data: dict) -> Stats`
  - `load_stats(path: Path) -> Stats` (default `Stats()` when missing or corrupt), `save_stats(path: Path, stats: Stats) -> None`
  - `load_cache(path: Path) -> dict`, `save_cache(path: Path, cache: dict) -> None`
  - `fetch_loc(session, user, repos, cache) -> tuple[int, int, dict]`
  - `refresh(session, user: str, today: date, previous: Stats, cache: dict) -> tuple[Stats, dict]`

- [ ] **Step 1: Write the failing tests**

`tests/test_stats_refresh.py`:
```python
from datetime import date

from fakes import FakeResponse, FakeSession
from profile_card.stats import (
    Repo,
    Stats,
    fetch_loc,
    load_stats,
    refresh,
    save_stats,
)

PUSHED = "2026-01-01T00:00:00Z"
URL = "https://api.github.com/repos/me/{}/stats/contributors"


def contributors(login, additions, deletions):
    return [
        {"author": {"login": login}, "weeks": [{"a": additions, "d": deletions, "c": 1}]},
        {"author": {"login": "someone-else"}, "weeks": [{"a": 999, "d": 999, "c": 1}]},
        {"author": None, "weeks": [{"a": 999, "d": 999, "c": 1}]},
    ]


def test_loc_counts_only_the_users_own_contributions():
    session = FakeSession(rest={URL.format("a"): FakeResponse(contributors("Me", 100, 40))})
    additions, deletions, cache = fetch_loc(session, "me", [Repo("a", 0, PUSHED)], {})
    assert (additions, deletions) == (100, 40)
    assert cache["a"] == {"pushed_at": PUSHED, "additions": 100, "deletions": 40}


def test_unchanged_repo_is_served_from_cache_without_a_request():
    cache = {"a": {"pushed_at": PUSHED, "additions": 7, "deletions": 3}}
    session = FakeSession()
    additions, deletions, _ = fetch_loc(session, "me", [Repo("a", 0, PUSHED)], cache)
    assert (additions, deletions) == (7, 3)
    assert session.gets == []


def test_pending_stats_keep_stale_cache_and_skip_uncached_repos():
    stale = {"a": {"pushed_at": "old", "additions": 7, "deletions": 3}}
    session = FakeSession(
        rest={URL.format("a"): FakeResponse(status_code=202), URL.format("b"): FakeResponse(status_code=202)}
    )
    repos = [Repo("a", 0, PUSHED), Repo("b", 0, PUSHED)]
    additions, deletions, cache = fetch_loc(session, "me", repos, stale)
    assert (additions, deletions) == (7, 3)
    assert cache["a"]["pushed_at"] == "old"
    assert "b" not in cache


def test_no_content_response_counts_as_zero():
    session = FakeSession(rest={URL.format("a"): FakeResponse(status_code=204)})
    assert fetch_loc(session, "me", [Repo("a", 0, PUSHED)], {})[:2] == (0, 0)


def test_removed_repos_leave_the_cache():
    cache = {"gone": {"pushed_at": PUSHED, "additions": 1, "deletions": 1}}
    _, _, updated = fetch_loc(FakeSession(), "me", [], cache)
    assert updated == {}


def test_failed_refresh_keeps_every_previous_value():
    previous = Stats(repos=3, stars=9, commits=100, additions=50, deletions=20, daily=(1,) * 30)
    error = {"errors": [{"message": "rate limited"}], "data": None}
    session = FakeSession(graphql=[error, error])
    stats, cache = refresh(session, "me", date(2026, 3, 1), previous, {"a": {}})
    assert stats == previous
    assert cache == {"a": {}}


def test_brand_new_account_refreshes_to_zeroes_with_a_flat_sparkline():
    account = {
        "data": {
            "user": {
                "createdAt": "2026-03-01T00:00:00Z",
                "repositories": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": []},
            }
        }
    }
    commits = {"data": {"user": {"contributionsCollection": {"totalCommitContributions": 0}}}}
    daily = {
        "data": {
            "user": {
                "contributionsCollection": {"contributionCalendar": {"weeks": []}}
            }
        }
    }
    session = FakeSession(graphql=[account, daily, commits])
    stats, _ = refresh(session, "me", date(2026, 3, 1), Stats(), {})
    assert (stats.repos, stats.stars, stats.commits, stats.additions, stats.deletions) == (0, 0, 0, 0, 0)
    assert stats.daily == (0,) * 30


def test_stats_round_trip_and_corrupt_file_degrades_to_defaults(tmp_path):
    path = tmp_path / "stats.json"
    original = Stats(repos=1, stars=2, commits=3, additions=4, deletions=5, daily=(6,) * 30)
    save_stats(path, original)
    assert load_stats(path) == original
    path.write_text("{not json")
    assert load_stats(path) == Stats()
    assert load_stats(tmp_path / "missing.json") == Stats()
```

The order of GraphQL responses in the brand-new-account test follows the call order fixed in the implementation below: account, then daily, then commits.

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_stats_refresh.py -v`
Expected: FAIL, `ImportError: cannot import name 'fetch_loc'`

- [ ] **Step 3: Implement**

At the top of `src/profile_card/stats.py` replace the imports with:
```python
import json
import sys
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path

import requests
```

Append to `src/profile_card/stats.py`:
```python
REST_ROOT = "https://api.github.com"
FETCH_ERRORS = (requests.RequestException, StatsError, KeyError, TypeError, ValueError)


@dataclass(frozen=True)
class Stats:
    repos: int | None = None
    stars: int | None = None
    commits: int | None = None
    additions: int | None = None
    deletions: int | None = None
    daily: tuple[int, ...] = ()

    def to_json(self):
        return {
            "repos": self.repos,
            "stars": self.stars,
            "commits": self.commits,
            "additions": self.additions,
            "deletions": self.deletions,
            "daily": list(self.daily),
        }

    @classmethod
    def from_json(cls, data):
        return cls(
            repos=data["repos"],
            stars=data["stars"],
            commits=data["commits"],
            additions=data["additions"],
            deletions=data["deletions"],
            daily=tuple(data["daily"]),
        )


def load_stats(path):
    try:
        return Stats.from_json(json.loads(path.read_text()))
    except (OSError, ValueError, KeyError, TypeError):
        return Stats()


def save_stats(path, stats):
    path.write_text(json.dumps(stats.to_json(), indent=2, sort_keys=True) + "\n")


def load_cache(path):
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_cache(path, cache):
    path.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")


def _repo_loc(session, user, repo):
    response = session.get(
        f"{REST_ROOT}/repos/{user}/{repo.name}/stats/contributors", timeout=TIMEOUT
    )
    if response.status_code == 202:
        return None
    response.raise_for_status()
    contributors = [] if response.status_code == 204 else response.json() or []
    additions = deletions = 0
    for contributor in contributors:
        login = (contributor.get("author") or {}).get("login", "")
        if login.lower() != user.lower():
            continue
        for week in contributor["weeks"]:
            additions += week["a"]
            deletions += week["d"]
    return {"pushed_at": repo.pushed_at, "additions": additions, "deletions": deletions}


def fetch_loc(session, user, repos, cache):
    updated = {}
    additions = deletions = 0
    for repo in repos:
        entry = cache.get(repo.name)
        if not entry or entry["pushed_at"] != repo.pushed_at:
            entry = _repo_loc(session, user, repo) or entry
        if not entry:
            continue
        updated[repo.name] = entry
        additions += entry["additions"]
        deletions += entry["deletions"]
    return additions, deletions, updated


def _attempt(label, action, fallback):
    try:
        return action()
    except FETCH_ERRORS as error:
        print(f"{label}: keeping previous value ({error})", file=sys.stderr)
        return fallback


def refresh(session, user, today, previous, cache):
    account = _attempt("account", lambda: fetch_account(session, user), None)
    daily = _attempt("daily", lambda: fetch_daily(session, user, today), previous.daily)
    if account is None:
        return replace(previous, daily=daily), cache
    commits = _attempt(
        "commits",
        lambda: fetch_commit_total(session, user, account.created, today),
        previous.commits,
    )
    additions, deletions, updated = _attempt(
        "loc",
        lambda: fetch_loc(session, user, account.repos, cache),
        (previous.additions, previous.deletions, cache),
    )
    stats = Stats(
        repos=len(account.repos),
        stars=sum(repo.stars for repo in account.repos),
        commits=commits,
        additions=additions,
        deletions=deletions,
        daily=daily,
    )
    return stats, updated
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest -v`
Expected: PASS (all tests in Tasks 1 to 4)

- [ ] **Step 5: Commit**

```bash
git add src/profile_card/stats.py tests/test_stats_refresh.py
git commit -m "Add LOC stats, persistence and per-field refresh fallback

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Theme and SVG renderer

**Files:**
- Create: `src/profile_card/theme.py`, `src/profile_card/render.py`, `tests/conftest.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: `Config` (Task 1), `Stats` (Task 4).
- Produces: `Theme` frozen dataclass (`background, foreground, key, dim, art, motif, accent: str`, `swatches: tuple[str, ...]`), constants `DARK`, `LIGHT` in `theme.py`; `render_svg(config: Config, stats: Stats, art: list[str], theme: Theme, today: date) -> str` in `render.py`.

- [ ] **Step 1: Write fixtures and failing tests**

`tests/conftest.py`:
```python
import pytest

from profile_card.config import Config
from profile_card.stats import Stats


@pytest.fixture
def config():
    return Config(
        handle="manush",
        username="Manushpm8",
        host="github",
        os="macOS",
        role="AI Engineer @ NVIDIA",
        location="Sunnyvale, CA",
        focus="Structured & graph foundation models",
        languages=("Python",),
        github_url="https://github.com/Manushpm8",
        linkedin_url="https://www.linkedin.com/in/manushmurali",
    )


@pytest.fixture
def stats():
    return Stats(
        repos=12, stars=930, commits=1500, additions=40000, deletions=12000, daily=tuple(range(30))
    )


@pytest.fixture
def art():
    return ["@" * 20, "#" * 20, "." * 20]
```

`tests/test_render.py`:
```python
import re
import xml.etree.ElementTree as ET
from datetime import date

from profile_card.render import render_svg
from profile_card.stats import Stats
from profile_card.theme import DARK, LIGHT

TODAY = date(2026, 10, 13)


def canvas_width(svg):
    return float(re.search(r'<svg [^>]*width="([\d.]+)"', svg).group(1))


def test_output_is_valid_xml_even_with_ampersand_in_config(config, stats, art):
    svg = render_svg(config, stats, art, DARK, TODAY)
    ET.fromstring(svg)
    assert "Structured &amp; graph foundation models" in svg


def test_value_column_is_aligned(config, stats, art):
    svg = render_svg(config, stats, art, DARK, TODAY)
    xs = set(re.findall(r'<tspan class="v" x="([\d.]+)"', svg))
    assert len(xs) == 1


def test_light_and_dark_differ_only_in_colour(config, stats, art):
    dark = render_svg(config, stats, art, DARK, TODAY)
    light = render_svg(config, stats, art, LIGHT, TODAY)
    strip = lambda svg: re.sub(r"#[0-9a-fA-F]{6}", "#", svg)
    assert dark != light
    assert strip(dark) == strip(light)


def test_rendering_is_deterministic(config, stats, art):
    assert render_svg(config, stats, art, DARK, TODAY) == render_svg(config, stats, art, DARK, TODAY)


def test_missing_stats_render_as_na(config, art):
    svg = render_svg(config, Stats(), art, DARK, TODAY)
    ET.fromstring(svg)
    assert svg.count("n/a") >= 4


def test_flat_sparkline_renders_when_every_day_is_zero(config, art):
    svg = render_svg(config, Stats(repos=0, stars=0, commits=0, additions=0, deletions=0, daily=(0,) * 30), art, DARK, TODAY)
    ET.fromstring(svg)
    assert svg.count('class="spark"') == 30


def test_canvas_widens_for_very_large_numbers(config, art, stats):
    huge = Stats(repos=1, stars=1, commits=1, additions=10**12, deletions=10**12, daily=(1,) * 30)
    assert canvas_width(render_svg(config, huge, art, DARK, TODAY)) > canvas_width(
        render_svg(config, stats, art, DARK, TODAY)
    )


def test_motion_is_disabled_for_reduced_motion_users(config, stats, art):
    assert "prefers-reduced-motion: reduce" in render_svg(config, stats, art, DARK, TODAY)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_render.py -v`
Expected: FAIL, `ModuleNotFoundError: profile_card.render`

- [ ] **Step 3: Implement the theme**

`src/profile_card/theme.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    background: str
    foreground: str
    key: str
    dim: str
    art: str
    motif: str
    accent: str
    swatches: tuple[str, ...]


DARK = Theme(
    background="#0d1117",
    foreground="#c9d1d9",
    key="#76b900",
    dim="#6e7681",
    art="#9be564",
    motif="#2f6f3e",
    accent="#58a6ff",
    swatches=("#f85149", "#ffa657", "#e3b341", "#76b900", "#39c5cf", "#58a6ff", "#bc8cff", "#c9d1d9"),
)

LIGHT = Theme(
    background="#ffffff",
    foreground="#24292f",
    key="#4c7a00",
    dim="#6e7781",
    art="#2f5d00",
    motif="#a7d8b0",
    accent="#0969da",
    swatches=("#cf222e", "#bc4c00", "#9a6700", "#4c7a00", "#1b7c83", "#0969da", "#8250df", "#24292f"),
)
```

- [ ] **Step 4: Implement the renderer**

`src/profile_card/render.py`:
```python
import math
import random
from datetime import date
from xml.sax.saxutils import escape

from .config import Config
from .stats import Stats
from .theme import Theme

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
ART_SIZE = 9
ART_CHAR = 5.4
ART_STEP = 10.5
INFO_SIZE = 12
INFO_CHAR = 7.2
INFO_STEP = 20
KEY_WIDTH = 96
PAD = 30
GAP = 30
SPARK_BARS = 30
SPARK_BAR_WIDTH = 4
SPARK_STEP = 6
SPARK_HEIGHT = 14
MOTIF_NODES = 18
MOTIF_SEED = 7

STACK = "tables → entities → relations → embeddings → predictions"
DEVICE = "NVIDIA AI Engineer | compute capability: human+GPU"
QUERY = "MATCH (me)-[:BUILDS]->(models) RETURN graphs, tables, structure;"


def _n(value):
    return f"{value:.1f}"


def _count(value):
    return "n/a" if value is None else f"{value:,}"


def _loc(stats):
    if stats.additions is None or stats.deletions is None:
        return "n/a"
    net = stats.additions - stats.deletions
    return f"{net:,} (+{stats.additions:,} / -{stats.deletions:,})"


def _link(url):
    return url.removeprefix("https://").removeprefix("www.")


def _info_rows(config, stats, today):
    epoch = today.timetuple().tm_yday
    loss = 1 / (1 + epoch / 20)
    return [
        ("OS", config.os),
        ("Role", config.role),
        ("Location", config.location),
        ("Focus", config.focus),
        ("Languages", ", ".join(config.languages)),
        ("Stack", STACK),
        ("Device", DEVICE),
        ("Repos", _count(stats.repos)),
        ("Stars", _count(stats.stars)),
        ("Commits", _count(stats.commits)),
        ("LOC", _loc(stats)),
        ("Activity", None),
        ("Run", f"epoch {epoch} | loss {loss:.3f} ↓ | curiosity ↑"),
        ("Query", QUERY),
        ("Contact", f"{_link(config.github_url)} | {_link(config.linkedin_url)}"),
    ]


def _style(theme):
    return f"""<style>
text{{font-family:{FONT};white-space:pre}}
.bg{{fill:{theme.background};stroke:{theme.dim};stroke-opacity:.35}}
.art{{font-size:{ART_SIZE}px;fill:{theme.art}}}
.h{{font-size:{INFO_SIZE}px;font-weight:700;fill:{theme.key}}}
.k{{font-size:{INFO_SIZE}px;font-weight:700;fill:{theme.key}}}
.v{{font-size:{INFO_SIZE}px;fill:{theme.foreground}}}
.d{{font-size:{INFO_SIZE}px;fill:{theme.dim}}}
.edge{{stroke:{theme.motif};stroke-width:1;opacity:.55}}
.node{{fill:{theme.motif};opacity:.8}}
.spark{{fill:{theme.accent}}}
.cursor{{fill:{theme.key}}}
.pulse{{animation:pulse 5s ease-in-out infinite}}
.cursor{{animation:blink 1.1s steps(1) infinite}}
@keyframes pulse{{0%,100%{{opacity:.25}}50%{{opacity:.8}}}}
@keyframes blink{{50%{{opacity:0}}}}
@media (prefers-reduced-motion: reduce){{.pulse,.cursor{{animation:none}}}}
</style>"""


def _motif(x0, y0, width, height):
    rng = random.Random(MOTIF_SEED)
    nodes = [(x0 + rng.uniform(0, width), y0 + rng.uniform(0, height)) for _ in range(MOTIF_NODES)]
    edges = set()
    for index, point in enumerate(nodes):
        others = sorted(
            (other for other in range(len(nodes)) if other != index),
            key=lambda other: math.dist(nodes[other], point),
        )
        edges.update(tuple(sorted((index, other))) for other in others[:2])
    parts = []
    for order, (a, b) in enumerate(sorted(edges)):
        (xa, ya), (xb, yb) = nodes[a], nodes[b]
        parts.append(
            f'<line class="edge pulse" style="animation-delay:{order % 5}s" '
            f'x1="{_n(xa)}" y1="{_n(ya)}" x2="{_n(xb)}" y2="{_n(yb)}"/>'
        )
    for x, y in nodes:
        parts.append(f'<circle class="node" cx="{_n(x)}" cy="{_n(y)}" r="2"/>')
    return "".join(parts)


def _art(art, x, y):
    lines = "".join(
        f'<tspan x="{_n(x)}" y="{_n(y + ART_STEP * index)}">{escape(line)}</tspan>'
        for index, line in enumerate(art)
    )
    return f'<text class="art" xml:space="preserve">{lines}</text>'


def _sparkline(values, x, baseline):
    peak = max(values, default=0) or 1
    bars = []
    for index, value in enumerate(values):
        height = 1 + (SPARK_HEIGHT - 1) * value / peak
        bars.append(
            f'<rect class="spark" x="{_n(x + index * SPARK_STEP)}" y="{_n(baseline - height)}" '
            f'width="{SPARK_BAR_WIDTH}" height="{_n(height)}"/>'
        )
    return "".join(bars)


def render_svg(config: Config, stats: Stats, art: list[str], theme: Theme, today: date) -> str:
    rows = _info_rows(config, stats, today)
    art_width = max((len(line) for line in art), default=0) * ART_CHAR
    art_height = len(art) * ART_STEP
    info_x = PAD + art_width + GAP
    value_x = info_x + KEY_WIDTH
    longest = max(len(value) for _, value in rows if value)
    spark_width = SPARK_BARS * SPARK_STEP
    width = value_x + max(longest * INFO_CHAR, spark_width) + PAD

    header = f"{config.handle}@{config.host}"
    lines = [("h", header), ("d", "-" * len(header))]
    y = PAD + INFO_SIZE
    info = []
    for kind, text in lines:
        info.append(f'<text class="{kind}" x="{_n(info_x)}" y="{_n(y)}">{escape(text)}</text>')
        y += INFO_STEP
    for key, value in rows:
        info.append(f'<text><tspan class="k" x="{_n(info_x)}" y="{_n(y)}">{escape(key)}:</tspan>')
        if value is None:
            info.append("</text>")
            info.append(_sparkline(stats.daily, value_x, y))
        else:
            info.append(f'<tspan class="v" x="{_n(value_x)}" y="{_n(y)}">{escape(value)}</tspan></text>')
        y += INFO_STEP
    for index, color in enumerate(theme.swatches):
        info.append(
            f'<rect x="{_n(info_x + index * 22)}" y="{_n(y - 10)}" width="18" height="12" rx="2" fill="{color}"/>'
        )
    y += INFO_STEP
    info.append(f'<text class="d" x="{_n(info_x)}" y="{_n(y)}">$</text>')
    info.append(
        f'<rect class="cursor" x="{_n(info_x + INFO_CHAR * 2)}" y="{_n(y - 11)}" width="8" height="14"/>'
    )

    height = PAD * 2 + max(art_height, y - PAD)
    title = escape(f"{config.handle}@{config.host}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_n(width)}" height="{_n(height)}" '
        f'viewBox="0 0 {_n(width)} {_n(height)}" role="img" aria-label="{title}">'
        f"<title>{title}</title>{_style(theme)}"
        f'<rect class="bg" x="0.5" y="0.5" width="{_n(width - 1)}" height="{_n(height - 1)}" rx="14"/>'
        f"{_motif(PAD, PAD, art_width, art_height)}"
        f"{_art(art, PAD, PAD + ART_SIZE)}"
        f'{"".join(info)}</svg>'
    )
```

- [ ] **Step 5: Run to verify pass**

Run: `.venv/bin/pytest -v`
Expected: PASS (everything so far). If the colour-only test fails, a hex colour leaked outside the theme; move it into `Theme`.

- [ ] **Step 6: Commit**

```bash
git add src/profile_card/theme.py src/profile_card/render.py tests/conftest.py tests/test_render.py
git commit -m "Add theme palettes and SVG renderer

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: CLI, README, workflow, and a real local render

**Files:**
- Create: `src/profile_card/cli.py`, `src/profile_card/__main__.py`, `tests/test_cli.py`, `README.md`, `.github/workflows/update.yml`
- Generated: `dark_mode.svg`, `light_mode.svg`, `data/stats.json`, `data/loc_cache.json`

**Interfaces:**
- Consumes: everything above.
- Produces: `main(argv: list[str] | None = None) -> int`. Commands: `render`, `refresh`, `ascii <image>`. Option `--root PATH` (before the command) selects the repo root, default current directory.

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
import shutil
from pathlib import Path

from profile_card.cli import main
from profile_card.stats import Stats, save_stats

REPO = Path(__file__).resolve().parent.parent


def test_render_writes_both_variants_from_committed_data_without_network(tmp_path):
    shutil.copy(REPO / "config.toml", tmp_path / "config.toml")
    data = tmp_path / "data"
    data.mkdir()
    for name in ("ascii_dark.txt", "ascii_light.txt"):
        shutil.copy(REPO / "data" / name, data / name)
    save_stats(data / "stats.json", Stats(repos=1, stars=2, commits=3, additions=4, deletions=1, daily=(1,) * 30))

    assert main(["--root", str(tmp_path), "render"]) == 0

    dark = (tmp_path / "dark_mode.svg").read_text()
    light = (tmp_path / "light_mode.svg").read_text()
    assert dark.startswith("<svg") and light.startswith("<svg")
    assert dark != light
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_cli.py -v`
Expected: FAIL, `ModuleNotFoundError: profile_card.cli`

- [ ] **Step 3: Implement**

`src/profile_card/cli.py`:
```python
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import load_config
from .render import render_svg
from .stats import load_cache, load_stats, refresh, save_cache, save_stats
from .theme import DARK, LIGHT


def _read_art(path):
    return path.read_text().splitlines() if path.exists() else []


def _render(root):
    config = load_config(root / "config.toml")
    stats = load_stats(root / "data" / "stats.json")
    today = datetime.now(timezone.utc).date()
    for theme, art_name, out_name in (
        (DARK, "ascii_dark.txt", "dark_mode.svg"),
        (LIGHT, "ascii_light.txt", "light_mode.svg"),
    ):
        art = _read_art(root / "data" / art_name)
        (root / out_name).write_text(render_svg(config, stats, art, theme, today))


def _refresh(root):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for refresh")
    config = load_config(root / "config.toml")
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-card",
        }
    )
    today = datetime.now(timezone.utc).date()
    stats, cache = refresh(
        session,
        config.username,
        today,
        load_stats(root / "data" / "stats.json"),
        load_cache(root / "data" / "loc_cache.json"),
    )
    save_stats(root / "data" / "stats.json", stats)
    save_cache(root / "data" / "loc_cache.json", cache)
    _render(root)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="profile_card")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("render")
    commands.add_parser("refresh")
    ascii_parser = commands.add_parser("ascii")
    ascii_parser.add_argument("image", type=Path)
    args = parser.parse_args(argv)

    if args.command == "render":
        _render(args.root)
    elif args.command == "refresh":
        _refresh(args.root)
    else:
        from .ascii_art import write_portraits

        write_portraits(args.image, args.root / "data")
    return 0
```

`src/profile_card/__main__.py`:
```python
import sys

from .cli import main

sys.exit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/pytest -v`
Expected: PASS (all tests)

- [ ] **Step 5: Real local refresh and render**

```bash
GITHUB_TOKEN=$(gh auth token) .venv/bin/python -m profile_card refresh
ls -la dark_mode.svg light_mode.svg data/
cat data/stats.json
```
Expected: both SVGs written; `stats.json` holds real counts (repos near 12). Locally the token can see your private contribution counts, so CI numbers can differ slightly; that is expected. A first LOC run may hit 202 for some repos; run `refresh` a second time after a minute and confirm LOC fills in.

- [ ] **Step 6: Look at the result and iterate on the design**

```bash
mkdir -p .tmp/preview && qlmanage -t -s 1400 -o .tmp/preview dark_mode.svg light_mode.svg >/dev/null 2>&1; ls .tmp/preview
```
Open both PNGs with the Read tool. Check: portrait is recognisable and aligned left of the info; text does not clip; the node motif is faint but visible; light mode is legible. If `qlmanage` does not render the SVG, open it in headless Chrome instead:
`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --screenshot=.tmp/preview/dark.png --window-size=1100,520 file://$PWD/dark_mode.svg`.
Adjust only constants in `render.py` or palettes in `theme.py`; rerun `render` and the tests until it looks good.

- [ ] **Step 7: Write the README**

`README.md`:
```markdown
<p align="center">
  <a href="https://github.com/Manushpm8">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="dark_mode.svg">
      <img alt="manush@github: AI Engineer at NVIDIA working on structured and graph foundation models" src="light_mode.svg">
    </picture>
  </a>
</p>

<p align="center">
  <a href="https://github.com/Manushpm8">GitHub</a> ·
  <a href="https://www.linkedin.com/in/manushmurali">LinkedIn</a>
</p>
```

- [ ] **Step 8: Write the workflow with pinned action SHAs**

Resolve the SHAs (avoid hammering the API; one call each):
```bash
gh api repos/actions/checkout/git/ref/tags/v4.2.2 --jq .object.sha
gh api repos/actions/setup-python/git/ref/tags/v5.6.0 --jq .object.sha
```
If either returns an annotated tag (`.object.type == "tag"`), dereference with `gh api repos/<repo>/git/tags/<sha> --jq .object.sha`.

`.github/workflows/update.yml` (replace `<CHECKOUT_SHA>` and `<SETUP_PYTHON_SHA>` with the resolved values):
```yaml
name: update-profile

on:
  schedule:
    - cron: "17 6 * * *"
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - config.toml
      - src/**
      - pyproject.toml

permissions:
  contents: write

concurrency:
  group: update-profile
  cancel-in-progress: false

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<CHECKOUT_SHA> # v4.2.2
      - uses: actions/setup-python@<SETUP_PYTHON_SHA> # v5.6.0
        with:
          python-version: "3.12"
      - run: pip install .
      - run: python -m profile_card refresh
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - name: Commit changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add dark_mode.svg light_mode.svg data/stats.json data/loc_cache.json
          if git diff --cached --quiet; then exit 0; fi
          git commit -m "Refresh profile stats"
          git push
```
Note: the `Run` line contains the day of year, so the SVGs change daily; that daily commit also keeps the scheduled workflow from being auto-disabled after 60 days of repo inactivity.

- [ ] **Step 9: Commit**

```bash
git add src/profile_card/cli.py src/profile_card/__main__.py tests/test_cli.py README.md .github/workflows/update.yml dark_mode.svg light_mode.svg data/stats.json data/loc_cache.json
git commit -m "Add CLI, README, daily workflow and first generated render

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Review gate and publish (needs the user's explicit yes)

**Files:** none new.

- [ ] **Step 1: Run the full suite and a clean-install check**

```bash
.venv/bin/pytest -q
python3 -m venv .tmp/clean && .tmp/clean/bin/pip install -q . && .tmp/clean/bin/python -m profile_card --root . render && git status --short
```
Expected: tests pass; the clean install (no dev extras) can render; `git status` shows no unexpected changes.

- [ ] **Step 2: Codex review loop**

```bash
codex exec -m gpt-5.6-sol -s read-only --skip-git-repo-check "Review the repo in $PWD (src/profile_card, tests, .github/workflows/update.yml, rendered SVGs) against docs/superpowers/specs/2026-10-13-neofetch-profile-readme-design.md. Report concrete bugs and visual or robustness problems only, ranked, with file:line. Say APPROVED if there are none."
```
Measure each finding before acting (some will be wrong), fix real ones with a failing test first, commit, and rerun until a round is clean. Run each round in the foreground with a bounded prompt; do not let it edit files.

- [ ] **Step 3: Show the user the rendered previews and ask for approval to publish**

Present both preview PNGs and the Codex verdict. Do not continue without an explicit yes.

- [ ] **Step 4: Publish (only after the yes)**

```bash
gh repo create Manushpm8/Manushpm8 --public --source=. --remote=origin --description "Profile README"
git branch -M main
git push -u origin main
gh workflow run update-profile.yml
gh run watch
```
Then open `https://github.com/Manushpm8`, confirm the card renders in light and dark, and confirm the workflow run commits (or cleanly no-ops).
