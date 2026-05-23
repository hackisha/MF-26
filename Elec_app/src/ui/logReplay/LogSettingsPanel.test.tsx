import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { createDefaultLogReplaySettings } from "../../domain/logSettingsDefaults";
import { LogSettingsPanel } from "./LogSettingsPanel";

describe("LogSettingsPanel", () => {
  test("edits sensor scale and adds a free-form derived sensor", async () => {
    const user = userEvent.setup();
    const onSettingsChange = vi.fn();
    const settings = createDefaultLogReplaySettings([{ key: "RPM", label: "RPM", type: "number", unit: "rpm" }]);

    render(<LogSettingsPanel settings={settings} onSettingsChange={onSettingsChange} />);

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
});
