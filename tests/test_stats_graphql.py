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
