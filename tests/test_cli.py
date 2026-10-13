import shutil
import re
from datetime import date
from pathlib import Path

from profile_card import cli
from profile_card.cli import main
from profile_card.stats import Stats, save_stats

REPO = Path(__file__).resolve().parent.parent


def prepare(tmp_path):
    shutil.copy(REPO / "config.toml", tmp_path / "config.toml")
    data = tmp_path / "data"
    data.mkdir()
    shutil.copy(REPO / "data" / "ascii.txt", data / "ascii.txt")
    save_stats(
        data / "stats.json",
        Stats(repos=1, stars=2, commits=3, additions=4, deletions=1, daily=(1,) * 30),
    )


def test_render_writes_both_variants_from_committed_data_without_network(tmp_path):
    prepare(tmp_path)

    assert main(["--root", str(tmp_path), "render"]) == 0

    dark = (tmp_path / "dark_mode.svg").read_text()
    light = (tmp_path / "light_mode.svg").read_text()
    assert dark.startswith("<svg") and light.startswith("<svg")
    assert dark != light


def test_both_variants_are_rendered_for_the_same_date(tmp_path, monkeypatch):
    prepare(tmp_path)
    dates = iter([date(2026, 1, 1), date(2026, 1, 2)])
    monkeypatch.setattr(cli, "_today", lambda: next(dates))

    main(["--root", str(tmp_path), "render"])

    strip = lambda svg: re.sub(r"#[0-9a-fA-F]{6}", "#", svg)
    dark = (tmp_path / "dark_mode.svg").read_text()
    light = (tmp_path / "light_mode.svg").read_text()
    assert strip(dark) == strip(light)
