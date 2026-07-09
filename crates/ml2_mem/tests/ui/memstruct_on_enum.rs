// MemStruct is only sensible on named-field structs. Deriving it on an
// enum should fail with a clear "structs only" message so users don't
// try to make a variant-per-field decoder that way.

use ml2_mem::MemStruct;

#[derive(MemStruct)]
enum NotAStruct {
    A,
    B,
}

fn main() {}
