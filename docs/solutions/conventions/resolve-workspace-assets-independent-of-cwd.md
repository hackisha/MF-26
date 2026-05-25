---
title: "Resolve workspace assets independent of cwd"
date: "2026-05-25"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "assets"
  - "fixtures"
  - "cwd"
  - "ui"
---

# Resolve Workspace Assets Independent Of Cwd

## Context

The prototype uses root-level fixtures such as `car.glb` while normal developer commands often run from `prototype/`. During P8 review, `3D Vehicle Model` looked up `Path.cwd() / "car.glb"`, which worked from the repository root but failed from the documented `cd prototype` workflow.

## Guidance

Asset helpers should not depend on the process current working directory alone. Resolve important workspace fixtures from a small set of stable candidates: current cwd, cwd parent, and a source-file-derived repository root.

```python
def _root_asset_path(name: str) -> Path:
    source_repo_root = Path(__file__).resolve().parents[4]
    candidates = (
        Path.cwd() / name,
        Path.cwd().parent / name,
        source_repo_root / name,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return source_repo_root / name
```

Add regression tests that change cwd to the directory used in README commands:

```python
def test_root_asset_path_finds_car_glb_from_prototype_cwd(monkeypatch):
    monkeypatch.chdir("prototype")

    path = _root_asset_path("car.glb")

    assert path.exists()
```

## Why This Matters

UI smoke tests often run from the repository root, while app commands, editable installs, and developer shells may run from a package subdirectory. Cwd-dependent fixture lookup creates a false sense of safety: tests pass, but the documented manual workflow fails.

## When to Apply

Apply this whenever the app references project-root fixtures, sample CSVs, bundled model files, storyboard assets, report templates, or benchmark inputs. Prefer explicit project/session paths once persistence exists; use source-derived fallback only for prototype and development fixtures.
