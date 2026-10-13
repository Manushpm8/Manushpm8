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
        rest={
            URL.format("a"): FakeResponse(status_code=202),
            URL.format("b"): FakeResponse(status_code=202),
        }
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
                "repositories": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [],
                },
            }
        }
    }
    commits = {"data": {"user": {"contributionsCollection": {"totalCommitContributions": 0}}}}
    daily = {
        "data": {
            "user": {"contributionsCollection": {"contributionCalendar": {"weeks": []}}}
        }
    }
    session = FakeSession(graphql=[account, daily, commits])
    stats, _ = refresh(session, "me", date(2026, 3, 1), Stats(), {})
    assert (stats.repos, stats.stars, stats.commits, stats.additions, stats.deletions) == (
        0,
        0,
        0,
        0,
        0,
    )
    assert stats.daily == (0,) * 30


def test_stats_round_trip_and_corrupt_file_degrades_to_defaults(tmp_path):
    path = tmp_path / "stats.json"
    original = Stats(repos=1, stars=2, commits=3, additions=4, deletions=5, daily=(6,) * 30)
    save_stats(path, original)
    assert load_stats(path) == original
    path.write_text("{not json")
    assert load_stats(path) == Stats()
    assert load_stats(tmp_path / "missing.json") == Stats()
