import { useState } from "react";
import { publishSessionSnapshot } from "../state/sessionStore";

type PopoutButtonProps = {
  route: string;
};

export function PopoutButton({ route }: PopoutButtonProps) {
  const [status, setStatus] = useState<"idle" | "opening" | "error">("idle");
  const hasDesktopPopout = typeof window.mfLogAnalyzer?.popout === "function";
  const hasBrowserPopout = typeof window.open === "function";
  const canOpenWindow = hasDesktopPopout || hasBrowserPopout;

  async function handlePopout() {
    if (!canOpenWindow || status === "opening") return;

    setStatus("opening");
    try {
      if (hasDesktopPopout) {
        await publishSessionSnapshot();
        await window.mfLogAnalyzer!.popout(route);
      } else {
        const opened = window.open(route, "_blank", "noopener,noreferrer");
        if (!opened) throw new Error("Browser blocked the new window.");
      }
      setStatus("idle");
    } catch {
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
          Could not open a new window.
        </span>
      ) : null}
    </span>
  );
}
