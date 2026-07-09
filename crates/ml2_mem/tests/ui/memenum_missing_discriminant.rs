// MemEnum variants must all carry an explicit `= <int>` discriminant.
// Rust would auto-number omitted ones, but game-state enums always
// have fixed wire values; a missed `= 3` would silently shift every
// subsequent variant one over.

use ml2_mem::MemEnum;

#[repr(i32)]
#[derive(MemEnum)]
enum MissingDiscriminant {
    A = 0,
    B, // deliberately no `= <int>`
    C = 2,
}

fn main() {}
