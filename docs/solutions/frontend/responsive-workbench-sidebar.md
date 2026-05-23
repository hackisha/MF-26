---
title: "Collapse fixed workbench sidebars on narrow viewports"
date: 2026-05-23
category: frontend
problem_type: ui_regression
component: Elec_app workbench shell
tags:
  - css
  - responsive-layout
  - sidebar
  - visual-qa
---

# Collapse fixed workbench sidebars on narrow viewports

## Problem

The Elec App workbench shell used a fixed-width sidebar with a two-column grid. On narrow in-app browser widths, the sidebar left too little room for the workspace content and created horizontal overflow.

## Symptoms

- `document.documentElement.scrollWidth` is larger than `clientWidth`.
- Wiring/debug panels feel cramped even though the page appears usable.
- Header metadata or upload controls can push beyond the visible viewport.

## Solution

At tablet/mobile widths, collapse the shell from sidebar layout to a single-column layout and turn the rail into a compact top navigation grid.

```css
@media (max-width: 820px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .app-sidebar {
    position: static;
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid #1e3b43;
  }

  .workspace-rail {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
```

## Prevention

After adding a persistent sidebar, verify at the actual Codex in-app browser width by checking both the screenshot and:

```js
document.documentElement.scrollWidth === document.documentElement.clientWidth
```

