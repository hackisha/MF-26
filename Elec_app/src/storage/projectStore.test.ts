import { beforeEach, describe, expect, it } from "vitest";
import { exportProjectJson, importProjectJson, loadProject, saveProject } from "./projectStore";
import type { ElecProject } from "../domain/types";

const project: ElecProject = {
  id: "p1",
  name: "MF-26",
  createdAt: "2026-05-21T00:00:00.000Z",
  updatedAt: "2026-05-21T00:00:00.000Z",
  source: null,
  components: [],
  graph: { nodes: [], edges: [] },
  classifications: {},
  notes: [],
  measurements: [],
  attachments: []
};

describe("projectStore", () => {
  beforeEach(() => localStorage.clear());

  it("saves and loads a project", () => {
    saveProject(project);
    expect(loadProject()?.name).toBe("MF-26");
  });

  it("exports and imports project JSON", () => {
    const text = exportProjectJson(project);
    expect(importProjectJson(text).id).toBe("p1");
  });
});
