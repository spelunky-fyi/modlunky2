import { useCallback, useEffect, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { listen } from "@tauri-apps/api/event";
import { writeText } from "@tauri-apps/plugin-clipboard-manager";
import { useToast } from "../shared/Toast";
import { useSetup } from "../shared/SetupContext";
import {
  ACCOUNT_LINK_EVENT,
  cancelAccountLink,
  startAccountLink,
  type LinkResult,
} from "../../lib/commands";

/**
 * The account-linking state machine, without any of its markup.
 *
 * Three places offer this now: the browse wall, the install modal, and
 * settings. Only one of them can be the place that remembers to cancel an
 * abandoned attempt, subscribe before starting so a fast approval is not
 * missed, and keep the URL around for when opening a browser silently fails.
 * So none of them own it and this does.
 */
export function useAccountLink(options: { onLinked?: () => void } = {}) {
  const { onLinked } = options;
  const toast = useToast();
  const { refresh } = useSetup();
  const [connecting, setConnecting] = useState(false);
  const [url, setUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Subscribed on mount rather than when an attempt starts, so approval
    // cannot land between the invoke resolving and a listener attaching.
    const unlisten = listen<LinkResult>(ACCOUNT_LINK_EVENT, (event) => {
      const result = event.payload;
      setConnecting(false);
      setUrl(null);
      if (result.status === "linked") {
        toast.success(`Connected as ${result.username}.`);
        void refresh();
        onLinked?.();
      } else if (result.status === "failed") {
        toast.error(result.message);
      }
    });
    return () => {
      void unlisten.then((off) => off());
    };
  }, [toast, refresh, onLinked]);

  // Abandon an in-flight attempt if this unmounts, rather than leaving a
  // listener holding a port for the full ten-minute timeout.
  useEffect(() => {
    return () => {
      void cancelAccountLink().catch(() => {});
    };
  }, []);

  const connect = useCallback(async () => {
    setConnecting(true);
    setCopied(false);
    try {
      const started = await startAccountLink();
      setUrl(started.url);
      await openUrl(started.url);
    } catch (err) {
      // The listener is running even when the browser refused to open, so this
      // keeps waiting rather than cancelling: the URL is still usable by hand,
      // which is the only route on a Steam Deck in Game Mode.
      toast.warning(
        "Couldn't open your browser. Copy the link below and open it yourself.",
      );
      console.error(err);
    }
  }, [toast]);

  const copy = useCallback(async () => {
    if (!url) return;
    try {
      await writeText(url);
      setCopied(true);
    } catch {
      toast.error("Couldn't copy the link.");
    }
  }, [url, toast]);

  const cancel = useCallback(() => {
    void cancelAccountLink().catch(() => {});
    setConnecting(false);
    setUrl(null);
  }, []);

  return { connecting, url, copied, connect, copy, cancel };
}
