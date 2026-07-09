// MemEnum variants must be unit variants. A tuple-like or struct-like
// variant can't be represented by a single primitive on the wire, so
// the derive rejects it rather than silently emit a mismatched read.

use ml2_mem::MemEnum;

#[repr(u8)]
#[derive(MemEnum)]
enum NonUnit {
    A = 0,
    B(u8) = 1,
}

fn main() {}
