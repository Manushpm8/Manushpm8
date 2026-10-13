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
