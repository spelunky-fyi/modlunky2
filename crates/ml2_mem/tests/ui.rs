//! UI tests for the ml2_mem_derive proc-macros.
//!
//! Each `tests/ui/*.rs` fixture is a stand-alone Rust file expected to
//! FAIL to compile in a specific way, and its `.stderr` snapshot pins
//! the exact compiler / derive error the macros emit. Regenerate
//! snapshots with `TRYBUILD=overwrite cargo test -p ml2_mem --test ui`.
//!
//! The derives compile-error a lot of ways (missing #[offset], non-lit
//! discriminant, non-unit variant, missing #[repr], unsupported
//! `#[repr(C, packed)]`, MemStruct on an enum, etc). Without this
//! harness those failure modes are effectively unverified: a refactor
//! that changed the emitted message would go unnoticed until a real
//! user hit the miscompile.

#[test]
fn ui() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/*.rs");
}
