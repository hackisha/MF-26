import type { ChangeEvent } from "react";
import type { OverlayPreset, VehicleProfile } from "../domain/types";

type ChannelPickerProps = {
  profile: VehicleProfile;
  selectedOverlay: OverlayPreset | null;
  onOverlayChange: (overlay: OverlayPreset | null) => void;
};

export function ChannelPicker({ profile, selectedOverlay, onOverlayChange }: ChannelPickerProps) {
  const overlays = profile.overlays;
  const selectedOverlayId = selectedOverlay?.id ?? overlays[0]?.id ?? "";

  function handleOverlayChange(event: ChangeEvent<HTMLSelectElement>) {
    const overlay = overlays.find((candidate) => candidate.id === event.target.value) ?? null;
    onOverlayChange(overlay);
  }

  return (
    <label className="field-row">
      <span>Overlay preset</span>
      <select value={selectedOverlayId} onChange={handleOverlayChange} disabled={overlays.length === 0}>
        {overlays.length === 0 ? (
          <option value="">No overlays configured</option>
        ) : (
          overlays.map((overlay) => (
            <option key={overlay.id} value={overlay.id}>
              {overlay.name}
            </option>
          ))
        )}
      </select>
    </label>
  );
}
