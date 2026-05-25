---
title: "Resolve workspace assets independent of cwd"
date: "2026-05-25"
last_updated: "2026-05-26"
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

Asset helpers should not depend on the process current working directory alone. Resolve important workspace fixtures from a small set of stable candidates: PyInstaller bundle root when frozen, executable directory when frozen, current cwd, cwd parent, and a source-file-derived repository root.

```python
def _root_asset_path(name: str) -> Path:
    for root in _asset_roots():
        candidate = root / name
        if candidate.exists():
            return candidate
    return _asset_roots()[-1] / name
```

Add regression tests that change cwd to the directory used in README commands:

```python
def test_root_asset_path_finds_car_glb_from_prototype_cwd(monkeypatch):
    monkeypatch.chdir("prototype")

    path = _root_asset_path("car.glb")

    assert path.exists()
```

For packaged builds, also test the frozen path:

```python
def test_root_asset_path_finds_bundled_assets_when_frozen(monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", str(PROJECT_ROOT), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    path = _root_asset_path("car.glb")

    assert path == PROJECT_ROOT / "car.glb"
```

## Why This Matters

UI smoke tests often run from the repository root, while app commands, editable installs, developer shells, and PyInstaller bundles each see a different runtime root. Cwd-dependent fixture lookup creates a false sense of safety: tests pass, but the documented manual workflow or packaged exe fails.

## When to Apply

Apply this whenever the app references project-root fixtures, sample CSVs, bundled model files, storyboard assets, report templates, or benchmark inputs. Prefer explicit project/session paths once persistence exists; use source-derived fallback only for prototype and development fixtures. For PyInstaller, bundle required root assets in the spec and keep `_MEIPASS` as the first lookup candidate.
