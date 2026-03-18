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

### Tokens Tab
- Parse `~/.claude/projects/**/*.jsonl` to compute Claude API usage and cost per project
- Global summary: total cost, sessions, token breakdown (input / output / cache write / cache read), top tools bar chart, all-projects cost table
- Per-project detail: usage totals, top tools, cost correlated to git commits, session list (recent 15)
- Agent tracking: for each session and commit group, list which sub-agent types were invoked (e.g. `Explore×3  Plan×1`) extracted from `Agent` tool_use `input.subagent_type`
- Token pricing configurable via `TOKEN_PRICE` dict (default: `claude-sonnet-4-6` rates)

### UX
- Always-visible keybindings in Footer with command palette (`ctrl+p`)
- Dark cyberpunk colour scheme
- Refresh all projects on demand with `r`

---

## Technical Stack

- **Language:** Python 3.8+
- **TUI framework:** Textual
- **Data source:** local `git` CLI subprocess calls; `~/.claude/projects/**/*.jsonl` for token data
- **Config:** env var `GIT_DASHBOARD_DIR` → `~/.git-dashboard.json` → cwd
- **Persistence:** `~/.git-dashboard-featured.json`

---

## Non-Goals

- No Git write operations (commit, push, merge, rebase)
- No remote repository integration (GitHub API, PRs, issues)
- No multi-user or networked use
