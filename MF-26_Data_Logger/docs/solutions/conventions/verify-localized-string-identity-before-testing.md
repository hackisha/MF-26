---
title: "Verify localized string identity before testing"
date: "2026-06-04"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "localization"
  - "tests"
  - "windows-console"
  - "mojibake"
---

# Verify Localized String Identity Before Testing

## Context

Some PySide6 shell tests display Korean UI labels as mojibake in the Windows
terminal, while the Python source and runtime strings are valid UTF-8. Copying
the terminal rendering into a test can create a different string from the real
sidebar group key, causing assertions such as `sidebar_item_titles(...)` to fail
even though the UI data is correct.

## Guidance

When a localized label looks corrupted in terminal output, verify the string
identity from the file or runtime before using it as a key in code or tests.
Prefer a quick unicode-escape or code-point check over copying the console
rendering directly:

```powershell
$lines = [System.IO.File]::ReadAllLines(
    (Resolve-Path 'tests/test_ui_shell.py'),
    [System.Text.Encoding]::UTF8
)
```

For runtime dictionaries, inspect the actual Python value rather than the
terminal glyphs:

```powershell
.\.venv\Scripts\python.exe -c "from mflog_proto.ui.main_window import SIDEBAR_GROUPS; print([k.encode('unicode_escape').decode() for k in SIDEBAR_GROUPS])"
```

Use the verified runtime key in assertions, and keep the test focused on the UI
behavior being added.

## Why This Matters

Mojibake is a display problem, but copied mojibake becomes a data problem. A test
that uses the wrong copied literal fails for the wrong reason and can hide the
real behavior under test.

## When to Apply

Apply this whenever editing tests or code that references localized UI labels,
sidebar group keys, menu titles, tab titles, or other strings that appear
corrupted in Windows terminal output.
