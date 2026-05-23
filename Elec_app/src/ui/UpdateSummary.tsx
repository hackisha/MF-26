import type { UpdateMatchResult } from "../domain/updateMatcher";

interface UpdateSummaryProps {
  result: UpdateMatchResult | null;
}

export function UpdateSummary({ result }: UpdateSummaryProps) {
  if (!result) return null;

  return (
    <section className="panel">
      <h2>회로도 업데이트 요약</h2>
      <dl className="summary-grid">
        <div>
          <dt>자동 유지</dt>
          <dd>{result.matched.length}</dd>
        </div>
        <div>
          <dt>확인 필요</dt>
          <dd>{result.needsReview.length}</dd>
        </div>
        <div>
          <dt>추가</dt>
          <dd>{result.added.length}</dd>
        </div>
        <div>
          <dt>삭제</dt>
          <dd>{result.removed.length}</dd>
        </div>
      </dl>
    </section>
  );
}
