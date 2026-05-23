import type { Component } from "../domain/types";

export function matchesComponent(component: Component, query: string): boolean {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return false;
  const haystack = [
    component.rawName,
    component.alias,
    component.packageName,
    component.symbolName,
    ...component.pins.map((pin) => `${component.alias} pin ${pin.number}`),
    ...component.pins.map((pin) => pin.label ?? "")
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(normalized);
}
