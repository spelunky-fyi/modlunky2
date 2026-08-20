//! The browse types are pinned against real responses from the spelunky.fyi
//! API, captured with `curl` and scrubbed of host and username.
//!
//! Deserialization is the whole risk surface for these structs: there is no
//! compiler checking that a Rust field name matches a Django serializer field,
//! and a rename or a newly nullable column on the server would otherwise show
//! up as an empty browse grid in front of a user rather than as a failing test.
//! `serde_json::from_str` on a captured body is the cheapest way to notice.

use ml2_mods::spelunkyfyi::http::{ModDetail, ModListing, Page};

const LIST: &str = include_str!("fixtures/list.json");
const DETAIL: &str = include_str!("fixtures/detail.json");

#[test]
fn a_real_list_response_deserializes() {
    let page: Page<ModListing> =
        serde_json::from_str(LIST).expect("list response should match Page<ModListing>");

    assert_eq!(page.count, 3);
    assert!(page.previous.is_none());
    assert!(page.next.is_some());

    let first = &page.results[0];
    assert_eq!(first.slug, "test-status");
    assert_eq!(first.game_display, "Spelunky 2");
    assert_eq!(
        first.mod_type_display.as_deref(),
        Some("Playable Character")
    );
    assert_eq!(first.submitter.username, "somebody");
    // A mod with no logo really does send null, which is why the field is an
    // Option rather than an empty string.
    assert!(first.logo.is_none());
    assert!(first.web_url.ends_with("/mods/m/test-status/"));
    assert!(first.latest_file.is_some());

    // Captured with ?include=preview_images, which is what the browse grid
    // always sends: the detail pane renders screenshots from the listing rather
    // than fetching each mod again.
    assert_eq!(first.preview_images.len(), 2);
    assert!(first.preview_images[0].image_url.contains("/mods/preview/"));
}

#[test]
fn a_listing_without_the_include_still_parses() {
    // preview_images is absent, not empty, when it was not asked for. A caller
    // that skips the include must not fail to deserialize.
    let without = LIST.replace("\"preview_images\"", "\"ignored_images\"");
    let page: Page<ModListing> =
        serde_json::from_str(&without).expect("a listing without previews should parse");
    assert!(page.results[0].preview_images.is_empty());
}

#[test]
fn a_real_detail_response_deserializes() {
    let detail: ModDetail =
        serde_json::from_str(DETAIL).expect("detail response should match ModDetail");

    assert_eq!(detail.slug, "test-status");
    assert_eq!(detail.mod_files.len(), 1);
    // The detail endpoint sends previews unconditionally; only the listing
    // gates them behind an include.
    assert_eq!(detail.preview_images.len(), 2);
    assert!(detail.latest_file.is_some());
}

#[test]
fn the_detail_type_ignores_the_prose_field() {
    // The server still sends `details`, the raw markdown, because the install
    // path's `Mod` struct needs it. `ModDetail` declares no such field and
    // serde drops unknown ones. Asserted rather than assumed: the app never
    // renders a stranger's markdown, so the deserialized value must offer no
    // way to reach it even by accident.
    assert!(DETAIL.contains("\"details\""));

    let detail: ModDetail = serde_json::from_str(DETAIL).expect("detail should parse");
    let round_tripped = serde_json::to_string(&detail).expect("detail should serialize");
    assert!(!round_tripped.contains("\"details\""));
    assert!(!round_tripped.contains("details_html"));
}

#[test]
fn a_null_mod_type_does_not_break_a_page() {
    // mod_type is null=True on the server. Before it was an Option, one mod
    // submitted without a type would fail the whole page.
    let with_null = LIST.replace("\"mod_type\": 1", "\"mod_type\": null");
    let page: Page<ModListing> =
        serde_json::from_str(&with_null).expect("a null mod_type should still parse");
    assert!(page.results[0].mod_type.is_none());
}
