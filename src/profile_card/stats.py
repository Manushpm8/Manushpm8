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
