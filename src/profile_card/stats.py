import json
import sys
import time
from dataclasses import dataclass, replace
from datetime import date, timedelta

import requests

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


REST_ROOT = "https://api.github.com"
RETRY_ATTEMPTS = 3
RETRY_DELAY = 3
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
    url = f"{REST_ROOT}/repos/{user}/{repo.name}/stats/contributors"
    for attempt in range(RETRY_ATTEMPTS):
        response = session.get(url, timeout=TIMEOUT)
        if response.status_code != 202:
            break
        if attempt < RETRY_ATTEMPTS - 1:
            time.sleep(RETRY_DELAY)
    else:
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
        print(f"::warning title=profile-card::{label}: keeping previous value ({error})", file=sys.stderr)
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
