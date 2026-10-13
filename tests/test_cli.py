import shutil
from pathlib import Path

from profile_card.cli import main
from profile_card.stats import Stats, save_stats

REPO = Path(__file__).resolve().parent.parent


def test_render_writes_both_variants_from_committed_data_without_network(tmp_path):
    shutil.copy(REPO / "config.toml", tmp_path / "config.toml")
    data = tmp_path / "data"
    data.mkdir()
    shutil.copy(REPO / "data" / "ascii.txt", data / "ascii.txt")
    save_stats(
        data / "stats.json",
        Stats(repos=1, stars=2, commits=3, additions=4, deletions=1, daily=(1,) * 30),
    )

    assert main(["--root", str(tmp_path), "render"]) == 0

    dark = (tmp_path / "dark_mode.svg").read_text()
    light = (tmp_path / "light_mode.svg").read_text()
    assert dark.startswith("<svg") and light.startswith("<svg")
    assert dark != light
