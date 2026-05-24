import { useState } from "react";
import { publishSessionSnapshot } from "../state/sessionStore";

type PopoutButtonProps = {
  route: string;
};

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown window error.";
}

export function PopoutButton({ route }: PopoutButtonProps) {
  const [status, setStatus] = useState<"idle" | "opening" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const hasDesktopPopout = typeof window.mfLogAnalyzer?.popout === "function";
  const hasBrowserPopout = typeof window.open === "function";
  const canOpenWindow = hasDesktopPopout || hasBrowserPopout;

  async function handlePopout() {
    if (!canOpenWindow || status === "opening") return;

    setStatus("opening");
    setErrorMessage(null);
    try {
      if (hasDesktopPopout) {
        await publishSessionSnapshot().catch(() => undefined);
        await window.mfLogAnalyzer!.popout(route);
      } else {
        const opened = window.open(route, "_blank");
        if (!opened) throw new Error("Browser blocked the new window.");
        try {
          opened.opener = null;
        } catch {
          // Best-effort browser fallback hardening; opening the window is the primary action.
        }
      }
      setStatus("idle");
    } catch (error) {
      setErrorMessage(`Could not open a new window: ${messageFromError(error)}`);
      setStatus("error");
    }
  }

  return (
    <span className="popout-control">
      <button
        type="button"
        className="popout-button"
        onClick={() => void handlePopout()}
        disabled={status === "opening" || !canOpenWindow}
        title={status === "error" ? "New window failed" : "Open this view in a new window"}
        aria-label="Open this view in a new window"
        aria-busy={status === "opening"}
      >
        <span aria-hidden="true">+</span>
        <span className="popout-button-label">{status === "opening" ? "Opening..." : "New window"}</span>
      </button>
      {status === "error" ? (
        <span className="popout-status" role="alert">
          {errorMessage ?? "Could not open a new window."}
        </span>
      ) : null}
    </span>
  );
}
