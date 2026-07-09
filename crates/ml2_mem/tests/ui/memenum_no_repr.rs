// MemEnum requires an explicit `#[repr(iN)]` / `#[repr(uN)]` so the on-
// wire primitive size is unambiguous. A plain #[derive(MemEnum)] with
// no repr must compile-error, not fall back to a compiler-default repr
// that could shift between rustc versions.

use ml2_mem::MemEnum;

#[derive(MemEnum)]
enum NoRepr {
    A = 0,
    B = 1,
}

fn main() {}
