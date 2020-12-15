# pylint: disable=invalid-name

from struct import pack, unpack

DEFAULT_COMPRESSION_LEVEL = 20


def rotate_left(a, b, bits=32):
    a &= (1 << bits) - 1
    return ((((a) << (b)) | ((a) >> (bits - (b))))) & ((1 << bits) - 1)


def quarter_round(w, a, b, c, d):
    w[a] += w[b]
    w[a] &= 0xFFFFFFFF
    w[d] ^= w[a]
    w[d] = rotate_left(w[d], 16)
    w[c] += w[d]
    w[c] &= 0xFFFFFFFF
    w[b] ^= w[c]
    w[b] = rotate_left(w[b], 12)
    w[a] += w[b]
    w[a] &= 0xFFFFFFFF
    w[d] ^= w[a]
    w[d] = rotate_left(w[d], 8)
    w[c] += w[d]
    w[c] &= 0xFFFFFFFF
    w[b] ^= w[c]
    w[b] = rotate_left(w[b], 7)


def round_pair(w):
    quarter_round(w, 0, 4, 8, 12)
    quarter_round(w, 1, 5, 9, 13)
    quarter_round(w, 2, 6, 10, 14)
    quarter_round(w, 3, 7, 11, 15)
    quarter_round(w, 0, 5, 10, 15)
    quarter_round(w, 1, 6, 11, 12)
    quarter_round(w, 2, 7, 8, 13)
    quarter_round(w, 3, 4, 9, 14)


def two_rounds(s):
    w = s_to_w(s)
    round_pair(w)
    round_pair(w)
    return w_to_s(w)


def quad_rounds(s):
    w = s_to_w(s)
    round_pair(w)
    round_pair(w)
    round_pair(w)
    round_pair(w)
    return w_to_s(w)


def sxor(x, y):
    return bytes(a ^ b for a, b in zip(x, y))


def s_to_w(s):
    return list(unpack(b"<" + (b"I" * (len(s) // 4)), s))


def w_to_s(w):
    return pack(b"<" + (b"I" * len(w)), *w)


def s_to_q(s):
    return list(unpack(b"<" + (b"Q" * (len(s) // 8)), s))


def q_to_s(w):
    return pack(b"<" + (b"Q" * len(w)), *w)


def add_qwords(h0, h1):
    return q_to_s(
        [(a + b) & 0xFFFFFFFFFFFFFFFF for a, b in zip(s_to_q(h0), s_to_q(h1))]
    )


def mix_in(h, s):
    def mix_partial(h, partial):
        assert len(partial) <= 0x40
        b = bytearray(h)
        for i, c in enumerate(partial[::-1]):
            b[i] ^= ord("%c" % c)
        return quad_rounds(bytes(b))

    while s != b"":
        h = mix_partial(h, s[:0x40])
        s = s[0x40:]

    return h


def hash_filepath_v1(filepath):
    # Generate initial hash from the string
    h0 = mix_in(b"\x00" * 0x40, filepath)

    # Advance h0 by four round pairs to get h1
    h1 = quad_rounds(h0)
    # Add the two together, and advance by four round pairs.
    key = quad_rounds(add_qwords(h0, h1))

    return keyed_hashing(filepath, key)


def hash_filepath_v2(filepath, key):
    # Generate initial hash from the string
    h = two_rounds(pack(b"<QQQQQQQQ", key, len(filepath), 0, 0, 0, 0, 0, 0))
    h = mix_in(h, filepath)

    # Add the two together, and advance by four round pairs.
    tmp = add_qwords(h, quad_rounds(h))
    tmp = s_to_q(tmp)
    key = quad_rounds(q_to_s([tmp[0] ^ len(filepath)] + tmp[1:]))

    return keyed_hashing(filepath, key)


def hash_filepath(filepath, key=None, version="v2"):
    if version == "v1":
        return hash_filepath_v1(filepath)

    if version == "v2":
        return hash_filepath_v2(filepath, key)

    raise ValueError("Invalid version provided.")


def keyed_hashing(filepath, key):
    # Do keyed hashing
    # NOTE: This appears to be an implementation mistake on the Spelunky 2 dev's part
    # They generate a quad_round advanced version of (nonce'd key), but then they
    # xor with the untweaked key instead of the tweaked key...

    h = b""
    for i in range(0, len(filepath), 0x40):
        partial = filepath[i : i + 0x40]
        h += sxor(partial, key[: len(partial)][::-1])
    return h


class Key:
    def __init__(self, key=0, mask=2 ** 64 - 1):
        self.key = key
        self.mask = mask

    def update(self, asset_len):
        v3 = (
            0x9E6C63D0676A9A99
            * (
                self.key
                ^ asset_len
                ^ rotate_left(self.key ^ asset_len, 17, 64)
                ^ rotate_left(self.key ^ asset_len, 64 - 25, 64)
            )
            & self.mask
        )
        v4 = 0x9E6D62D06F6A9A9B * (v3 ^ ((v3 ^ (v3 >> 28)) >> 23)) & self.mask
        self.key ^= v4 ^ ((v4 ^ (v4 >> 28)) >> 23)


def mix_in_filepath(filepath, h):
    # Mix the filename in to tweak the key
    for i in range(0, len(filepath), 0x40):
        partial = filepath[i : i + 0x40]
        h = quad_rounds(sxor(h[: len(partial)], partial[::-1]) + h[len(partial) :])
    return h


def chacha_rest(data, key):
    # NOTE: This appears to be an implementation mistake on the Spelunky 2 dev's part
    # They generate a quad_round advanced version of (nonce'd key), but then they
    # xor with the untweaked key instead of the tweaked key...
    out = b""
    if len(data) >= 0x40:
        blocks = len(data) // 0x40
        out += sxor(data, key[::-1] * blocks)
        data = data[blocks * 0x40 :]
    if len(data) > 0:
        out += sxor(data, key[: len(data)][::-1])

    return out


def chacha_v1(filepath, data):
    # Untweaked key begins as half-advanced "0xBABE"
    h = two_rounds(pack(b"<QQQQQQQQ", 0xBABE, 0, 0, 0, 0, 0, 0, 0))

    h = mix_in_filepath(filepath, h)

    # Add the tweaked key and its advancement, then advance by four round pairs.
    key = quad_rounds(add_qwords(h, quad_rounds(h)))

    return chacha_rest(data, key)


def chacha_v2(filepath, data, key):
    # Untweaked key begins as half-advanced `key`
    h = two_rounds(pack(b"<QQQQQQQQ", key, len(filepath), 0, 0, 0, 0, 0, 0))

    h = mix_in_filepath(filepath, h)

    # Add the tweaked key and its advancement, then advance by four round pairs.
    tmp = add_qwords(h, quad_rounds(h))
    tmp = s_to_q(tmp)
    key = quad_rounds(q_to_s([tmp[0] ^ key + len(data)] + tmp[1:]))

    return chacha_rest(data, key)


def chacha(filepath, data, key=None, version="v2"):
    if version == "v1":
        return chacha_v1(filepath, data)

    if version == "v2":
        return chacha_v2(filepath, data, key)

    raise ValueError("Invalid version provided.")
