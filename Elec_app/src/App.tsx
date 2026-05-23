import { useEffect, useState } from "react";
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
  const [activeWorkspace, setActiveWorkspace] = useState<"logReplay" | "wiring">("logReplay");
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
    link.download = "elec-app-project.json";
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

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>Elec App</h1>
          <p>MF-26 engine/elec wiring debugger</p>
        </div>
      </header>
      <nav className="workspace-tabs" aria-label="작업 탭">
        <button
          type="button"
          className={activeWorkspace === "logReplay" ? "active" : ""}
          onClick={() => setActiveWorkspace("logReplay")}
        >
          로그 재생
        </button>
        <button
          type="button"
          className={activeWorkspace === "wiring" ? "active" : ""}
          onClick={() => setActiveWorkspace("wiring")}
        >
          배선 디버거
        </button>
      </nav>
      {activeWorkspace === "logReplay" ? (
        <LogReplayTab />
      ) : (
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
              <ClassificationQueue components={project.components} onConfirm={confirmClassification} />
              <SearchDebugger components={project.components} graph={project.graph} />
              <ConnectorPinout components={project.components} notes={project.notes} measurements={project.measurements} />
              <ComponentInfoPanel
                component={project.components[0] ?? null}
                notes={project.notes}
                measurements={project.measurements}
                attachments={project.attachments}
              />
              <NotesMeasurements targetId={firstPinId} onAddNote={addNote} onAddMeasurement={addMeasurement} />
              <ReferenceTabs attachments={project.attachments} onAddLink={addReferenceLink} onAddFile={addReferenceFile} />
            </>
          ) : (
            <section className="empty-state">
              <h2>프로젝트 없음</h2>
              <p>EasyEDA JSON 또는 Elec App 프로젝트 파일을 가져오세요.</p>
            </section>
          )}
        </>
      )}
    </main>
  );
}
