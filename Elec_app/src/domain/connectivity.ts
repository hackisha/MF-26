import type { Component, GraphEdge, GraphNode, NetGraph, ParsedSchematic } from "./types";

const SNAP = 0.5;

function pointKey(x: number, y: number): string {
  return `${Math.round(x / SNAP) * SNAP}:${Math.round(y / SNAP) * SNAP}`;
}

function edgeId(from: string, to: string, kind: GraphEdge["kind"]): string {
  return [kind, from, to].sort().join(":");
}

function setPointNode(nodes: Map<string, GraphNode>, node: GraphNode): string {
  const key = pointKey(node.x, node.y);
  if (!nodes.has(key)) nodes.set(key, node);
  return nodes.get(key)!.id;
}

export function buildConnectivityGraph(parsed: ParsedSchematic): NetGraph {
  const nodesByPoint = new Map<string, GraphNode>();
  const pinNodes = new Map<string, GraphNode>();
  const edgesById = new Map<string, GraphEdge>();

  for (const wire of parsed.wires) {
    for (let i = 0; i < wire.points.length; i += 1) {
      const point = wire.points[i];
      setPointNode(nodesByPoint, {
        id: `wire:${point.x}:${point.y}`,
        kind: "wire-point",
        x: point.x,
        y: point.y,
        label: null,
        refId: wire.id
      });

      if (i > 0) {
        const previous = wire.points[i - 1];
        const from = setPointNode(nodesByPoint, {
          id: `wire:${previous.x}:${previous.y}`,
          kind: "wire-point",
          x: previous.x,
          y: previous.y,
          label: null,
          refId: wire.id
        });
        const to = setPointNode(nodesByPoint, {
          id: `wire:${point.x}:${point.y}`,
          kind: "wire-point",
          x: point.x,
          y: point.y,
          label: null,
          refId: wire.id
        });
        const id = edgeId(from, to, "wire");
        edgesById.set(id, { id, from, to, kind: "wire", confidence: 1 });
      }
    }
  }

  for (const junction of parsed.junctions) {
    setPointNode(nodesByPoint, {
      id: `junction:${junction.id}`,
      kind: "junction",
      x: junction.x,
      y: junction.y,
      label: null,
      refId: junction.id
    });
  }

  for (const label of parsed.labels) {
    const pointNode = setPointNode(nodesByPoint, {
      id: `wire:${label.x}:${label.y}`,
      kind: "wire-point",
      x: label.x,
      y: label.y,
      label: null,
      refId: null
    });
    const labelNodeId = `label:${label.id}`;
    pinNodes.set(labelNodeId, {
      id: labelNodeId,
      kind: "label",
      x: label.x,
      y: label.y,
      label: label.label,
      refId: label.id
    });
    const id = edgeId(labelNodeId, pointNode, "label-contact");
    edgesById.set(id, { id, from: labelNodeId, to: pointNode, kind: "label-contact", confidence: 0.85 });
  }

  for (const component of parsed.components) {
    for (const pin of component.pins) {
      const pointNode = setPointNode(nodesByPoint, {
        id: `wire:${pin.x}:${pin.y}`,
        kind: "wire-point",
        x: pin.x,
        y: pin.y,
        label: null,
        refId: null
      });
      const pinNodeId = `pin:${pin.id}`;
      pinNodes.set(pinNodeId, {
        id: pinNodeId,
        kind: "pin",
        x: pin.x,
        y: pin.y,
        label: pin.label,
        refId: pin.id
      });
      const id = edgeId(pinNodeId, pointNode, "pin-contact");
      edgesById.set(id, { id, from: pinNodeId, to: pointNode, kind: "pin-contact", confidence: 1 });
    }
  }

  return {
    nodes: [...nodesByPoint.values(), ...pinNodes.values()],
    edges: [...edgesById.values()]
  };
}

function adjacency(graph: NetGraph): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const edge of graph.edges) {
    map.set(edge.from, [...(map.get(edge.from) ?? []), edge.to]);
    map.set(edge.to, [...(map.get(edge.to) ?? []), edge.from]);
  }
  return map;
}

export function traceFromPin(graph: NetGraph, components: Component[], pinId: string): Component[] {
  const start = `pin:${pinId}`;
  const seen = new Set<string>([start]);
  const queue = [start];
  const links = adjacency(graph);
  const connectedPinIds = new Set<string>();

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (current.startsWith("pin:")) connectedPinIds.add(current.slice(4));
    for (const next of links.get(current) ?? []) {
      if (!seen.has(next)) {
        seen.add(next);
        queue.push(next);
      }
    }
  }

  return components.filter((component) =>
    component.pins.some((pin) => connectedPinIds.has(pin.id))
  );
}
