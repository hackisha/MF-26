import type { Severity } from "../domain/types";

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`severity severity-${severity}`}>{severity}</span>;
}
