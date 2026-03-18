# git-dashboard — PRD

## Overview

A terminal TUI dashboard for developers managing multiple Git repositories.
Provides a single pane of glass for project status, commit history, and planning docs — without switching directories.

---

## Core Features

### Project List
- Auto-discover all Git repos under a configured root directory
- Show current branch, uncommitted change count per project
- Featured projects — pin active repos to the top, persisted across sessions

### Git Tabs
- **Status** — `git status -s` style with M/A/D/U/?? colour indicators, staged and unstaged diff stat
- **Log** — recent commits with hash, message, author, relative time
- **Graph** — branch topology via `git log --oneline --graph --decorate --all`

### Doc Tabs
- **PRD / TODO / DECISION** — render markdown files from the project root
- Colour-coded TODO markers: `[ ]` `[~]` `[x]` `[-]` `[R]`
- Section navigation with `n` / `p` keys (jump between `##` headings)

### UX
- Always-visible keybindings in Footer with command palette (`ctrl+p`)
- Dark cyberpunk colour scheme
- Refresh all projects on demand with `r`

---

## Technical Stack

- **Language:** Python 3.8+
- **TUI framework:** Textual
- **Data source:** local `git` CLI subprocess calls
- **Config:** `PROJECTS_DIR` constant in `dashboard.py`
- **Persistence:** `~/.git-dashboard-featured.json`

---

## Non-Goals

- No Git write operations (commit, push, merge, rebase)
- No remote repository integration (GitHub API, PRs, issues)
- No multi-user or networked use
