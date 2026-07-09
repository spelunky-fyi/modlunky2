import { useEffect, useState } from "react";
import { getModLogo } from "../lib/commands";

// Session-lived cache keyed by mod id. Data URLs are cheap to hold and
// avoiding the IPC roundtrip per row scroll is worth it. Cleared on app
// reload; individual entries do not invalidate on mod update yet.
const logoCache = new Map<string, string | null>();

export function useModLogo(id: string): string | null {
  const cached = logoCache.has(id) ? logoCache.get(id) ?? null : null;
  const [url, setUrl] = useState<string | null>(cached);

  useEffect(() => {
    if (logoCache.has(id)) {
      setUrl(logoCache.get(id) ?? null);
      return;
    }
    let cancelled = false;
    getModLogo(id)
      .then((u) => {
        logoCache.set(id, u ?? null);
        if (!cancelled) setUrl(u ?? null);
      })
      .catch(() => {
        logoCache.set(id, null);
        if (!cancelled) setUrl(null);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return url;
}
