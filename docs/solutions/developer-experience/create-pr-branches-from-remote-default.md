---
title: Create PR Branches From The Remote Default Branch
date: 2026-05-24
category: developer-experience
module: git
problem_type: developer_experience
component: version_control
severity: medium
applies_when:
  - "Opening a pull request from a branch created outside the repository's current default-branch history"
  - "Moving work from a local prototype branch into an existing GitHub repository"
tags:
  - git
  - github
  - pull-request
  - worktree
---

# Create PR Branches From The Remote Default Branch

## Context

GitHub rejects a pull request when the head branch has no merge base with the target branch. The API error can look like `Validation Failed` with a message that the branch `has no history in common with main`.

## Guidance

Before opening a PR, verify that the feature branch shares history with the remote default branch:

```bash
git fetch origin main
git merge-base HEAD origin/main
```

If `git merge-base` exits non-zero, do not try to open the PR from that branch. Create a clean PR branch from the remote default branch, then move only the intended files or commits onto it:

```bash
git worktree add -b codex/example-pr .worktrees/codex-example-pr origin/main
git checkout prototype-branch -- path/to/app path/to/tests README.md
git commit -m "feat: add example capability"
git push -u origin HEAD
```

When copying files into the main-based branch, preserve existing repository directories unless the change intentionally removes them.

Before pushing follow-up commits to an existing PR branch, check that the PR is still open:

```bash
gh pr view --json number,state,merged,headRefName,baseRefName
```

If the PR is already merged or closed, create a new branch from the latest remote default branch and move only the intended follow-up files onto it. Pushing to the old head branch after merge will not update the closed PR.

## Why This Matters

An unrelated-history branch can pass local tests and still be impossible to review or merge on GitHub. Rebuilding the PR branch from `origin/main` keeps the diff reviewable, preserves existing repository contents, and avoids a confusing 422 failure during PR creation.

## When to Apply

- A feature branch started from an empty or unrelated local repository.
- `git merge-base HEAD origin/main` returns no SHA.
- GitHub says the branch has no history in common with the target branch.

## Related

- `docs/solutions/build-errors/windows-unicode-worktree-node-builds.md`
