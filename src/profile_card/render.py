import math
import random
from datetime import date
from xml.sax.saxutils import escape

from .config import Config
from .stats import Stats
from .theme import Theme

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
ART_SIZE = 9
ART_CHAR = 5.4
ART_STEP = 10.5
INFO_SIZE = 12
INFO_CHAR = 7.2
INFO_STEP = 20
KEY_WIDTH = 96
PAD = 30
GAP = 30
SPARK_BARS = 30
SPARK_BAR_WIDTH = 4
SPARK_STEP = 6
SPARK_HEIGHT = 14
MOTIF_NODES = 18
MOTIF_SEED = 7

STACK = "tables → entities → relations → embeddings → predictions"
DEVICE = "NVIDIA AI Engineer | compute capability: human+GPU"
QUERY = "MATCH (me)-[:BUILDS]->(models) RETURN graphs, tables, structure;"


def _n(value):
    return f"{value:.1f}"


def _count(value):
    return "n/a" if value is None else f"{value:,}"


def _loc(stats):
    if stats.additions is None or stats.deletions is None:
        return "n/a"
    net = stats.additions - stats.deletions
    return f"{net:,} (+{stats.additions:,} / -{stats.deletions:,})"


def _link(url):
    return url.removeprefix("https://").removeprefix("www.")


def _info_rows(config, stats, today):
    epoch = today.timetuple().tm_yday
    loss = 1 / (1 + epoch / 20)
    return [
        ("OS", config.os),
        ("Role", config.role),
        ("Location", config.location),
        ("Focus", config.focus),
        ("Languages", ", ".join(config.languages)),
        ("Stack", STACK),
        ("Device", DEVICE),
        ("Repos", _count(stats.repos)),
        ("Stars", _count(stats.stars)),
        ("Commits", _count(stats.commits)),
        ("LOC", _loc(stats)),
        ("Activity", None),
        ("Run", f"epoch {epoch} | loss {loss:.3f} ↓ | curiosity ↑"),
        ("Query", QUERY),
        ("Contact", f"{_link(config.github_url)} | {_link(config.linkedin_url)}"),
    ]


def _style(theme):
    return f"""<style>
text{{font-family:{FONT};white-space:pre}}
.bg{{fill:{theme.background};stroke:{theme.dim};stroke-opacity:.35}}
.art{{font-size:{ART_SIZE}px;fill:{theme.art}}}
.h{{font-size:{INFO_SIZE}px;font-weight:700;fill:{theme.key}}}
.k{{font-size:{INFO_SIZE}px;font-weight:700;fill:{theme.key}}}
.v{{font-size:{INFO_SIZE}px;fill:{theme.foreground}}}
.d{{font-size:{INFO_SIZE}px;fill:{theme.dim}}}
.edge{{stroke:{theme.motif};stroke-width:1;opacity:.55}}
.node{{fill:{theme.motif};opacity:.8}}
.spark{{fill:{theme.accent}}}
.cursor{{fill:{theme.key};animation:blink 1.1s steps(1) infinite}}
.pulse{{animation:pulse 5s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{opacity:.25}}50%{{opacity:.8}}}}
@keyframes blink{{50%{{opacity:0}}}}
@media (prefers-reduced-motion: reduce){{.pulse,.cursor{{animation:none}}}}
</style>"""


def _motif(x0, y0, width, height):
    rng = random.Random(MOTIF_SEED)
    nodes = [
        (x0 + rng.uniform(0, width), y0 + rng.uniform(0, height)) for _ in range(MOTIF_NODES)
    ]
    edges = set()
    for index, point in enumerate(nodes):
        others = sorted(
            (other for other in range(len(nodes)) if other != index),
            key=lambda other: math.dist(nodes[other], point),
        )
        edges.update(tuple(sorted((index, other))) for other in others[:2])
    parts = []
    for order, (a, b) in enumerate(sorted(edges)):
        (xa, ya), (xb, yb) = nodes[a], nodes[b]
        parts.append(
            f'<line class="edge pulse" style="animation-delay:{order % 5}s" '
            f'x1="{_n(xa)}" y1="{_n(ya)}" x2="{_n(xb)}" y2="{_n(yb)}"/>'
        )
    for x, y in nodes:
        parts.append(f'<circle class="node" cx="{_n(x)}" cy="{_n(y)}" r="2"/>')
    return "".join(parts)


def _art(art, x, y):
    lines = "".join(
        f'<tspan x="{_n(x)}" y="{_n(y + ART_STEP * index)}">{escape(line)}</tspan>'
        for index, line in enumerate(art)
    )
    return f'<text class="art" xml:space="preserve">{lines}</text>'


def _sparkline(values, x, baseline):
    peak = max(values, default=0) or 1
    bars = []
    for index, value in enumerate(values):
        height = 1 + (SPARK_HEIGHT - 1) * value / peak
        bars.append(
            f'<rect class="spark" x="{_n(x + index * SPARK_STEP)}" y="{_n(baseline - height)}" '
            f'width="{SPARK_BAR_WIDTH}" height="{_n(height)}"/>'
        )
    return "".join(bars)


def render_svg(config: Config, stats: Stats, art: list[str], theme: Theme, today: date) -> str:
    rows = _info_rows(config, stats, today)
    art_width = max((len(line) for line in art), default=0) * ART_CHAR
    art_height = len(art) * ART_STEP
    info_x = PAD + art_width + GAP
    value_x = info_x + KEY_WIDTH
    longest = max(len(value) for _, value in rows if value)
    spark_width = SPARK_BARS * SPARK_STEP
    width = value_x + max(longest * INFO_CHAR, spark_width) + PAD

    header = f"{config.handle}@{config.host}"
    info_lines = len(rows) + 4
    offset = max(0.0, (art_height - info_lines * INFO_STEP) / 2)
    y = PAD + INFO_SIZE + offset
    info = []
    for kind, text in (("h", header), ("d", "-" * len(header))):
        info.append(f'<text class="{kind}" x="{_n(info_x)}" y="{_n(y)}">{escape(text)}</text>')
        y += INFO_STEP
    for key, value in rows:
        info.append(f'<text><tspan class="k" x="{_n(info_x)}" y="{_n(y)}">{escape(key)}:</tspan>')
        if value is None:
            info.append("</text>")
            info.append(_sparkline(stats.daily, value_x, y))
        else:
            info.append(
                f'<tspan class="v" x="{_n(value_x)}" y="{_n(y)}">{escape(value)}</tspan></text>'
            )
        y += INFO_STEP
    for index, color in enumerate(theme.swatches):
        info.append(
            f'<rect x="{_n(info_x + index * 22)}" y="{_n(y - 10)}" width="18" height="12" '
            f'rx="2" fill="{color}"/>'
        )
    y += INFO_STEP
    info.append(f'<text class="d" x="{_n(info_x)}" y="{_n(y)}">$</text>')
    info.append(
        f'<rect class="cursor" x="{_n(info_x + INFO_CHAR * 2)}" y="{_n(y - 11)}" '
        f'width="8" height="14"/>'
    )

    height = PAD * 2 + max(art_height, y - PAD)
    title = escape(f"{config.handle}@{config.host}", {'"': "&quot;"})
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_n(width)}" height="{_n(height)}" '
        f'viewBox="0 0 {_n(width)} {_n(height)}" role="img" aria-label="{title}">'
        f"<title>{title}</title>{_style(theme)}"
        f'<rect class="bg" x="0.5" y="0.5" width="{_n(width - 1)}" height="{_n(height - 1)}" rx="14"/>'
        f"{_motif(PAD, PAD, art_width, art_height)}"
        f"{_art(art, PAD, PAD + ART_SIZE)}"
        f'{"".join(info)}</svg>'
    )
