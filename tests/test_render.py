import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date

from profile_card.render import render_svg
from profile_card.stats import Stats
from profile_card.theme import DARK, LIGHT

TODAY = date(2026, 10, 13)


def canvas_width(svg):
    return float(re.search(r'<svg [^>]*width="([\d.]+)"', svg).group(1))


def strip_colours(svg):
    return re.sub(r"#[0-9a-fA-F]{6}", "#", svg)


def test_output_is_valid_xml_even_with_ampersand_in_config(config, stats, art):
    svg = render_svg(config, stats, art, DARK, TODAY)
    ET.fromstring(svg)
    assert "Structured &amp; graph foundation models" in svg


def test_value_column_is_aligned(config, stats, art):
    svg = render_svg(config, stats, art, DARK, TODAY)
    xs = set(re.findall(r'<tspan class="v" x="([\d.]+)"', svg))
    assert len(xs) == 1


def test_light_and_dark_differ_only_in_colour(config, stats, art):
    dark = render_svg(config, stats, art, DARK, TODAY)
    light = render_svg(config, stats, art, LIGHT, TODAY)
    assert dark != light
    assert strip_colours(dark) == strip_colours(light)


def test_rendering_is_deterministic(config, stats, art):
    first = render_svg(config, stats, art, DARK, TODAY)
    assert first == render_svg(config, stats, art, DARK, TODAY)


def test_missing_stats_render_as_na(config, art):
    svg = render_svg(config, Stats(), art, DARK, TODAY)
    ET.fromstring(svg)
    assert svg.count("n/a") >= 4


def test_flat_sparkline_renders_when_every_day_is_zero(config, art):
    flat = Stats(repos=0, stars=0, commits=0, additions=0, deletions=0, daily=(0,) * 30)
    svg = render_svg(config, flat, art, DARK, TODAY)
    ET.fromstring(svg)
    assert svg.count('class="spark"') == 30


def test_canvas_widens_for_values_longer_than_the_default_rows(config, art, stats):
    wide = replace(config, role="x" * 120)
    assert canvas_width(render_svg(wide, stats, art, DARK, TODAY)) > canvas_width(
        render_svg(config, stats, art, DARK, TODAY)
    )


def test_very_large_numbers_render_valid_xml(config, art):
    huge = Stats(repos=1, stars=1, commits=1, additions=10**12, deletions=10**12, daily=(1,) * 30)
    ET.fromstring(render_svg(config, huge, art, DARK, TODAY))


def test_motion_is_disabled_for_reduced_motion_users(config, stats, art):
    assert "prefers-reduced-motion: reduce" in render_svg(config, stats, art, DARK, TODAY)
