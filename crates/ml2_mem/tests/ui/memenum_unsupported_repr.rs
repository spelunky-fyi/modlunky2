// MemEnum only supports the concrete integer reprs (u8..u64, i8..i64).
// `#[repr(C)]` doesn't fix a size to read on the wire, so the derive
// must reject it rather than emit an ambiguous read.

use ml2_mem::MemEnum;

#[repr(C)]
#[derive(MemEnum)]
enum ReprC {
    A = 0,
    B = 1,
}

fn main() {}
