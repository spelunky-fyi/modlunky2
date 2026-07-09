//! Turn a `TrackerPayload` into the flat display string OBS Text
//! sources render. Every payload variant carries a `text` field; the
//! `text()` accessor on the enum handles the dispatch. Kept in its
//! own module so file writer + any future file-tail consumers stay in
//! sync on the empty / failure rendering.

use ml2_trackers::tracker::TrackerPayload;

pub fn payload_to_display(payload: &TrackerPayload) -> String {
    payload.text().to_string()
}
