//! Linking a spelunky.fyi account without making the user copy a token.
//!
//! The user clicks Connect, a browser opens on the site's consent page, and the
//! token lands in the config. The awkward part is getting the result back from
//! the browser into this process, and the shape of that answer is dictated by
//! how Modlunky2 ships: one self-contained exe, no installer, dropped wherever
//! the user likes and moved around freely.
//!
//! That rules out a `modlunky2://` scheme. On Windows a scheme is an absolute
//! exe path in `HKCU\Software\Classes`, which goes stale the moment someone
//! relocates the exe, and it needs single-instance handling because Windows
//! answers a scheme by launching a *second* process. On Linux we ship an
//! AppImage, which installs no `.desktop` entry, so there would be no handler
//! at all. The one thing a scheme buys, waking a closed app from a link, is
//! worth nothing here: this flow only ever starts from a button in the running
//! app.
//!
//! So instead we bind an ephemeral port on loopback and hand the site a
//! `redirect_uri` pointing at it. No registration, nothing to go stale, and it
//! is what RFC 8252 recommends for native apps. PKCE rides along: the verifier
//! never leaves this process, so an intercepted code is useless.
//!
//! `start_account_link` deliberately returns the URL instead of only opening
//! it. Opening a browser fails on a Steam Deck in Game Mode, where there is no
//! desktop session for `xdg-open` to talk to, so the UI needs something to show
//! the user that they can copy. The same URL works whenever they get to a
//! browser on this machine.

use std::sync::Mutex;
use std::time::Duration;

use axum::Router;
use axum::extract::{Query, State as AxumState};
use axum::response::{Html, IntoResponse};
use axum::routing::get;
use base64::Engine as _;
use ml2_mods::spelunkyfyi::http::{DEFAULT_SERVICE_ROOT, exchange_app_link_code};
// rand 0.10 splits the trait: `Rng` is the re-exported core trait, and the
// sampling helpers like `random_range` live on `RngExt`.
use rand::RngExt as _;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use tauri::{AppHandle, Emitter, Manager as _, Runtime};
use tokio::sync::oneshot;

/// Emitted once, when a link attempt finishes for any reason.
const LINK_EVENT: &str = "account-link";

/// How long the listener waits before giving up. Long enough to create an
/// account and verify an email in another tab, short enough that a forgotten
/// attempt does not hold a port for the rest of the session.
const LINK_TIMEOUT: Duration = Duration::from_secs(10 * 60);

/// RFC 7636 allows 43-128 characters. 64 is comfortably inside that and gives
/// 384 bits of entropy through the unreserved alphabet below.
const VERIFIER_LENGTH: usize = 64;
const STATE_LENGTH: usize = 32;

/// The `unreserved` set from RFC 7636, which is also what the server validates
/// the verifier against.
const UNRESERVED: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";

/// The in-flight attempt, if any. Only one can be running: a second Connect
/// click cancels the first rather than leaving an orphaned listener holding a
/// port and a stale verifier.
static SESSION: Mutex<Option<Session>> = Mutex::new(None);

struct Session {
    cancel: oneshot::Sender<()>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct LinkStart {
    /// Open this, and also show it: see the Steam Deck note above.
    pub url: String,
    pub port: u16,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase", tag = "status")]
pub enum LinkResult {
    Linked { username: String },
    Failed { message: String },
    Cancelled,
}

/// Query params the site appends to our loopback redirect.
#[derive(Debug, Deserialize)]
struct Callback {
    code: Option<String>,
    state: Option<String>,
}

#[derive(Clone)]
struct CallbackState {
    /// `Some` until the first callback consumes it. An Arc<Mutex<Option<_>>>
    /// because axum handlers get a clone of the state per request and a oneshot
    /// sender can only be used once.
    tx: std::sync::Arc<Mutex<Option<oneshot::Sender<Callback>>>>,
}

fn random_string(len: usize) -> String {
    let mut rng = rand::rng();
    (0..len)
        .map(|_| UNRESERVED[rng.random_range(0..UNRESERVED.len())] as char)
        .collect()
}

fn code_challenge(verifier: &str) -> String {
    let digest = Sha256::digest(verifier.as_bytes());
    base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(digest)
}

fn service_root() -> String {
    crate::config::load()
        .spelunky_fyi_root
        .map(|r| r.trim().to_string())
        .filter(|r| !r.is_empty())
        .unwrap_or_else(|| DEFAULT_SERVICE_ROOT.to_string())
}

/// Colours lifted from the app's own tokens in `App.css`, so the tab the user
/// is bounced into looks like the app they came from rather than a stock white
/// page at the end of a dark-themed flow.
struct Palette {
    scheme: &'static str,
    bg: &'static str,
    card: &'static str,
    border: &'static str,
    fg: &'static str,
    muted: &'static str,
    accent: &'static str,
}

const DARK: Palette = Palette {
    scheme: "dark",
    bg: "#1a1a1e",
    card: "#23232a",
    border: "#34343d",
    fg: "#e6e6ea",
    muted: "#8a8a95",
    accent: "#f0a55a",
};

const LIGHT: Palette = Palette {
    scheme: "light",
    bg: "#f4f4f6",
    card: "#ffffff",
    border: "#d7d7de",
    fg: "#1c1c22",
    muted: "#63636e",
    accent: "#a35f16",
};

/// The app's configured theme, which is what this page should match. Not
/// `prefers-color-scheme`: someone running the app in dark on a light desktop
/// picked dark, and this page is the tail end of an app flow.
fn palette() -> &'static Palette {
    if crate::config::load().theme == "light" {
        &LIGHT
    } else {
        &DARK
    }
}

/// The page the browser lands on once the app has the code. Served by us rather
/// than the site because only this side knows whether the exchange worked.
///
/// Written with placeholders rather than `format!` because a stylesheet is
/// mostly braces, and escaping every one of them is how this ends up broken and
/// unreadable at the same time.
fn closing_page(heading: &str, detail: &str) -> Html<String> {
    Html(render_page(palette(), heading, detail))
}

/// Split out from `closing_page` so it can be tested without reading config.
fn render_page(p: &Palette, heading: &str, detail: &str) -> String {
    const TEMPLATE: &str = r#"<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__HEADING__</title>
<style>
  /* Tells the browser to paint its own chrome, scrollbars included, to match. */
  :root { color-scheme: __SCHEME__; }
  html, body { height: 100%; }
  body {
    margin: 0;
    background: __BG__;
    color: __FG__;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
    box-sizing: border-box;
  }
  .card {
    background: __CARD__;
    border: 1px solid __BORDER__;
    border-radius: 10px;
    padding: 2rem 2.5rem;
    text-align: center;
    max-width: 26rem;
  }
  h1 { font-size: 1.25rem; margin: 0 0 .5rem; color: __ACCENT__; }
  p { margin: 0; color: __MUTED__; line-height: 1.5; }
</style>
<body>
  <div class="card">
    <h1>__HEADING__</h1>
    <p>__DETAIL__</p>
  </div>
</body>"#;

    TEMPLATE
        .replace("__SCHEME__", p.scheme)
        .replace("__BG__", p.bg)
        .replace("__CARD__", p.card)
        .replace("__BORDER__", p.border)
        .replace("__FG__", p.fg)
        .replace("__MUTED__", p.muted)
        .replace("__ACCENT__", p.accent)
        .replace("__HEADING__", heading)
        .replace("__DETAIL__", detail)
}

async fn handle_callback(
    AxumState(state): AxumState<CallbackState>,
    Query(params): Query<Callback>,
) -> impl IntoResponse {
    let sender = state.tx.lock().unwrap().take();
    match sender {
        Some(tx) => {
            let had_code = params.code.is_some();
            let _ = tx.send(params);
            if had_code {
                closing_page("Modlunky2 is connected", "You can close this tab.")
            } else {
                closing_page("Connection cancelled", "You can close this tab.")
            }
        }
        // A refresh, or the browser following the redirect twice. The first
        // callback already took the code, so say something harmless.
        None => closing_page("Already done", "You can close this tab."),
    }
}

/// Begin an account link. Returns immediately with the URL to open, leaving a
/// background task waiting for the browser to come back; the outcome arrives as
/// an `account-link` event.
#[tauri::command]
pub async fn start_account_link<R: Runtime>(app: AppHandle<R>) -> Result<LinkStart, String> {
    cancel_account_link();

    let verifier = random_string(VERIFIER_LENGTH);
    let expected_state = random_string(STATE_LENGTH);
    let challenge = code_challenge(&verifier);

    // Port 0 lets the OS pick a free one. Loopback only, so this never becomes
    // a listening socket on the network and never trips a firewall prompt.
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .map_err(|e| format!("Couldn't open a local port: {e}"))?;
    let port = listener
        .local_addr()
        .map_err(|e| format!("Couldn't read the local port: {e}"))?
        .port();

    let root = service_root();
    let redirect_uri = format!("http://127.0.0.1:{port}/callback");
    let mut url = url::Url::parse(&root).map_err(|e| format!("Invalid spelunky.fyi root: {e}"))?;
    url.set_path("/accounts/link/modlunky2/");
    url.query_pairs_mut()
        .append_pair("code_challenge", &challenge)
        .append_pair("code_challenge_method", "S256")
        .append_pair("state", &expected_state)
        .append_pair("redirect_uri", &redirect_uri);
    let url = url.to_string();

    let (result_tx, result_rx) = oneshot::channel::<Callback>();
    let (cancel_tx, cancel_rx) = oneshot::channel::<()>();
    let (shutdown_tx, shutdown_rx) = oneshot::channel::<()>();

    let router = Router::new()
        .route("/callback", get(handle_callback))
        .with_state(CallbackState {
            tx: std::sync::Arc::new(Mutex::new(Some(result_tx))),
        });

    tokio::spawn(async move {
        let _ = axum::serve(listener, router)
            .with_graceful_shutdown(async move {
                let _ = shutdown_rx.await;
            })
            .await;
    });

    tokio::spawn(async move {
        let outcome = wait_for_callback(result_rx, cancel_rx, &expected_state, &verifier, &root)
            .await
            .unwrap_or_else(|message| LinkResult::Failed { message });

        // Drop the listener before announcing: by the time the UI reacts, the
        // port is already free.
        let _ = shutdown_tx.send(());
        SESSION.lock().unwrap().take();

        if let LinkResult::Linked { .. } = &outcome {
            // Both halves of what Settings does on a credentials change, and
            // both are needed. The mod manager captures its API client once, at
            // construction, so without a rebuild it keeps the `None` it was
            // built with at boot and the next install fails with "Tried to
            // access remote mod, but API isn't configured" - long after the
            // step that caused it, and with browsing working fine in the
            // meantime, because that builds its client per call.
            {
                let state = app.state::<crate::state::AppState>();
                crate::mods::rebuild(&state, &app);
            }
            // Reconnect the push-install socket with the token we just stored,
            // so the site's "Install in modlunky2" button works without a
            // restart.
            crate::fyi_ws::refresh(&app);
        }
        let _ = app.emit(LINK_EVENT, outcome);
    });

    *SESSION.lock().unwrap() = Some(Session { cancel: cancel_tx });

    Ok(LinkStart { url, port })
}

/// Waits for one of: the browser calling back, the user cancelling, or the
/// timeout. Returns `Err` with a user-facing message for anything that went
/// wrong after a code actually arrived.
async fn wait_for_callback(
    result_rx: oneshot::Receiver<Callback>,
    cancel_rx: oneshot::Receiver<()>,
    expected_state: &str,
    verifier: &str,
    root: &str,
) -> Result<LinkResult, String> {
    let callback = tokio::select! {
        received = result_rx => match received {
            Ok(callback) => callback,
            // Server died without a callback.
            Err(_) => return Ok(LinkResult::Cancelled),
        },
        _ = cancel_rx => return Ok(LinkResult::Cancelled),
        () = tokio::time::sleep(LINK_TIMEOUT) => {
            return Err("Connection timed out. Try again.".to_string());
        }
    };

    // Anything on loopback can hit this port, so the code is only trusted when
    // it arrives with the state we generated. Mismatch means the request did
    // not come from the browser we sent.
    if callback.state.as_deref() != Some(expected_state) {
        return Err("Unexpected response. Try connecting again.".to_string());
    }

    let Some(code) = callback.code.filter(|c| !c.is_empty()) else {
        return Ok(LinkResult::Cancelled);
    };

    let client = reqwest::Client::new();
    let token = exchange_app_link_code(root, &code, verifier, &client)
        .await
        .map_err(|e| format!("spelunky.fyi rejected the connection: {e}"))?;

    crate::config::apply_patch(crate::config::ConfigPatch {
        spelunky_fyi_api_token: Some(token.token),
        ..Default::default()
    })
    .map_err(|e| format!("Couldn't save the token: {e}"))?;

    Ok(LinkResult::Linked {
        username: token.username,
    })
}

/// Abandon any in-flight attempt. Safe to call when nothing is running.
#[tauri::command]
pub fn cancel_account_link() {
    let session = SESSION.lock().unwrap().take();
    if let Some(session) = session {
        let _ = session.cancel.send(());
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn challenge_matches_the_rfc_7636_worked_example() {
        // Straight from RFC 7636 appendix B, which is the only way to be sure
        // this agrees with the server's independent implementation.
        let verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";
        assert_eq!(
            code_challenge(verifier),
            "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
        );
    }

    #[test]
    fn verifiers_use_only_unreserved_characters() {
        let verifier = random_string(VERIFIER_LENGTH);
        assert_eq!(verifier.len(), VERIFIER_LENGTH);
        assert!(verifier.bytes().all(|b| UNRESERVED.contains(&b)));
    }

    #[test]
    fn verifiers_are_not_repeated() {
        assert_ne!(
            random_string(VERIFIER_LENGTH),
            random_string(VERIFIER_LENGTH)
        );
    }

    /// Drives `wait_for_callback` with a callback that never needs the network,
    /// so these cover the decisions made before any exchange is attempted.
    async fn callback_outcome(callback: Callback, expected_state: &str) -> Result<LinkResult, String> {
        let (tx, rx) = oneshot::channel();
        let (_cancel_tx, cancel_rx) = oneshot::channel();
        tx.send(callback).expect("receiver is alive");
        wait_for_callback(rx, cancel_rx, expected_state, "verifier", "https://example.invalid").await
    }

    #[test]
    fn the_closing_page_leaves_no_placeholder_behind() {
        // The failure mode of a placeholder template is a typo shipping a
        // literal __BG__ into the stylesheet, which compiles and looks fine
        // until someone actually opens the page.
        for p in [&DARK, &LIGHT] {
            let html = render_page(p, "Heading", "Detail");
            assert!(
                !html.contains("__"),
                "unreplaced placeholder in the {} page",
                p.scheme
            );
            assert!(html.contains(p.bg));
            assert!(html.contains("Heading"));
            assert!(html.contains("Detail"));
        }
    }

    #[test]
    fn the_two_themes_actually_differ() {
        assert_ne!(
            render_page(&DARK, "H", "D"),
            render_page(&LIGHT, "H", "D")
        );
    }

    #[tokio::test]
    async fn a_mismatched_state_is_rejected_before_the_code_is_used() {
        // Anything on the machine can reach a loopback port, so the code is
        // only trusted when it arrives with the state we generated. Without
        // this check, another local process could feed us its own code.
        let result = callback_outcome(
            Callback {
                code: Some("stolen".into()),
                state: Some("not-ours".into()),
            },
            "ours",
        )
        .await;

        assert!(result.is_err(), "a foreign state must not be accepted");
    }

    #[tokio::test]
    async fn a_missing_state_is_rejected() {
        let result = callback_outcome(
            Callback {
                code: Some("code".into()),
                state: None,
            },
            "ours",
        )
        .await;

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn a_callback_without_a_code_is_a_cancellation() {
        // How the site reports "the user said no": right state, no code. That
        // is not an error worth showing as one.
        let result = callback_outcome(
            Callback {
                code: None,
                state: Some("ours".into()),
            },
            "ours",
        )
        .await;

        assert!(matches!(result, Ok(LinkResult::Cancelled)));
    }

    #[tokio::test]
    async fn cancelling_beats_a_callback_that_never_comes() {
        let (_tx, rx) = oneshot::channel::<Callback>();
        let (cancel_tx, cancel_rx) = oneshot::channel();
        cancel_tx.send(()).expect("receiver is alive");

        let result =
            wait_for_callback(rx, cancel_rx, "ours", "verifier", "https://example.invalid").await;

        assert!(matches!(result, Ok(LinkResult::Cancelled)));
    }
}
