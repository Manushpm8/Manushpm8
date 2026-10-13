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
