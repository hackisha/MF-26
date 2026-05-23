import type { Attachment, Component, Measurement, Note } from "../domain/types";

interface ComponentInfoPanelProps {
  component: Component | null;
  notes: Note[];
  measurements: Measurement[];
  attachments: Attachment[];
}

export function ComponentInfoPanel({ component, notes, measurements, attachments }: ComponentInfoPanelProps) {
  if (!component) {
    return (
      <aside className="panel info-panel">
        <h2>부품 정보</h2>
        <p className="muted">부품을 선택하면 정보가 표시됩니다.</p>
      </aside>
    );
  }

  const componentNotes = notes.filter((note) => note.targetId === component.id);
  const componentAttachments = attachments.filter((attachment) => attachment.targetId === component.id);
  const componentMeasurements = measurements.filter((measurement) =>
    component.pins.some((pin) => pin.id === measurement.pinId)
  );

  return (
    <aside className="panel info-panel">
      <h2>{component.alias || component.rawName}</h2>
      <dl>
        <dt>분류</dt>
        <dd>{component.confirmedRole ?? component.autoRole}</dd>
        <dt>핀 수</dt>
        <dd>{component.pins.length}</dd>
        <dt>원본 이름</dt>
        <dd>{component.symbolName || component.packageName}</dd>
      </dl>
      <h3>데이터시트</h3>
      {componentAttachments.length > 0 ? (
        <ul>{componentAttachments.map((item) => <li key={item.id}>{item.label}</li>)}</ul>
      ) : (
        <p className="muted">등록된 데이터시트가 없습니다.</p>
      )}
      <h3>메모</h3>
      {componentNotes.length > 0 ? (
        <ul>{componentNotes.map((note) => <li key={note.id}>{note.body}</li>)}</ul>
      ) : (
        <p className="muted">메모가 없습니다.</p>
      )}
      <h3>측정 기록</h3>
      <p>{componentMeasurements.length}개</p>
    </aside>
  );
}
