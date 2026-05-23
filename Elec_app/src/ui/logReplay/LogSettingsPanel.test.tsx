import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, test, vi } from "vitest";
import { createDefaultLogReplaySettings } from "../../domain/logSettingsDefaults";
import type { LogReplaySettings } from "../../domain/logSettingsTypes";
import { LogSettingsPanel } from "./LogSettingsPanel";

function SettingsHarness({ initial, onChange }: { initial: LogReplaySettings; onChange: (settings: LogReplaySettings) => void }) {
  const [settings, setSettings] = useState(initial);
  return (
    <LogSettingsPanel
      settings={settings}
      onSettingsChange={(next) => {
        setSettings(next);
        onChange(next);
      }}
    />
  );
}

describe("LogSettingsPanel", () => {
  test("edits sensor scale and adds a free-form derived sensor", async () => {
    const user = userEvent.setup();
    const onSettingsChange = vi.fn();
    const settings = createDefaultLogReplaySettings([{ key: "RPM", label: "RPM", type: "number", unit: "rpm" }]);

    render(<SettingsHarness initial={settings} onChange={onSettingsChange} />);

    await user.clear(screen.getByLabelText("RPM 배율"));
    await user.type(screen.getByLabelText("RPM 배율"), "0.001");
    expect(onSettingsChange).toHaveBeenCalled();

    await user.type(screen.getByLabelText("새 센서 이름"), "RPM k");
    await user.type(screen.getByLabelText("새 센서 수식"), "RPM / 1000");
    await user.click(screen.getByRole("button", { name: "수식 센서 추가" }));

    expect(onSettingsChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        derivedSensors: expect.arrayContaining([expect.objectContaining({ label: "RPM k", expression: "RPM / 1000" })]),
      }),
    );
  });

  test("edits anomaly event detection criteria", async () => {
    const user = userEvent.setup();
    const onSettingsChange = vi.fn();
    const settings = createDefaultLogReplaySettings();

    render(<SettingsHarness initial={settings} onChange={onSettingsChange} />);

    await user.clear(screen.getByLabelText("오일 압력 낮음 감지식"));
    await user.type(screen.getByLabelText("오일 압력 낮음 감지식"), "OilPressure_bar < 1.4");
    await user.selectOptions(screen.getByLabelText("오일 압력 낮음 심각도"), "warning");

    expect(onSettingsChange).toHaveBeenCalledWith(
      expect.objectContaining({
        eventRules: expect.arrayContaining([
          expect.objectContaining({ id: "low-oil-pressure", expression: "OilPressure_bar < 1.4" }),
        ]),
      }),
    );
    expect(onSettingsChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        eventRules: expect.arrayContaining([expect.objectContaining({ id: "low-oil-pressure", severity: "warning" })]),
      }),
    );
  });
});
