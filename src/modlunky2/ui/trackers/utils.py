def hex_to_rgb(hex_value):
    return tuple(int(hex_value[idx : idx + 2], 16) for idx in (0, 2, 4))


def get_text_color(bg_color):
    rgb = hex_to_rgb(bg_color.lstrip("#"))
    if (rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114) > 160:
        return "#000000"
    return "#ffffff"
