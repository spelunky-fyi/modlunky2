import { Check, Copy, Loader2 } from "lucide-react";
import { useAccountLink } from "./useAccountLink";
import "./ConnectInline.css";

interface Props {
  /** Text for the idle button. The surrounding copy differs per host. */
  label?: string;
  /** Rendered next to Connect, for the host's own alternative action. */
  children?: React.ReactNode;
  /** Fired once a link succeeds. A host holding its own copy of the config
   *  needs this: the token changes underneath it, and saving a stale copy
   *  afterwards would overwrite what was just linked. */
  onLinked?: () => void;
}

/**
 * The link flow in a form-sized box, for the install modal and settings.
 *
 * `ConnectAccount` is the same flow as a full-page wall. Both exist because the
 * browse tab has nothing else to show until an account is connected, whereas
 * these two are one option among several on a screen that already works.
 */
export function ConnectInline({
  label = "Connect account",
  children,
  onLinked,
}: Props) {
  const { connecting, url, copied, connect, copy, cancel } = useAccountLink({
    onLinked,
  });

  if (!connecting) {
    return (
      <div className="connect-inline-actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void connect()}
        >
          {label}
        </button>
        {children}
      </div>
    );
  }

  return (
    <div className="connect-inline">
      <p className="connect-inline-waiting">
        <Loader2 size={14} className="connect-inline-spin" aria-hidden="true" />
        Waiting for approval in your browser&hellip;
      </p>
      {url && (
        <div className="connect-inline-url">
          <input type="text" value={url} readOnly spellCheck={false} />
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => void copy()}
          >
            {copied ? (
              <Check size={13} aria-hidden="true" />
            ) : (
              <Copy size={13} aria-hidden="true" />
            )}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      )}
      <p className="connect-inline-note">
        {/* Game Mode on a Steam Deck has no desktop session to hand a URL to,
            so the button does nothing there and the link has to be openable by
            hand. It has to be opened on this machine: the approval comes back
            to a port here. */}
        If your browser didn't open automatically, open on this computer.
      </p>
      <button type="button" className="btn btn-ghost" onClick={cancel}>
        Cancel
      </button>
    </div>
  );
}
