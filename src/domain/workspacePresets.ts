export type WorkspacePanelView = "summary" | "diagnostics" | "playback" | "time-series" | "behavior" | "map-lap";

export type WorkspacePanel = {
  id: string;
  view: WorkspacePanelView;
  title: string;
  x: number;
  y: number;
  width: number;
  height: number;
};

export type WorkspacePreset = {
  id: string;
  name: string;
  panels: WorkspacePanel[];
};

export const workspaceStorageKey = "mf-log-analyzer-workspace-presets-v1";
export const workspaceGridColumns = 12;
export const workspaceGridRows = 8;
export const minWorkspacePanelWidth = 4;
export const minWorkspacePanelHeight = 2;
export const defaultWorkspacePanelWidth = 6;
export const defaultWorkspacePanelHeight = 4;

export const workspacePanelLabels: Record<WorkspacePanelView, string> = {
  summary: "Summary",
  diagnostics: "Log Diagnostics",
  playback: "CSV Playback",
  "time-series": "Time-Series Graph",
  behavior: "Vehicle Behavior",
  "map-lap": "Map / Lap"
};

export const workspacePanelViews: WorkspacePanelView[] = [
  "summary",
  "diagnostics",
  "playback",
  "time-series",
  "behavior",
  "map-lap"
];

export const defaultWorkspacePresets: WorkspacePreset[] = [
  {
    id: "cooling-review",
    name: "Cooling Review",
    panels: [
      { id: "cooling-graph", view: "time-series", title: workspacePanelLabels["time-series"], x: 0, y: 0, width: 12, height: 5 },
      { id: "cooling-map", view: "map-lap", title: workspacePanelLabels["map-lap"], x: 0, y: 5, width: 12, height: 3 }
    ]
  },
  {
    id: "vehicle-behavior",
    name: "Vehicle Behavior",
    panels: [
      { id: "behavior-model", view: "behavior", title: workspacePanelLabels.behavior, x: 0, y: 0, width: 12, height: 5 },
      { id: "behavior-map", view: "map-lap", title: workspacePanelLabels["map-lap"], x: 0, y: 5, width: 12, height: 3 }
    ]
  },
  {
    id: "engine-safety",
    name: "Engine Safety",
    panels: [
      { id: "safety-diagnostics", view: "diagnostics", title: workspacePanelLabels.diagnostics, x: 0, y: 0, width: 4, height: 8 },
      { id: "safety-graph", view: "time-series", title: workspacePanelLabels["time-series"], x: 4, y: 0, width: 8, height: 8 }
    ]
  }
];

type StorageLike = Pick<Storage, "getItem" | "setItem">;

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function storageOrNull(): StorageLike | null {
  return typeof window === "undefined" ? null : window.localStorage;
}

function isWorkspacePanelView(value: unknown): value is WorkspacePanelView {
  return typeof value === "string" && workspacePanelViews.includes(value as WorkspacePanelView);
}

function copyDefaults(): WorkspacePreset[] {
  return defaultWorkspacePresets.map((preset) => ({
    ...preset,
    panels: preset.panels.map((panel) => ({ ...panel }))
  }));
}

function validString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function finiteInteger(value: unknown, fallback: number): number {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? Math.floor(numberValue) : fallback;
}

function normalizePanel(panel: Partial<WorkspacePanel>): WorkspacePanel | null {
  if (!isWorkspacePanelView(panel.view)) return null;

  const width = clamp(
    finiteInteger(panel.width, defaultWorkspacePanelWidth),
    minWorkspacePanelWidth,
    workspaceGridColumns
  );
  const height = clamp(
    finiteInteger(panel.height, defaultWorkspacePanelHeight),
    minWorkspacePanelHeight,
    workspaceGridRows
  );
  const maxX = workspaceGridColumns - width;
  const maxY = workspaceGridRows - height;

  return {
    id: validString(panel.id, panel.view),
    view: panel.view,
    title: validString(panel.title, workspacePanelLabels[panel.view]),
    x: clamp(finiteInteger(panel.x, 0), 0, maxX),
    y: clamp(finiteInteger(panel.y, 0), 0, maxY),
    width,
    height
  };
}

export function normalizeWorkspacePreset(preset: Partial<WorkspacePreset>): WorkspacePreset {
  const panels = Array.isArray(preset.panels)
    ? preset.panels.map((panel) => normalizePanel(panel)).filter((panel): panel is WorkspacePanel => panel !== null)
    : [];

  return {
    id: validString(preset.id, "workspace"),
    name: validString(preset.name, "Workspace"),
    panels
  };
}

export function loadWorkspacePresets(storage: StorageLike | null = storageOrNull()): WorkspacePreset[] {
  if (!storage) return copyDefaults();

  try {
    const rawValue = storage.getItem(workspaceStorageKey);
    if (!rawValue) return copyDefaults();

    const parsedValue = JSON.parse(rawValue) as unknown;
    if (!Array.isArray(parsedValue)) return copyDefaults();

    const presets = parsedValue.map((preset) => normalizeWorkspacePreset(preset as Partial<WorkspacePreset>));
    return presets.length > 0 ? presets : copyDefaults();
  } catch {
    return copyDefaults();
  }
}

export function saveWorkspacePresets(presets: WorkspacePreset[], storage: StorageLike | null = storageOrNull()): void {
  if (!storage) return;
  storage.setItem(workspaceStorageKey, JSON.stringify(presets.map(normalizeWorkspacePreset)));
}

export function workspacePresetIdFromName(name: string, existingPresets: WorkspacePreset[]): string {
  const baseId = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "workspace";
  let id = baseId;
  let suffix = 2;

  while (existingPresets.some((preset) => preset.id === id)) {
    id = `${baseId}-${suffix}`;
    suffix += 1;
  }

  return id;
}

export function createWorkspacePanel(view: WorkspacePanelView, existingPanels: WorkspacePanel[]): WorkspacePanel {
  let ordinal = existingPanels.filter((panel) => panel.view === view).length + 1;
  let id = `${view}-${ordinal}`;

  while (existingPanels.some((panel) => panel.id === id)) {
    ordinal += 1;
    id = `${view}-${ordinal}`;
  }

  return {
    id,
    view,
    title: workspacePanelLabels[view],
    x: 0,
    y: 0,
    width: defaultWorkspacePanelWidth,
    height: defaultWorkspacePanelHeight
  };
}
