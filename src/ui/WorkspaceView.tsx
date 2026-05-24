import { lazy, Suspense, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  createWorkspacePanel,
  defaultWorkspacePresets,
  loadWorkspacePresets,
  normalizeWorkspacePreset,
  saveWorkspacePresets,
  workspaceGridColumns,
  workspaceGridRows,
  workspacePanelLabels,
  workspacePanelViews,
  workspacePresetIdFromName,
  type WorkspacePanel,
  type WorkspacePanelView,
  type WorkspacePreset
} from "../domain/workspacePresets";
import { DiagnosticsView } from "./DiagnosticsView";
import { SummaryView } from "./SummaryView";

const TimeSeriesView = lazy(() => import("./TimeSeriesView").then((module) => ({ default: module.TimeSeriesView })));
const PlaybackView = lazy(() => import("./PlaybackView").then((module) => ({ default: module.PlaybackView })));
const BehaviorView = lazy(() => import("./BehaviorView").then((module) => ({ default: module.BehaviorView })));
const MapLapView = lazy(() => import("./MapLapView").then((module) => ({ default: module.MapLapView })));

export type WorkspacePanelRenderer = (view: WorkspacePanelView, panel: WorkspacePanel) => ReactNode;

type WorkspaceViewProps = {
  renderPanel?: WorkspacePanelRenderer;
};

function defaultRenderPanel(view: WorkspacePanelView): ReactNode {
  switch (view) {
    case "summary":
      return <SummaryView />;
    case "diagnostics":
      return <DiagnosticsView />;
    case "playback":
      return (
        <Suspense fallback={<section className="empty-state">Loading CSV playback...</section>}>
          <PlaybackView />
        </Suspense>
      );
    case "time-series":
      return (
        <Suspense fallback={<section className="empty-state">Loading graph...</section>}>
          <TimeSeriesView />
        </Suspense>
      );
    case "behavior":
      return (
        <Suspense fallback={<section className="empty-state">Loading behavior view...</section>}>
          <BehaviorView />
        </Suspense>
      );
    case "map-lap":
      return (
        <Suspense fallback={<section className="empty-state">Loading map / lap view...</section>}>
          <MapLapView />
        </Suspense>
      );
  }
}

function defaultPresetForId(presetId: string): WorkspacePreset | null {
  return defaultWorkspacePresets.find((preset) => preset.id === presetId) ?? null;
}

function normalizePresets(presets: WorkspacePreset[]): WorkspacePreset[] {
  return presets.map((preset) => normalizeWorkspacePreset(preset));
}

function panelPlacement(panel: WorkspacePanel, panelCount: number): WorkspacePanel {
  if (panel.x !== 0 || panel.y !== 0 || panelCount === 0) return panel;

  return normalizeWorkspacePreset({
    id: "placement",
    name: "Placement",
    panels: [
      {
        ...panel,
        x: (panelCount * 2) % 7,
        y: Math.min(4, Math.floor(panelCount / 2) * 2)
      }
    ]
  }).panels[0];
}

export function WorkspaceView({ renderPanel = defaultRenderPanel }: WorkspaceViewProps = {}) {
  const [presets, setPresets] = useState<WorkspacePreset[]>(() => normalizePresets(loadWorkspacePresets()));
  const [activePresetId, setActivePresetId] = useState(() => presets[0]?.id ?? defaultWorkspacePresets[0].id);
  const [panelType, setPanelType] = useState<WorkspacePanelView>("time-series");
  const [draftPresetName, setDraftPresetName] = useState(() => presets[0]?.name ?? defaultWorkspacePresets[0].name);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const activePreset = useMemo(
    () => presets.find((preset) => preset.id === activePresetId) ?? presets[0] ?? defaultWorkspacePresets[0],
    [activePresetId, presets]
  );

  useEffect(() => {
    setDraftPresetName(activePreset.name);
  }, [activePreset.id, activePreset.name]);

  function replaceActivePreset(nextPreset: WorkspacePreset, shouldPersist = false) {
    const normalizedPreset = normalizeWorkspacePreset(nextPreset);
    const nextPresets = presets.some((preset) => preset.id === normalizedPreset.id)
      ? presets.map((preset) => (preset.id === normalizedPreset.id ? normalizedPreset : preset))
      : [...presets, normalizedPreset];

    setPresets(nextPresets);
    setActivePresetId(normalizedPreset.id);
    if (shouldPersist) saveWorkspacePresets(nextPresets);
  }

  function updateActivePanels(updater: (panels: WorkspacePanel[]) => WorkspacePanel[]) {
    replaceActivePreset({
      ...activePreset,
      panels: updater(activePreset.panels)
    });
    setStatusMessage(null);
  }

  function addPanel() {
    updateActivePanels((panels) => {
      const panel = panelPlacement(createWorkspacePanel(panelType, panels), panels.length);
      return [...panels, panel];
    });
  }

  function removePanel(panelId: string) {
    updateActivePanels((panels) => panels.filter((panel) => panel.id !== panelId));
  }

  function updatePanel(panelId: string, update: (panel: WorkspacePanel) => WorkspacePanel) {
    updateActivePanels((panels) => panels.map((panel) => (panel.id === panelId ? update(panel) : panel)));
  }

  function movePanel(panel: WorkspacePanel, dx: number, dy: number) {
    updatePanel(panel.id, (currentPanel) => ({ ...currentPanel, x: currentPanel.x + dx, y: currentPanel.y + dy }));
  }

  function resizePanel(panel: WorkspacePanel, widthDelta: number, heightDelta: number) {
    updatePanel(panel.id, (currentPanel) => ({
      ...currentPanel,
      width: currentPanel.width + widthDelta,
      height: currentPanel.height + heightDelta
    }));
  }

  function handleSave() {
    const nextPreset = normalizeWorkspacePreset({
      ...activePreset,
      name: draftPresetName.trim() || activePreset.name
    });
    const nextPresets = presets.map((preset) => (preset.id === nextPreset.id ? nextPreset : preset));

    setPresets(nextPresets);
    saveWorkspacePresets(nextPresets);
    setStatusMessage("Layout saved.");
  }

  function handleSaveAs() {
    const name = draftPresetName.trim() || `${activePreset.name} Copy`;
    const nextPreset = normalizeWorkspacePreset({
      ...activePreset,
      id: workspacePresetIdFromName(name, presets),
      name,
      panels: activePreset.panels.map((panel) => ({ ...panel }))
    });
    const nextPresets = [...presets, nextPreset];

    setPresets(nextPresets);
    setActivePresetId(nextPreset.id);
    saveWorkspacePresets(nextPresets);
    setStatusMessage("Preset saved.");
  }

  function handleReset() {
    const defaultPreset = defaultPresetForId(activePreset.id) ?? defaultWorkspacePresets[0];
    const nextPresets = presets.map((preset) =>
      preset.id === activePreset.id
        ? {
            ...defaultPreset,
            panels: defaultPreset.panels.map((panel) => ({ ...panel }))
          }
        : preset
    );

    setPresets(nextPresets);
    saveWorkspacePresets(nextPresets);
    setStatusMessage("Preset reset.");
  }

  return (
    <section className="workspace-view" aria-label="Workspace presets">
      <div className="workspace-heading">
        <div>
          <h2>Workspace</h2>
          <p>Arrange multiple analysis panels together, then save the layout as a preset.</p>
        </div>
      </div>

      <div className="workspace-toolbar" aria-label="Workspace controls">
        <label className="workspace-field">
          <span>Preset</span>
          <select
            aria-label="Workspace preset"
            value={activePreset.id}
            onChange={(event) => {
              setActivePresetId(event.currentTarget.value);
              setStatusMessage(null);
            }}
          >
            {presets.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.name}
              </option>
            ))}
          </select>
        </label>

        <button type="button" onClick={handleSave}>
          Save layout
        </button>
        <label className="workspace-field workspace-name-field">
          <span>Preset name</span>
          <input
            aria-label="Preset name"
            value={draftPresetName}
            onChange={(event) => {
              setDraftPresetName(event.currentTarget.value);
              setStatusMessage(null);
            }}
          />
        </label>
        <button type="button" onClick={handleSaveAs}>
          Save as preset
        </button>
        <button type="button" onClick={handleReset}>
          Reset preset
        </button>

        <label className="workspace-field">
          <span>Panel</span>
          <select
            aria-label="Panel type"
            value={panelType}
            onChange={(event) => setPanelType(event.currentTarget.value as WorkspacePanelView)}
          >
            {workspacePanelViews.map((view) => (
              <option key={view} value={view}>
                {workspacePanelLabels[view]}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={addPanel}>
          Add panel
        </button>
        {statusMessage ? (
          <span className="workspace-status" role="status">
            {statusMessage}
          </span>
        ) : null}
      </div>

      <div
        className="workspace-desktop"
        style={{
          gridTemplateColumns: `repeat(${workspaceGridColumns}, minmax(0, 1fr))`,
          gridTemplateRows: `repeat(${workspaceGridRows}, 96px)`
        }}
      >
        {activePreset.panels.length === 0 ? (
          <section className="inline-empty workspace-empty">
            <h3>No panels in this preset</h3>
            <p>Add a panel to start building an analysis workspace.</p>
          </section>
        ) : (
          activePreset.panels.map((panel) => (
            <article
              key={panel.id}
              className="workspace-panel"
              aria-label={`Workspace panel: ${panel.title}`}
              data-grid-x={panel.x}
              data-grid-y={panel.y}
              data-grid-width={panel.width}
              data-grid-height={panel.height}
              style={{
                gridColumn: `${panel.x + 1} / span ${panel.width}`,
                gridRow: `${panel.y + 1} / span ${panel.height}`
              }}
            >
              <div className="workspace-panel-titlebar" aria-label={`${panel.title} panel controls`}>
                <div className="workspace-panel-title">
                  <strong>{panel.title}</strong>
                  <span>{workspacePanelLabels[panel.view]}</span>
                </div>
                <div className="workspace-panel-controls">
                  <button type="button" title="Move left" aria-label={`Move ${panel.title} left`} onClick={() => movePanel(panel, -1, 0)}>
                    L
                  </button>
                  <button type="button" title="Move right" aria-label={`Move ${panel.title} right`} onClick={() => movePanel(panel, 1, 0)}>
                    R
                  </button>
                  <button type="button" title="Move up" aria-label={`Move ${panel.title} up`} onClick={() => movePanel(panel, 0, -1)}>
                    U
                  </button>
                  <button type="button" title="Move down" aria-label={`Move ${panel.title} down`} onClick={() => movePanel(panel, 0, 1)}>
                    D
                  </button>
                  <button
                    type="button"
                    title="Shrink width"
                    aria-label={`Shrink ${panel.title} width`}
                    onClick={() => resizePanel(panel, -1, 0)}
                  >
                    W-
                  </button>
                  <button
                    type="button"
                    title="Grow width"
                    aria-label={`Grow ${panel.title} width`}
                    onClick={() => resizePanel(panel, 1, 0)}
                  >
                    W+
                  </button>
                  <button
                    type="button"
                    title="Shrink height"
                    aria-label={`Shrink ${panel.title} height`}
                    onClick={() => resizePanel(panel, 0, -1)}
                  >
                    H-
                  </button>
                  <button
                    type="button"
                    title="Grow height"
                    aria-label={`Grow ${panel.title} height`}
                    onClick={() => resizePanel(panel, 0, 1)}
                  >
                    H+
                  </button>
                  <button type="button" title="Close" aria-label={`Close ${panel.title} panel`} onClick={() => removePanel(panel.id)}>
                    X
                  </button>
                </div>
              </div>
              <div className="workspace-panel-body">{renderPanel(panel.view, panel)}</div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
