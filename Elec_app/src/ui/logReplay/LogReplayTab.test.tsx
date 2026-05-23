import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { LogReplayTab } from "./LogReplayTab";

describe("LogReplayTab", () => {
  test("starts as a real uploader workspace, not a static preview with sample telemetry", () => {
    render(<LogReplayTab />);

    expect(screen.getByRole("heading", { name: "EMU 로그 재생" })).toBeInTheDocument();
    expect(screen.getByLabelText("CSV 로그 파일")).toBeInTheDocument();
    expect(screen.queryByText("test_run_0523.csv")).not.toBeInTheDocument();
    expect(screen.queryByText("MF-26 Replay")).not.toBeInTheDocument();
  });
});
