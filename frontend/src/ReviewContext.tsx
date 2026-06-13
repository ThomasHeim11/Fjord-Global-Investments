/**
 * App-level review context: runs and tracks the portfolio scan ("review") so
 * its progress and result persist across navigation. Exposes runReview,
 * stopReview, and the latest digest/error/notice via the useReview hook.
 */
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "./api";
import type { DigestResponse } from "./types";

interface ReviewState {
  digest: DigestResponse | null;
  running: boolean;
  error: string | null;
  notice: string | null;
  runReview: () => Promise<void>;
  stopReview: () => void;
}

const ReviewCtx = createContext<ReviewState | null>(null);

/**
 * Holds the review run at app level so it keeps going (and keeps showing
 * progress) even if you navigate to Register or PortfolioGPT while it works.
 */
export function ReviewProvider({ children }: { children: ReactNode }) {
  const [digest, setDigest] = useState<DigestResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Fetch the latest stored digest into state.
  const reload = useCallback(
    () => api.getDigest().then(setDigest).catch((e) => setError(String(e))),
    [],
  );

  useEffect(() => { reload(); }, [reload]);

  /**
   * Live re-scan first; fall back to replaying the cached scan if the AI is
   * rate-limited, so a result always appears. Abortable via stopReview().
   */
  const runReview = useCallback(async () => {
    const controller = new AbortController();
    abortRef.current = controller;
    setRunning(true);
    setError(null);
    setNotice(null);
    try {
      await api.triggerDigest(true, controller.signal);
      await reload();
    } catch {
      if (controller.signal.aborted) {
        // user pressed Stop — keep the last review on screen, no error
      } else {
        try {
          await api.triggerDigest(false, controller.signal);
          await reload();
          setNotice("The live scan was rate-limited, so this shows your last cached review. Try again in a moment for a fresh scan.");
        } catch (e2) {
          if (!controller.signal.aborted) setError(String(e2));
        }
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }, [reload]);

  /**
   * Truly stops the run: tells the backend to cancel (it unwinds without
   * saving) and aborts the request so the UI is freed immediately.
   */
  const stopReview = useCallback(() => {
    api.cancelDigest().catch(() => {});
    abortRef.current?.abort();
    setRunning(false);
    setNotice("Review stopped.");
  }, []);

  return (
    <ReviewCtx.Provider value={{ digest, running, error, notice, runReview, stopReview }}>
      {children}
    </ReviewCtx.Provider>
  );
}

/** Access the review context; throws if used outside a ReviewProvider. */
export function useReview(): ReviewState {
  const ctx = useContext(ReviewCtx);
  if (!ctx) throw new Error("useReview must be used within a ReviewProvider");
  return ctx;
}
