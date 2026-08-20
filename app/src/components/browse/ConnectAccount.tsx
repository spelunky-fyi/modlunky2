import { Check, Copy, KeyRound, Loader2 } from "lucide-react";
import { useSetup } from "../shared/SetupContext";
import { useAccountLink } from "./useAccountLink";
import "./ConnectAccount.css";

export function ConnectAccount() {
  const { openSettings } = useSetup();
  const { connecting, url, copied, connect, copy, cancel } = useAccountLink();

  return (
    <div className="connect-account">
      <div className="connect-card">
        <div className="connect-icon">
          <KeyRound size={30} aria-hidden="true" />
        </div>
        <h2 className="connect-title">Connect your spelunky.fyi account</h2>
        <p className="connect-body">
          Browsing mods requires connecting your spelunky.fyi account.
        </p>

        {connecting ? (
          <>
            <p className="connect-waiting">
              <Loader2 size={16} className="connect-spin" aria-hidden="true" />
              Waiting for approval in your browser&hellip;
            </p>
            {url && (
              <div className="connect-url">
                <input type="text" value={url} readOnly spellCheck={false} />
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => void copy()}
                >
                  {copied ? (
                    <Check size={14} aria-hidden="true" />
                  ) : (
                    <Copy size={14} aria-hidden="true" />
                  )}
                  {copied ? "Copied" : "Copy link"}
                </button>
              </div>
            )}
            <p className="connect-note">
              {/* Game Mode on a Steam Deck has no desktop session for the app
                  to hand a URL to, so the button quietly does nothing there.
                  The link has to be openable by hand, and it has to be opened
                  on this machine: the approval comes back to a port here. */}
              If your browser didn't open automatically, open on this computer.
            </p>
            <button type="button" className="btn btn-ghost" onClick={cancel}>
              Cancel
            </button>
          </>
        ) : (
          <div className="connect-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void connect()}
            >
              Connect account
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => openSettings("apiToken")}
            >
              Paste a token instead
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
