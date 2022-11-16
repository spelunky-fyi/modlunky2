use std::cmp;
use std::io::Cursor;

use byteorder::WriteBytesExt;
use byteorder::LE;
use bytes::Buf;

// https://mostlymangling.blogspot.com/2020/01/nasam-not-another-strange-acronym-mixer.html
fn xnasamx(constant: u64, data: u64) -> u64 {
    let mut data = data;

    data ^= constant;
    data ^= data.rotate_right(25) ^ data.rotate_right(47);
    data = data.wrapping_mul(0x9E6C63D0676A9A99);

    data ^= data >> 23 ^ data >> 51;
    data = data.wrapping_mul(0x9E6D62D06F6A9A9B);
    data ^= data >> 23 ^ data >> 51;

    data ^= constant;

    data
}

#[derive(Default)]
pub struct NasamGenerator {
    previous_key: u64,
}

impl NasamGenerator {
    pub fn get_next_key(&mut self, data: u64) -> u64 {
        let new_key = xnasamx(self.previous_key, data);
        self.previous_key = new_key;
        new_key
    }
}

trait Spel2ChaCha {
    fn hash_filepath(&self, filepath: &[u8]) -> Vec<u8>;
    fn decrypt(&self, filepath: &[u8], data: &[u8]) -> Vec<u8>;
}

#[derive(Default)]
pub struct Spel2ChaChaVersion1 {}

impl Spel2ChaChaVersion1 {
    pub fn new() -> Self {
        Self {}
    }
}

impl Spel2ChaCha for Spel2ChaChaVersion1 {
    fn hash_filepath(&self, filepath: &[u8]) -> Vec<u8> {
        let h0 = mix_in(&[0; 64], filepath);
        let h1 = quad_rounds(&h0);
        let key = quad_rounds(&add_bytes_as_quads(&h0, &h1));

        keyed_hashing(filepath, &key)
    }

    fn decrypt(&self, filepath: &[u8], data: &[u8]) -> Vec<u8> {
        let h = two_rounds(&quads_to_bytes(&[0xBABE, 0, 0, 0, 0, 0, 0, 0]));
        let h = mix_in_filepath(filepath, &h);

        let key = quad_rounds(&add_bytes_as_quads(&h, &quad_rounds(&h)));
        decrypt_common(data, &key)
    }
}

pub struct Spel2ChaChaVersion2 {
    pub key: u64,
}

impl Spel2ChaChaVersion2 {
    pub fn new(key: u64) -> Self {
        Self { key }
    }
}

impl Spel2ChaCha for Spel2ChaChaVersion2 {
    fn hash_filepath(&self, filepath: &[u8]) -> Vec<u8> {
        let h = mix_in(
            &two_rounds(&quads_to_bytes(&[
                self.key,
                filepath.len() as u64,
                0,
                0,
                0,
                0,
                0,
                0,
            ])),
            filepath,
        );

        let tmp = add_bytes_as_quads(&h, &quad_rounds(&h));
        let mut tmp = bytes_to_quads(&tmp);
        tmp[0] ^= filepath.len() as u64;

        let key = quad_rounds(&quads_to_bytes(&tmp));

        keyed_hashing(filepath, &key)
    }

    fn decrypt(&self, filepath: &[u8], data: &[u8]) -> Vec<u8> {
        let h = two_rounds(&quads_to_bytes(&[
            self.key,
            filepath.len() as u64,
            0,
            0,
            0,
            0,
            0,
            0,
        ]));
        let h = mix_in_filepath(filepath, &h);

        let tmp = add_bytes_as_quads(&h, &quad_rounds(&h));
        let mut tmp = bytes_to_quads(&tmp);
        tmp[0] ^= self.key.wrapping_add(data.len() as u64);

        let key = quad_rounds(&quads_to_bytes(&tmp));
        decrypt_common(data, &key)
    }
}

fn words_to_bytes(words: &[u32]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(words.len() * 4);
    for word in words {
        let _ = bytes.write_u32::<LE>(*word);
    }
    bytes
}

fn bytes_to_words(bytes: &[u8]) -> Vec<u32> {
    assert!(bytes.len() % 4 == 0);
    let mut buf = Cursor::new(bytes);
    let mut words: Vec<u32> = Vec::with_capacity(bytes.len() / 4);
    while buf.remaining() >= 4 {
        words.push(buf.get_u32_le());
    }

    words
}

fn quads_to_bytes(quads: &[u64]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(quads.len() * 8);
    for quad in quads {
        let _ = bytes.write_u64::<LE>(*quad);
    }
    bytes
}

fn bytes_to_quads(bytes: &[u8]) -> Vec<u64> {
    assert!(bytes.len() % 8 == 0);
    let mut buf = Cursor::new(bytes);
    let mut quads: Vec<u64> = Vec::with_capacity(bytes.len() / 8);
    while buf.remaining() >= 4 {
        quads.push(buf.get_u64_le());
    }

    quads
}

fn add_bytes_as_quads(bytes1: &[u8], bytes2: &[u8]) -> Vec<u8> {
    let quads: Vec<u64> = bytes_to_quads(bytes1)
        .iter()
        .zip(bytes_to_quads(bytes2))
        .map(|(a, b)| a.wrapping_add(b))
        .collect();
    quads_to_bytes(&quads)
}

fn xor_bytes(bytes1: &[u8], bytes2: &[u8]) -> Vec<u8> {
    bytes1.iter().zip(bytes2).map(|(a, b)| a ^ b).collect()
}

fn quarter_round(words: &mut [u32], a: usize, b: usize, c: usize, d: usize) {
    words[a] = words[a].wrapping_add(words[b]);
    words[d] ^= words[a];
    words[d] = words[d].rotate_left(16);
    words[c] = words[c].wrapping_add(words[d]);
    words[b] ^= words[c];
    words[b] = words[b].rotate_left(12);
    words[a] = words[a].wrapping_add(words[b]);
    words[d] ^= words[a];
    words[d] = words[d].rotate_left(8);
    words[c] = words[c].wrapping_add(words[d]);
    words[b] ^= words[c];
    words[b] = words[b].rotate_left(7);
}

fn round_pair(words: &mut [u32]) {
    quarter_round(words, 0, 4, 8, 12);
    quarter_round(words, 1, 5, 9, 13);
    quarter_round(words, 2, 6, 10, 14);
    quarter_round(words, 3, 7, 11, 15);
    quarter_round(words, 0, 5, 10, 15);
    quarter_round(words, 1, 6, 11, 12);
    quarter_round(words, 2, 7, 8, 13);
    quarter_round(words, 3, 4, 9, 14);
}

fn two_rounds(bytes: &[u8]) -> Vec<u8> {
    let mut words = bytes_to_words(bytes);
    round_pair(&mut words);
    round_pair(&mut words);
    words_to_bytes(&words)
}

fn quad_rounds(bytes: &[u8]) -> Vec<u8> {
    let mut words = bytes_to_words(bytes);
    round_pair(&mut words);
    round_pair(&mut words);
    round_pair(&mut words);
    round_pair(&mut words);
    words_to_bytes(&words)
}

fn mix_in(h: &[u8], s: &[u8]) -> Vec<u8> {
    let mut buf = Cursor::new(s);
    let len = h.len();
    let mut out: Vec<u8> = h.to_vec();

    while buf.remaining() > 0 {
        let amount = cmp::min(len, buf.remaining());
        let partial = buf.copy_to_bytes(amount);
        for (idx, byte) in partial.iter().rev().enumerate() {
            out[idx] ^= byte;
        }
        out = quad_rounds(&out);
    }

    out
}

fn mix_in_filepath(filepath: &[u8], h: &[u8]) -> Vec<u8> {
    let mut out: Vec<u8> = h.to_vec();

    for idx in (0..filepath.len()).step_by(64) {
        let amount = cmp::min(idx + 64, filepath.len());
        let partial = &filepath[idx..amount];

        let mut new_out = xor_bytes(
            &out[..partial.len()],
            &partial.iter().rev().cloned().collect::<Vec<_>>(),
        );
        new_out.extend_from_slice(&out[partial.len()..]);
        out = quad_rounds(&new_out);
    }

    out
}

fn keyed_hashing(filepath: &[u8], key: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(filepath.len());

    for idx in (0..filepath.len()).step_by(64) {
        let amount = cmp::min(idx + 64, filepath.len());
        let partial = &filepath[idx..amount];
        let key_input: Vec<u8> = key[..partial.len()].iter().rev().cloned().collect();
        out.extend_from_slice(&xor_bytes(partial, &key_input));
    }

    out
}

fn decrypt_common(data: &[u8], key: &[u8]) -> Vec<u8> {
    let mut buf = Cursor::new(data);
    let mut out: Vec<u8> = Vec::with_capacity(data.len());

    if buf.remaining() >= 64 {
        let blocks = buf.remaining() / 64;
        let tmp_key: Vec<_> = key
            .iter()
            .rev()
            .cycle()
            .take(key.len() * blocks)
            .cloned()
            .collect();
        out.extend_from_slice(&xor_bytes(data, &tmp_key));
        buf.advance(blocks * 64);
    }

    if buf.remaining() > 0 {
        let tmp_key: Vec<_> = key.iter().take(buf.remaining()).rev().cloned().collect();
        out.extend_from_slice(&xor_bytes(&buf.copy_to_bytes(buf.remaining()), &tmp_key));
    }

    out
}

#[cfg(test)]
mod tests {
    use crate::{
        bytes_to_words, mix_in, mix_in_filepath, quad_rounds, quarter_round, round_pair,
        words_to_bytes, xnasamx, NasamGenerator, Spel2ChaCha, Spel2ChaChaVersion1,
        Spel2ChaChaVersion2,
    };

    #[test]
    fn test_xnasamx() {
        let result = xnasamx(0, 20);
        assert_eq!(result, 12792988793366353668);

        let result = xnasamx(result, 32);
        assert_eq!(result, 3725411152094604090);
    }

    #[test]
    fn test_xnasamx_generator() {
        let mut keygen = NasamGenerator::default();
        assert_eq!(keygen.get_next_key(20), 12792988793366353668);
        assert_eq!(keygen.get_next_key(32), 3725411152094604090);
    }

    #[test]
    fn test_byte_utils() {
        let words = [
            1650552427, 1634626350, 1970168930, 29551, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        ];
        let bytes = words_to_bytes(&words);
        let expected_bytes = vec![
            107, 110, 97, 98, 46, 107, 110, 97, 98, 100, 110, 117, 111, 115, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        ];
        assert_eq!(bytes, expected_bytes);

        assert_eq!(bytes_to_words(&expected_bytes), words);
    }

    #[test]
    fn test_quad_rounds() {
        let input = vec![
            107, 110, 97, 98, 46, 107, 110, 97, 98, 100, 110, 117, 111, 115, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        ];
        let expected_output = vec![
            212, 127, 188, 241, 31, 19, 122, 110, 205, 138, 55, 10, 53, 235, 26, 251, 124, 235,
            133, 204, 147, 37, 146, 229, 166, 155, 88, 181, 60, 95, 47, 187, 82, 112, 179, 220,
            157, 2, 100, 110, 46, 45, 186, 29, 108, 37, 125, 232, 54, 68, 100, 145, 93, 89, 78, 85,
            235, 120, 201, 166, 59, 150, 177, 0,
        ];
        assert_eq!(quad_rounds(&input), expected_output);
    }

    #[test]
    fn test_quarter_rounds() {
        let input: &mut [u32] = &mut [
            1650552427, 1634626350, 1970168930, 29551, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        ];
        let expected_output: &[u32] = &[
            411534673, 1634626350, 1970168930, 29551, 3124893942, 0, 0, 0, 1532138199, 0, 0, 0,
            3974574198, 0, 0, 0,
        ];

        quarter_round(input, 0, 4, 8, 12);
        assert_eq!(input, expected_output);
    }

    #[test]
    fn test_round_pair() {
        let input: &mut [u32] = &mut [
            1650552427, 1634626350, 1970168930, 29551, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        ];
        let expected_output: &[u32] = &[
            3167643655, 236668630, 588641371, 3902845107, 2431346184, 895988070, 4273507265,
            3758282703, 2394901125, 796904404, 1277722972, 3486881271, 2607530847, 139394312,
            3283996349, 2218520832,
        ];

        round_pair(input);
        assert_eq!(input, expected_output);
    }

    #[test]
    fn test_mix_in() {
        let input: &[u8] = &[0; 64];
        let input2 = b"soundbank.bank";

        let output = mix_in(input, &input2[..]);
        assert_eq!(
            output,
            vec![
                212, 127, 188, 241, 31, 19, 122, 110, 205, 138, 55, 10, 53, 235, 26, 251, 124, 235,
                133, 204, 147, 37, 146, 229, 166, 155, 88, 181, 60, 95, 47, 187, 82, 112, 179, 220,
                157, 2, 100, 110, 46, 45, 186, 29, 108, 37, 125, 232, 54, 68, 100, 145, 93, 89, 78,
                85, 235, 120, 201, 166, 59, 150, 177, 0
            ]
        );

        let input2 = [b'A'; 100];
        let output = mix_in(input, &input2[..]);
        assert_eq!(
            output,
            vec![
                146, 39, 70, 209, 220, 37, 0, 29, 179, 43, 94, 74, 190, 68, 228, 79, 127, 144, 134,
                95, 55, 176, 95, 235, 210, 226, 88, 29, 47, 85, 28, 175, 33, 212, 238, 246, 79, 63,
                163, 102, 254, 176, 179, 134, 248, 174, 241, 35, 231, 204, 53, 181, 110, 57, 101,
                125, 65, 122, 89, 217, 181, 248, 173, 166
            ]
        );
    }

    #[test]
    fn test_hash_filepath() {
        let chacha = Spel2ChaChaVersion1::new();
        let out = chacha.hash_filepath(b"soundbank.bank");
        assert_eq!(
            out,
            vec![183, 203, 129, 66, 138, 9, 175, 90, 79, 23, 201, 49, 59, 196]
        );

        let mut gen = NasamGenerator::default();
        let key = gen.get_next_key(10);
        let chacha = Spel2ChaChaVersion2::new(key);
        let out = chacha.hash_filepath(b"soundbank.bank");
        assert_eq!(
            out,
            vec![195, 155, 109, 179, 10, 55, 151, 210, 190, 15, 107, 118, 50, 62]
        );
    }

    #[test]
    fn test_mix_in_filehash() {
        let input = vec![
            207, 131, 4, 64, 139, 182, 207, 58, 174, 141, 160, 97, 202, 34, 10, 250, 227, 118, 59,
            221, 247, 72, 244, 64, 21, 146, 60, 182, 145, 77, 122, 83, 190, 51, 169, 157, 162, 193,
            28, 35, 133, 93, 78, 247, 3, 197, 220, 26, 42, 145, 10, 187, 172, 0, 249, 143, 211,
            176, 42, 175, 223, 248, 213, 14,
        ];
        assert_eq!(
            mix_in_filepath(b"soundbank.bank", &input),
            vec![
                174, 69, 29, 145, 46, 160, 69, 42, 87, 168, 10, 195, 164, 139, 64, 107, 234, 62,
                58, 184, 88, 26, 108, 192, 96, 101, 117, 192, 2, 194, 8, 142, 35, 19, 238, 143,
                193, 96, 147, 220, 71, 38, 138, 110, 243, 26, 97, 246, 0, 113, 126, 158, 59, 36,
                173, 253, 137, 6, 190, 176, 156, 79, 1, 106
            ]
        );
    }

    #[test]
    fn test_decrypt_v1() {
        let chacha = Spel2ChaChaVersion1::new();
        let out = chacha.decrypt(b"soundbank.bank", b"Hello, world!");
        assert_eq!(
            out,
            vec![26, 179, 242, 15, 166, 167, 221, 26, 174, 209, 254, 86, 24]
        );

        let out = chacha.decrypt(b"soundbank.bank", &[b'A'; 64][..]);
        assert_eq!(
            out,
            vec![
                62, 189, 27, 158, 228, 154, 122, 96, 213, 155, 139, 30, 55, 25, 53, 204, 179, 1, 9,
                244, 145, 175, 160, 228, 141, 238, 3, 52, 51, 85, 18, 66, 170, 78, 177, 176, 118,
                26, 151, 181, 95, 205, 225, 23, 235, 143, 192, 217, 212, 96, 213, 19, 151, 223, 34,
                136, 202, 188, 44, 128, 226, 211, 115, 120
            ]
        );

        let out = chacha.decrypt(b"soundbank.bank", &[b'A'; 80][..]);
        assert_eq!(
            out,
            vec![
                62, 189, 27, 158, 228, 154, 122, 96, 213, 155, 139, 30, 55, 25, 53, 204, 179, 1, 9,
                244, 145, 175, 160, 228, 141, 238, 3, 52, 51, 85, 18, 66, 170, 78, 177, 176, 118,
                26, 151, 181, 95, 205, 225, 23, 235, 143, 192, 217, 212, 96, 213, 19, 151, 223, 34,
                136, 202, 188, 44, 128, 226, 211, 115, 120, 212, 96, 213, 19, 151, 223, 34, 136,
                202, 188, 44, 128, 226, 211, 115, 120
            ]
        );
    }

    #[test]
    fn test_decrypt_v2() {
        let mut gen = NasamGenerator::default();
        let key = gen.get_next_key(10);

        let chacha = Spel2ChaChaVersion2::new(key);
        let out = chacha.decrypt(b"soundbank.bank", b"Hello, world!");
        assert_eq!(
            out,
            vec![225, 238, 172, 4, 94, 243, 170, 1, 163, 85, 34, 169, 103]
        );

        let out = chacha.decrypt(b"soundbank.bank", &[b'A'; 64][..]);
        assert_eq!(
            out,
            vec![
                43, 161, 88, 42, 147, 2, 147, 189, 95, 27, 229, 80, 9, 4, 116, 80, 134, 38, 104,
                81, 203, 220, 19, 96, 255, 204, 163, 50, 233, 184, 140, 248, 119, 23, 50, 119, 208,
                105, 183, 128, 106, 254, 122, 159, 243, 172, 193, 81, 208, 78, 129, 137, 175, 103,
                17, 170, 21, 121, 31, 210, 160, 199, 24, 103
            ]
        );

        let out = chacha.decrypt(b"soundbank.bank", &[b'A'; 80][..]);
        assert_eq!(
            out,
            vec![
                227, 158, 40, 253, 221, 175, 40, 54, 146, 95, 131, 246, 187, 171, 50, 212, 71, 122,
                128, 197, 247, 40, 190, 131, 204, 200, 18, 44, 58, 66, 19, 28, 115, 244, 120, 155,
                247, 173, 62, 140, 172, 124, 19, 246, 138, 91, 1, 245, 246, 132, 69, 154, 23, 153,
                186, 70, 37, 197, 84, 30, 89, 53, 111, 231, 246, 132, 69, 154, 23, 153, 186, 70,
                37, 197, 84, 30, 89, 53, 111, 231
            ]
        );
    }
}
