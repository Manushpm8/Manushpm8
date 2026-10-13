from PIL import Image

from profile_card.ascii_art import image_to_ascii


def half_black_half_white():
    image = Image.new("L", (40, 40), 0)
    image.paste(255, (20, 0, 40, 40))
    return image


def test_lines_have_requested_width_and_aspect_corrected_height():
    lines = image_to_ascii(half_black_half_white(), columns=10, invert=False)
    assert len(lines) == 5
    assert {len(line) for line in lines} == {10}


def test_dark_variant_is_dense_where_bright_and_light_variant_is_inverse():
    dark = image_to_ascii(half_black_half_white(), columns=10, invert=False)[0]
    light = image_to_ascii(half_black_half_white(), columns=10, invert=True)[0]
    assert dark[0] == " " and dark[-1] == "@"
    assert light[0] == "@" and light[-1] == " "
