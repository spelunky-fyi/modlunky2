// A MemStruct field with no #[offset(N)] must be a hard compile error.
// Otherwise a typo in the annotation (e.g. `#[offse(0x8)]`) would go
// unnoticed and the derive would silently skip laying out that field.

use ml2_mem::MemStruct;

#[derive(MemStruct)]
struct MissingOffset {
    #[offset(0x0)]
    header: u32,
    // Deliberately no #[offset(...)] here.
    body: u32,
}

fn main() {}
