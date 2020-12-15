import io
from struct import pack, unpack

from PIL import Image


def rgba_to_png(data):
    width, height = unpack(b"<II", data[:8])
    img = Image.frombytes("RGBA", (width, height), data[8:], "raw")
    new_data = io.BytesIO()
    img.save(new_data, format="PNG")
    return new_data.getvalue()


def dds_to_png(data):
    """ Takes a .DDS `Image` and returns .png data."""
    img = Image.open(io.BytesIO(data))
    img.tile[0] = img.tile[0][:-1] + ((img.tile[0][-1][0][::-1], 0, 1),)
    new_data = io.BytesIO()
    img.save(new_data, format="PNG")
    return new_data.getvalue()


def png_to_dds(img):
    """ Takes a .png `Image` and returns .DDS data."""

    img = img.convert("RGBA")

    # https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dds-header
    header_size = 124  # always the same
    flags = 0x0002100F  # required flags + pitch + mipmapped

    height = img.height
    width = img.width

    pitch = width * 4  # bytes per line
    depth = 1
    mipmaps = 1

    # pixel format sub structure
    pfsize = 32  # size of pixel format structure, constant
    pfflags = 0x41  # uncompressed RGB with alpha channel
    fourcc = 0  # compression mode (not used for uncompressed data)
    bitcount = 32
    # bit masks for each channel, here for RGBA
    rmask = 0xFF000000
    gmask = 0x00FF0000
    bmask = 0x0000FF00
    amask = 0x000000FF

    caps = 0x1000  # simple texture with only one surface and no mipmaps
    caps2 = 0  # additional surface data, unused
    caps3 = 0  # unused
    caps4 = 0  # unused

    data = b"DDS "  # magic bytes
    data += pack("<II", header_size, flags)
    data += pack("<5I", height, width, pitch, depth, mipmaps)
    data += pack("<11I", *((0,) * 11))  # reserved
    data += pack("<4I", pfsize, pfflags, fourcc, bitcount)
    data += pack(">4I", rmask, gmask, bmask, amask)  # masks are stored in big endian
    data += pack("<4I", caps, caps2, caps3, caps4)
    data += pack("<I", 0)  # reserved

    data += bytes(
        (
            byte if rgba[3] != 0 else 0
        )  # Hack to force all transparent pixels to be (0, 0, 0, 0)
        # instead of (255, 255, 255, 0)
        for rgba in img.getdata()
        for byte in rgba
    )

    return data
