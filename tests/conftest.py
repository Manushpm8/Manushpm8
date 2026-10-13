import pytest

import profile_card.stats as stats_module

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


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr(stats_module, "RETRY_DELAY", 0)
