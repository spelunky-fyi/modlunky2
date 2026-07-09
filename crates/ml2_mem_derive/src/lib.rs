//! Derive macros for `ml2_mem`. Two shapes:
//!
//! - `#[derive(MemStruct)]` on named-field structs: generates
//!   `MemStruct::read_from` (fields read at `base + offset`) plus
//!   `MemType` (passthrough) plus `MemLayout` (SIZE = max of
//!   `offset + <FieldType as MemLayout>::SIZE`). Each field must carry
//!   exactly one `#[offset(N)]`; a missing offset is a compile error so
//!   schema mistakes fail at build time, not at runtime with a wrong
//!   field reading garbage.
//!
//! - `#[derive(MemEnum)]` on `#[repr(iN)]` / `#[repr(uN)]` enums with
//!   explicit variant discriminants: generates `MemType` (reads the
//!   primitive, matches to a variant, returns `MemError::BadEnum` on an
//!   unknown value) plus `MemLayout` (SIZE = primitive size). Enums
//!   without an explicit `#[repr]` or a variant without an explicit
//!   discriminant are rejected so the on-wire encoding is unambiguous.
//!
//! Example:
//!
//! ```ignore
//! use ml2_mem::{MemStruct, MemEnum};
//!
//! #[repr(i32)]
//! #[derive(Debug, Copy, Clone, PartialEq, MemEnum)]
//! pub enum Screen {
//!     Logo = 0,
//!     Intro = 1,
//!     Menu  = 2,
//! }
//!
//! #[derive(Debug, MemStruct)]
//! pub struct State {
//!     #[offset(0x30)] pub screen: Screen,
//!     #[offset(0x64)] pub time_total: u32,
//! }
//! ```

use proc_macro::TokenStream;
use quote::quote;
use syn::{Data, DeriveInput, Expr, Fields, LitInt, Meta, parse_macro_input};

// ---------------------------------------------------------------------
// #[derive(MemStruct)]
// ---------------------------------------------------------------------

#[proc_macro_derive(MemStruct, attributes(offset))]
pub fn derive_mem_struct(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    let struct_name = &input.ident;
    let (impl_generics, ty_generics, where_clause) = input.generics.split_for_impl();

    let Data::Struct(data) = &input.data else {
        return compile_error(
            &input.ident,
            "MemStruct only supports structs with named fields",
        );
    };
    let Fields::Named(fields) = &data.fields else {
        return compile_error(&input.ident, "MemStruct only supports named-field structs");
    };

    // For each field, find the #[offset(N)] attribute and pair it with
    // the field's ident + type. Missing #[offset] is a hard error rather
    // than a silent default so schema mistakes surface at compile time.
    let mut field_reads = Vec::with_capacity(fields.named.len());
    let mut field_ends = Vec::with_capacity(fields.named.len());
    for field in &fields.named {
        let ident = field.ident.as_ref().expect("named struct");
        let ty = &field.ty;
        let offset_attr = field.attrs.iter().find(|a| a.path().is_ident("offset"));
        let Some(attr) = offset_attr else {
            return compile_error(ident, &format!("field `{ident}` is missing #[offset(N)]"));
        };
        let offset_lit: LitInt = match &attr.meta {
            Meta::List(list) => match list.parse_args::<LitInt>() {
                Ok(lit) => lit,
                Err(err) => return err.to_compile_error().into(),
            },
            _ => {
                return compile_error(
                    ident,
                    "#[offset] expects a literal integer, e.g. #[offset(0x18)]",
                );
            }
        };
        field_reads.push(quote! {
            #ident: <#ty as ::ml2_mem::MemType>::read_from(
                process,
                base + #offset_lit as u64,
            )?
        });
        // For MemLayout auto-sizing: field_end = offset + FieldType::SIZE.
        // Struct SIZE is max(field_end) across all fields.
        field_ends.push(quote! {
            (#offset_lit as usize + <#ty as ::ml2_mem::MemLayout>::SIZE)
        });
    }

    // Fold field_ends into a chain of ct_max calls so SIZE is a real
    // const expr. Empty structs get SIZE = 0.
    let size_expr = if field_ends.is_empty() {
        quote! { 0usize }
    } else {
        let mut iter = field_ends.into_iter();
        let first = iter.next().unwrap();
        iter.fold(first, |acc, end| {
            quote! { ::ml2_mem::const_max(#acc, #end) }
        })
    };

    let expanded = quote! {
        impl #impl_generics ::ml2_mem::MemStruct for #struct_name #ty_generics
        #where_clause
        {
            fn read_from(
                process: &dyn ::ml2_mem::ReadProcess,
                base: u64,
            ) -> ::ml2_mem::Result<Self> {
                Ok(Self {
                    #(#field_reads),*
                })
            }
        }

        impl #impl_generics ::ml2_mem::MemType for #struct_name #ty_generics
        #where_clause
        {
            fn read_from(
                process: &dyn ::ml2_mem::ReadProcess,
                addr: u64,
            ) -> ::ml2_mem::Result<Self> {
                <Self as ::ml2_mem::MemStruct>::read_from(process, addr)
            }
        }

        impl #impl_generics ::ml2_mem::MemLayout for #struct_name #ty_generics
        #where_clause
        {
            const SIZE: usize = #size_expr;
        }
    };
    TokenStream::from(expanded)
}

// ---------------------------------------------------------------------
// #[derive(MemEnum)]
// ---------------------------------------------------------------------

#[proc_macro_derive(MemEnum)]
pub fn derive_mem_enum(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    let enum_name = &input.ident;
    let enum_name_str = enum_name.to_string();
    let (impl_generics, ty_generics, where_clause) = input.generics.split_for_impl();

    // Reject non-enums outright; the derive can't produce a sensible
    // read for anything else and a struct author probably wanted
    // MemStruct instead.
    let Data::Enum(data) = &input.data else {
        return compile_error(&input.ident, "MemEnum only supports enums");
    };

    // Sniff #[repr(iN)] / #[repr(uN)] to determine which primitive to
    // read on the wire. Reject implicit-repr enums since their layout
    // is compiler-dependent and reading them from another process is
    // fundamentally unsafe.
    let repr = match extract_repr(&input) {
        Ok(r) => r,
        Err(msg) => return compile_error(&input.ident, &msg),
    };

    // Every variant needs an explicit discriminant. Rust allows omitting
    // it (auto-incrementing) but game-state enums always carry a fixed
    // wire value; forgetting one would silently shift every subsequent
    // variant. Compile-error instead.
    let mut arms = Vec::with_capacity(data.variants.len());
    for variant in &data.variants {
        if !matches!(variant.fields, Fields::Unit) {
            return compile_error(
                &variant.ident,
                &format!(
                    "MemEnum variant `{}` must be a unit variant (no fields)",
                    variant.ident
                ),
            );
        }
        let Some((_, disc_expr)) = &variant.discriminant else {
            return compile_error(
                &variant.ident,
                &format!(
                    "MemEnum variant `{}` needs an explicit discriminant (e.g. `= 3`)",
                    variant.ident
                ),
            );
        };
        let disc_lit = match discriminant_as_lit(disc_expr) {
            Some(lit) => lit,
            None => {
                return compile_error(
                    &variant.ident,
                    "MemEnum variant discriminant must be a literal integer",
                );
            }
        };
        let variant_ident = &variant.ident;
        arms.push(quote! {
            #disc_lit => Self::#variant_ident
        });
    }

    let expanded = quote! {
        impl #impl_generics ::ml2_mem::MemType for #enum_name #ty_generics
        #where_clause
        {
            fn read_from(
                process: &dyn ::ml2_mem::ReadProcess,
                addr: u64,
            ) -> ::ml2_mem::Result<Self> {
                let raw = <#repr as ::ml2_mem::MemType>::read_from(process, addr)?;
                Ok(match raw {
                    #(#arms,)*
                    _ => return Err(::ml2_mem::MemError::BadEnum {
                        ty: #enum_name_str,
                        value: raw as i64,
                    }),
                })
            }
        }

        impl #impl_generics ::ml2_mem::MemLayout for #enum_name #ty_generics
        #where_clause
        {
            const SIZE: usize = <#repr as ::ml2_mem::MemLayout>::SIZE;
        }
    };
    TokenStream::from(expanded)
}

/// Pulls the primitive from `#[repr(iN)]` / `#[repr(uN)]`. Returns the
/// ident (e.g. `i32`) so the caller can splice it into a type position.
fn extract_repr(input: &DeriveInput) -> Result<proc_macro2::TokenStream, String> {
    for attr in &input.attrs {
        if !attr.path().is_ident("repr") {
            continue;
        }
        // Only Meta::List(...) shape is valid for #[repr(...)]; parse
        // the inner ident. Multi-ident reprs (e.g. #[repr(C, packed)])
        // aren't currently supported.
        if let Meta::List(list) = &attr.meta {
            let text = list.tokens.to_string();
            let text = text.trim();
            match text {
                "i8" | "i16" | "i32" | "i64" | "u8" | "u16" | "u32" | "u64" => {
                    let ident: proc_macro2::TokenStream = text.parse().unwrap();
                    return Ok(ident);
                }
                _ => {
                    return Err(format!(
                        "MemEnum only supports #[repr(iN)] / #[repr(uN)], got `{}`",
                        text
                    ));
                }
            }
        }
    }
    Err("MemEnum requires an explicit #[repr(iN)] or #[repr(uN)]".into())
}

/// Discriminants are Rust expressions; only `= <integer literal>` is
/// accepted so game-state constants don't drift under const-eval.
fn discriminant_as_lit(expr: &Expr) -> Option<LitInt> {
    match expr {
        Expr::Lit(lit) => match &lit.lit {
            syn::Lit::Int(i) => Some(i.clone()),
            _ => None,
        },
        // Support unary minus for signed enums like `= -1`.
        Expr::Unary(u) if matches!(u.op, syn::UnOp::Neg(_)) => {
            if let Expr::Lit(lit) = &*u.expr
                && let syn::Lit::Int(i) = &lit.lit
            {
                // Splice the sign back in so downstream `match` arms
                // see `-1` and not `1`.
                let text = format!("-{}", i.base10_digits());
                return syn::parse_str::<LitInt>(&text).ok();
            }
            None
        }
        _ => None,
    }
}

fn compile_error(spanned: &impl quote::ToTokens, msg: &str) -> TokenStream {
    syn::Error::new_spanned(spanned, msg)
        .to_compile_error()
        .into()
}
