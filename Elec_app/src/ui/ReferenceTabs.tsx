import { useState } from "react";
import type { Attachment } from "../domain/types";

type ReferenceTarget = "component" | "wiring-diagram" | "regulation";

interface ReferenceTabsProps {
  attachments: Attachment[];
  onAddLink: (targetType: ReferenceTarget, label: string, url: string) => void;
  onAddFile: (targetType: ReferenceTarget, file: File) => void;
}

const tabs: Array<{ target: ReferenceTarget; label: string }> = [
  { target: "component", label: "데이터시트" },
  { target: "wiring-diagram", label: "전체 배선도" },
  { target: "regulation", label: "대회 규정" }
];

export function ReferenceTabs({ attachments, onAddLink, onAddFile }: ReferenceTabsProps) {
  const [active, setActive] = useState<ReferenceTarget>("component");
  const [label, setLabel] = useState("");
  const [url, setUrl] = useState("");
  const visible = attachments.filter((attachment) => attachment.targetType === active);

  return (
    <section className="panel">
      <h2>레퍼런스</h2>
      <div className="tab-row">
        {tabs.map((tab) => (
          <button key={tab.target} type="button" onClick={() => setActive(tab.target)}>
            {tab.label}
          </button>
        ))}
      </div>
      <div className="reference-form">
        <label className="field">
          링크 제목
          <input value={label} onChange={(event) => setLabel(event.currentTarget.value)} />
        </label>
        <label className="field">
          URL
          <input value={url} onChange={(event) => setUrl(event.currentTarget.value)} />
        </label>
        <button type="button" onClick={() => onAddLink(active, label, url)}>
          링크 저장
        </button>
        <label className="field">
          파일 첨부
          <input
            type="file"
            accept=".pdf,image/*"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onAddFile(active, file);
            }}
          />
        </label>
      </div>
      <ul>
        {visible.map((item) => (
          <li key={item.id}>{item.label}</li>
        ))}
      </ul>
    </section>
  );
}
