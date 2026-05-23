import { useState } from "react";
import type { Component, ComponentRole } from "../domain/types";

const roleLabels: Record<ComponentRole, string> = {
  ecu: "ECU",
  connector: "커넥터",
  sensor: "센서",
  actuator: "액추에이터",
  power: "전원 부품",
  other: "기타",
  unknown: "미확인"
};

interface ClassificationQueueProps {
  components: Component[];
  onConfirm: (componentId: string, role: ComponentRole, alias: string) => void;
}

export function ClassificationQueue({ components, onConfirm }: ClassificationQueueProps) {
  const pending = components.filter((component) => !component.confirmedRole && component.autoConfidence < 0.7);

  return (
    <section className="panel">
      <h2>분류 확인 큐</h2>
      {pending.length === 0 ? (
        <p>확인할 애매한 부품이 없습니다.</p>
      ) : (
        <div className="stack">
          {pending.map((component) => (
            <ClassificationRow key={component.id} component={component} onConfirm={onConfirm} />
          ))}
        </div>
      )}
    </section>
  );
}

function ClassificationRow({
  component,
  onConfirm
}: {
  component: Component;
  onConfirm: ClassificationQueueProps["onConfirm"];
}) {
  const [role, setRole] = useState<ComponentRole>(component.autoRole);
  const [alias, setAlias] = useState(component.alias || component.rawName);

  return (
    <article className="classification-row">
      <div>
        <h3>{component.rawName || component.symbolName || component.packageName}</h3>
        <p>
          {component.packageName} / pins {component.pins.length} / confidence{" "}
          {component.autoConfidence.toFixed(2)}
        </p>
      </div>
      <label>
        분류
        <select value={role} onChange={(event) => setRole(event.currentTarget.value as ComponentRole)}>
          {Object.entries(roleLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        별칭
        <input value={alias} onChange={(event) => setAlias(event.currentTarget.value)} />
      </label>
      <button type="button" onClick={() => onConfirm(component.id, role, alias)}>
        확정
      </button>
    </article>
  );
}
