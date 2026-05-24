import { useState } from "react";
import { publishSessionSnapshot } from "../state/sessionStore";

type PopoutButtonProps = {
  route: string;
};

export function PopoutButton({ route }: PopoutButtonProps) {
  const [status, setStatus] = useState<"idle" | "opening" | "error">("idle");

  async function handlePopout() {
    const popout = window.mfLogAnalyzer?.popout;
    if (!popout || status === "opening") return;

    setStatus("opening");
    try {
      await publishSessionSnapshot();
      await popout(route);
      setStatus("idle");
    } catch {
      setStatus("error");
    }
  }

  return (
    <button
      type="button"
      className="popout-button"
      onClick={() => void handlePopout()}
      disabled={status === "opening" || !window.mfLogAnalyzer?.popout}
      title={status === "error" ? "Pop-out failed" : "Open this view in a new window"}
      aria-label="Open this view in a new window"
      aria-busy={status === "opening"}
    >
      <span aria-hidden="true">+</span>
      <span className="popout-button-label">Pop out</span>
      <span className="sr-only" aria-live="polite">
        {status === "opening" ? "Opening view" : status === "error" ? "Pop-out failed" : ""}
      </span>
    </button>
  );
}
