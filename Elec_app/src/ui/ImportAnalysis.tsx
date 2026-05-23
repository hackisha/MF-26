import type { ParsedSchematic } from "../domain/types";

interface ImportAnalysisProps {
  parsed: ParsedSchematic | null;
  error: string | null;
}

export function ImportAnalysis({ parsed, error }: ImportAnalysisProps) {
  if (error) {
    return (
      <section className="panel error">
        <h2>분석 실패</h2>
        <p>{error}</p>
      </section>
    );
  }
  if (!parsed) return null;

  return (
    <section className="panel">
      <h2>업로드 분석</h2>
      <dl className="summary-grid">
        <div>
          <dt>파일</dt>
          <dd>{parsed.source.fileName}</dd>
        </div>
        <div>
          <dt>부품</dt>
          <dd>{parsed.components.length}</dd>
        </div>
        <div>
          <dt>와이어</dt>
          <dd>{parsed.wires.length}</dd>
        </div>
        <div>
          <dt>접점</dt>
          <dd>{parsed.junctions.length}</dd>
        </div>
        <div>
          <dt>Net label</dt>
          <dd>{parsed.labels.length}</dd>
        </div>
        <div>
          <dt>경고</dt>
          <dd>{parsed.warnings.length}</dd>
        </div>
      </dl>
    </section>
  );
}
