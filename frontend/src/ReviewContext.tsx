import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import type { DigestResponse } from "./types";

interface ReviewState {
  digest: DigestResponse | null;
  running: boolean;
  error: string | null;
  notice: string | null;
  runReview: () => Promise<void>;
}

const ReviewCtx = createContext<ReviewState | null>(null);

// Holds the review run at app level so it keeps going (and keeps showing
// progress) even if you navigate to Register or PortfolioGPT while it works.
export function ReviewProvider({ children }: { children: ReactNode }) {
  const [digest, setDigest] = useState<DigestResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const reload = useCallback(
    () => api.getDigest().then(setDigest).catch((e) => setError(String(e))),
    [],
  );

  useEffect(() => { reload(); }, [reload]);

  // Live re-scan first; fall back to replaying the cached scan if the AI is
  // rate-limited, so a result always appears.
  const runReview = useCallback(async () => {
    setRunning(true);
    setError(null);
    setNotice(null);
    try {
      await api.triggerDigest(true);
      await reload();
    } catch {
      try {
        await api.triggerDigest(false);
        await reload();
        setNotice("The live scan was rate-limited, so this shows your last cached review. Try again in a moment for a fresh scan.");
      } catch (e2) {
        setError(String(e2));
      }
    } finally {
      setRunning(false);
    }
  }, [reload]);

  return (
    <ReviewCtx.Provider value={{ digest, running, error, notice, runReview }}>
      {children}
    </ReviewCtx.Provider>
  );
}

export function useReview(): ReviewState {
  const ctx = useContext(ReviewCtx);
  if (!ctx) throw new Error("useReview must be used within a ReviewProvider");
  return ctx;
}
