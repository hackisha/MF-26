import { useState } from "react";
import type { Measurement } from "../domain/types";

interface NotesMeasurementsProps {
  targetId: string;
  onAddNote: (targetId: string, body: string) => void;
  onAddMeasurement: (measurement: Omit<Measurement, "id" | "measuredAt">) => void;
}

export function NotesMeasurements({ targetId, onAddNote, onAddMeasurement }: NotesMeasurementsProps) {
  const [note, setNote] = useState("");
  const [expectedValue, setExpectedValue] = useState("");
  const [measuredValue, setMeasuredValue] = useState("");

  return (
    <section className="panel notes-measurements">
      <h2>메모 / 측정 기록</h2>
      <label className="field">
        메모
        <textarea value={note} onChange={(event) => setNote(event.currentTarget.value)} />
      </label>
      <button type="button" onClick={() => onAddNote(targetId, note)}>
        메모 저장
      </button>
      <label className="field">
        예상값
        <input value={expectedValue} onChange={(event) => setExpectedValue(event.currentTarget.value)} />
      </label>
      <label className="field">
        실측값
        <input value={measuredValue} onChange={(event) => setMeasuredValue(event.currentTarget.value)} />
      </label>
      <button
        type="button"
        onClick={() =>
          onAddMeasurement({
            pinId: targetId,
            expectedValue,
            condition: "",
            measuredValue,
            status: "unknown",
            note: ""
          })
        }
      >
        측정 저장
      </button>
    </section>
  );
}
