import { KeyRound } from "lucide-react";
import { useSetup } from "../shared/SetupContext";
import "./ReconnectPrompt.css";

interface Props {
  message: string;
  /** Retry the thing that failed, once the user has reconnected. */
  onRetry?: () => void;
}

/**
 * Shown when spelunky.fyi refuses our credentials.
 *
 * The app cannot tell in advance that a token has stopped working: nothing
 * notifies it when someone resets one on the website, so the first sign is a
 * 401 in the middle of whatever the user was doing. That makes it worth naming
 * the cause rather than showing a status code, and worth carrying the fix
 * rather than leaving them to guess which setting is wrong.
 */
export function ReconnectPrompt({ message, onRetry }: Props) {
  const { openSettings } = useSetup();

  return (
    <div className="reconnect">
      <KeyRound size={22} aria-hidden="true" />
      <div className="reconnect-text">
        <p className="reconnect-message">{message}</p>
        <p className="reconnect-hint">
          Reconnect your account to continue using spelunky.fyi features.
        </p>
      </div>
      <div className="reconnect-actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => openSettings("apiToken")}
        >
          Reconnect account
        </button>
        {onRetry && (
          <button type="button" className="btn btn-ghost" onClick={onRetry}>
            Try again
          </button>
        )}
      </div>
    </div>
  );
}
