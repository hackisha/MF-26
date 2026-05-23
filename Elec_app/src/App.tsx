import { useEffect, useState } from "react";
import { BookOpen, Cable, FileImage, Gauge, Settings, UploadCloud } from "lucide-react";
import { buildConnectivityGraph } from "./domain/connectivity";
import { parseEasyEdaSchematic } from "./domain/easyedaParser";
import { matchUpdatedComponents, type UpdateMatchResult } from "./domain/updateMatcher";
import type { ComponentRole, ElecProject, Measurement, ParsedSchematic } from "./domain/types";
import { exportProjectJson, importProjectJson, loadProject, saveProject } from "./storage/projectStore";
import { ClassificationQueue } from "./ui/ClassificationQueue";
import { ComponentInfoPanel } from "./ui/ComponentInfoPanel";
import { ConnectorPinout } from "./ui/ConnectorPinout";
import { ImportAnalysis } from "./ui/ImportAnalysis";
import { NotesMeasurements } from "./ui/NotesMeasurements";
import { ProjectHome } from "./ui/ProjectHome";
import { ReferenceTabs } from "./ui/ReferenceTabs";
import { SearchDebugger } from "./ui/SearchDebugger";
import { LogReplayTab } from "./ui/logReplay/LogReplayTab";
import { UpdateSummary } from "./ui/UpdateSummary";
import { hashText } from "./utils/fileHash";

type Workspace = "logReplay" | "wiring" | "references" | "settings";

const workspaceItems: Array<{
  id: Workspace;
  label: string;
  description: string;
  icon: typeof Gauge;
}> = [
  { id: "logReplay", label: "로그 분석", description: "CSV 분석/재생", icon: Gauge },
  { id: "wiring", label: "배선 디버거", description: "핀/커넥터 추적", icon: Cable },
  { id: "references", label: "자료 보관함", description: "배선도/규정/데이터시트", icon: BookOpen },
  { id: "settings", label: "프로젝트", description: "업로드/내보내기", icon: Settings },
];

function createProject(parsed: ParsedSchematic): ElecProject {
  const now = new Date().toISOString();
  return {
    id: parsed.source.hash,
    name: parsed.source.title || parsed.source.fileName,
    createdAt: now,
    updatedAt: now,
    source: parsed.source,
    components: parsed.components,
    graph: buildConnectivityGraph(parsed),
    classifications: {},
    notes: [],
    measurements: [],
    attachments: [],
  };
}

export default function App() {
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace>("logReplay");
  const [parsed, setParsed] = useState<ParsedSchematic | null>(null);
  const [project, setProject] = useState<ElecProject | null>(() => loadProject());
  const [error, setError] = useState<string | null>(null);
  const [updateResult, setUpdateResult] = useState<UpdateMatchResult | null>(null);

  useEffect(() => {
    if (project) saveProject(project);
  }, [project]);

  async function handleJsonFile(file: File) {
    setError(null);
    try {
      const text = await file.text();
      const hash = await hashText(text);
      const nextParsed = await parseEasyEdaSchematic({
        fileName: file.name,
        text,
        uploadedAt: new Date().toISOString(),
        hash,
      });
      const nextProject = createProject(nextParsed);

      if (project?.components.length) {
        const matched = matchUpdatedComponents(project.components, nextProject.components);
        setUpdateResult(matched);
        const preserved = new Map(
          matched.matched.map((item) => [item.nextId, project.components.find((component) => component.id === item.previousId)]),
        );
        nextProject.components = nextProject.components.map((component) => {
          const previous = preserved.get(component.id);
          return previous
            ? {
                ...component,
                alias: previous.alias,
                confirmedRole: previous.confirmedRole,
              }
            : component;
        });
      }

      setParsed(nextParsed);
      setProject(nextProject);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function handleProjectFile(file: File) {
    setError(null);
    try {
      const text = await file.text();
      setProject(importProjectJson(text));
      setParsed(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "프로젝트 파일을 읽을 수 없습니다.");
    }
  }

  function handleExport() {
    if (!project) return;
    const blob = new Blob([exportProjectJson(project)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "muzil-tools-project.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  function confirmClassification(componentId: string, role: ComponentRole, alias: string) {
    setProject((current) => {
      if (!current) return current;
      const updatedAt = new Date().toISOString();
      return {
        ...current,
        updatedAt,
        components: current.components.map((component) =>
          component.id === componentId ? { ...component, confirmedRole: role, alias } : component,
        ),
        classifications: {
          ...current.classifications,
          [componentId]: { componentId, role, alias, confirmedAt: updatedAt },
        },
      };
    });
  }

  function addNote(targetId: string, body: string) {
    if (!body.trim()) return;
    setProject((current) =>
      current
        ? {
            ...current,
            notes: [
              ...current.notes,
              { id: crypto.randomUUID(), targetType: "pin", targetId, body, updatedAt: new Date().toISOString() },
            ],
          }
        : current,
    );
  }

  function addMeasurement(input: Omit<Measurement, "id" | "measuredAt">) {
    setProject((current) =>
      current
        ? {
            ...current,
            measurements: [
              ...current.measurements,
              { ...input, id: crypto.randomUUID(), measuredAt: new Date().toISOString() },
            ],
          }
        : current,
    );
  }

  function addReferenceLink(targetType: "component" | "wiring-diagram" | "regulation", label: string, url: string) {
    if (!label.trim() || !url.trim()) return;
    setProject((current) =>
      current
        ? {
            ...current,
            attachments: [
              ...current.attachments,
              { id: crypto.randomUUID(), targetType, targetId: null, label, kind: "link", url, blobKey: null, mimeType: null },
            ],
          }
        : current,
    );
  }

  function addReferenceFile(targetType: "component" | "wiring-diagram" | "regulation", file: File) {
    setProject((current) =>
      current
        ? {
            ...current,
            attachments: [
              ...current.attachments,
              {
                id: crypto.randomUUID(),
                targetType,
                targetId: null,
                label: file.name,
                kind: "file",
                url: null,
                blobKey: `${Date.now()}-${file.name}`,
                mimeType: file.type,
              },
            ],
          }
        : current,
    );
  }

  const firstPinId = project?.components.find((component) => component.pins.length > 0)?.pins[0].id ?? "project";
  const activeItem = workspaceItems.find((item) => item.id === activeWorkspace) ?? workspaceItems[0];
  const ActiveIcon = activeItem.icon;

  return (
    <main className="app-shell">
      <aside className="app-sidebar">
        <div className="app-brand">
          <span>MF-26</span>
          <strong>Muzil Tools</strong>
        </div>
        <nav className="workspace-rail" aria-label="작업 공간">
          {workspaceItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                className={activeWorkspace === item.id ? "active" : ""}
                onClick={() => setActiveWorkspace(item.id)}
              >
                <Icon size={18} aria-hidden="true" />
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
              </button>
            );
          })}
        </nav>
        <div className="sidebar-status">
          <span>회로도</span>
          <strong>{project?.source?.fileName ?? "미업로드"}</strong>
        </div>
      </aside>

      <section className="app-main">
        <header className="workspace-header">
          <div>
            <span>
              <ActiveIcon size={17} aria-hidden="true" />
              {activeItem.label}
            </span>
            <h1>{activeWorkspace === "logReplay" ? "주행 데이터 분석" : activeItem.label}</h1>
            <p>
              {activeWorkspace === "logReplay"
                ? "CSV 로그를 GPS, G-G, 센서 시계열, 이벤트 기준으로 나누어 한 화면에서 확인합니다."
                : activeWorkspace === "wiring"
                  ? "EasyEDA 회로도에서 ECU, 커넥터, 센서 핀의 연결 경로를 추적합니다."
                  : activeWorkspace === "references"
                    ? "배선도 이미지, 대회 규정, 데이터시트 링크를 프로젝트와 함께 보관합니다."
                    : "회로도 JSON과 프로젝트 파일을 업로드하거나 내보냅니다."}
            </p>
          </div>
          <div className="workspace-header__meta">
            <span>{project ? `${project.components.length} components` : "No schematic"}</span>
            <span>{project ? `${project.attachments.length} refs` : "0 refs"}</span>
          </div>
        </header>

        {activeWorkspace === "logReplay" ? <LogReplayTab /> : null}

        {activeWorkspace === "wiring" ? (
          <>
            <ProjectHome
              currentFileName={parsed?.source.fileName ?? project?.source?.fileName ?? null}
              onJsonFile={(file) => void handleJsonFile(file)}
              onProjectFile={(file) => void handleProjectFile(file)}
              onExport={handleExport}
            />
            <ImportAnalysis parsed={parsed} error={error} />
            <UpdateSummary result={updateResult} />
            {project ? (
              <>
                <SearchDebugger components={project.components} graph={project.graph} />
                <ConnectorPinout components={project.components} notes={project.notes} measurements={project.measurements} />
                <ComponentInfoPanel
                  component={project.components[0] ?? null}
                  notes={project.notes}
                  measurements={project.measurements}
                  attachments={project.attachments}
                />
                <NotesMeasurements targetId={firstPinId} onAddNote={addNote} onAddMeasurement={addMeasurement} />
                <ClassificationQueue components={project.components} onConfirm={confirmClassification} />
              </>
            ) : (
              <section className="empty-state workbench-empty">
                <UploadCloud size={24} aria-hidden="true" />
                <h2>회로도 프로젝트가 없습니다</h2>
                <p>EasyEDA JSON 또는 Muzil Tools 프로젝트 파일을 업로드하면 배선 검색과 커넥터 추적을 시작할 수 있습니다.</p>
              </section>
            )}
          </>
        ) : null}

        {activeWorkspace === "references" ? (
          project ? (
            <ReferenceTabs attachments={project.attachments} onAddLink={addReferenceLink} onAddFile={addReferenceFile} />
          ) : (
            <section className="empty-state workbench-empty">
              <FileImage size={24} aria-hidden="true" />
              <h2>자료를 연결할 프로젝트가 없습니다</h2>
              <p>먼저 프로젝트 탭에서 회로도 또는 프로젝트 파일을 불러오면 배선도, 규정, 데이터시트를 저장할 수 있습니다.</p>
            </section>
          )
        ) : null}

        {activeWorkspace === "settings" ? (
          <>
            <ProjectHome
              currentFileName={parsed?.source.fileName ?? project?.source?.fileName ?? null}
              onJsonFile={(file) => void handleJsonFile(file)}
              onProjectFile={(file) => void handleProjectFile(file)}
              onExport={handleExport}
            />
            <ImportAnalysis parsed={parsed} error={error} />
            <UpdateSummary result={updateResult} />
          </>
        ) : null}
      </section>
    </main>
  );
}
