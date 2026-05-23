import type { ElecProject } from "../domain/types";

const CURRENT_PROJECT_KEY = "elec-app/current-project";

export function saveProject(project: ElecProject): void {
  localStorage.setItem(CURRENT_PROJECT_KEY, JSON.stringify(project));
}

export function loadProject(): ElecProject | null {
  const raw = localStorage.getItem(CURRENT_PROJECT_KEY);
  if (!raw) return null;
  return importProjectJson(raw);
}

export function exportProjectJson(project: ElecProject): string {
  return JSON.stringify(project, null, 2);
}

export function importProjectJson(text: string): ElecProject {
  const parsed = JSON.parse(text) as ElecProject;
  if (!parsed.id || !parsed.name || !Array.isArray(parsed.components)) {
    throw new Error("지원하지 않는 Elec App 프로젝트 파일입니다.");
  }
  return parsed;
}
