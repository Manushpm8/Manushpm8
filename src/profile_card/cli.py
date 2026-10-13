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


def _today():
    return datetime.now(timezone.utc).date()


def _render(root, today):
    config = load_config(root / "config.toml")
    stats = load_stats(root / "data" / "stats.json")
    art = _read_art(root / "data" / "ascii.txt")
    for theme, out_name in ((DARK, "dark_mode.svg"), (LIGHT, "light_mode.svg")):
        (root / out_name).write_text(render_svg(config, stats, art, theme, today))


def _session(token):
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-card",
        }
    )
    return session


def _refresh(root):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for refresh")
    config = load_config(root / "config.toml")
    today = _today()
    stats, cache = refresh(
        _session(token),
        config.username,
        today,
        load_stats(root / "data" / "stats.json"),
        load_cache(root / "data" / "loc_cache.json"),
    )
    save_stats(root / "data" / "stats.json", stats)
    save_cache(root / "data" / "loc_cache.json", cache)
    _render(root, today)


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
        _render(args.root, _today())
    elif args.command == "refresh":
        _refresh(args.root)
    else:
        from .ascii_art import write_portrait

        write_portrait(args.image, args.root / "data")
    return 0
