from PIL import Image

from profile_card.ascii_art import image_to_ascii


def half_black_half_white():
    image = Image.new("L", (40, 40), 0)
    image.paste(255, (20, 0, 40, 40))
    return image


def test_lines_have_requested_width_and_aspect_corrected_height():
    lines = image_to_ascii(half_black_half_white(), columns=10)
    assert len(lines) == 5
    assert {len(line) for line in lines} == {10}


def test_bright_pixels_are_dense_and_dark_pixels_are_blank():
    first = image_to_ascii(half_black_half_white(), columns=10)[0]
    assert first[0] == " " and first[-1] == "@"
