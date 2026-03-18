# git-dashboard

When you're working with AI coding assistants — Claude Code, Cursor, Copilot, or any agent-driven workflow — the AI moves fast. Tabs multiply. Context switches constantly. It's easy to lose track of what's actually been changed, which branch you're on, or where a project stands.

**git-dashboard** is a terminal TUI built for exactly this: a human-readable view of all your Git projects at once. While the AI writes code, you stay oriented — seeing live status, recent commits, and project planning docs without leaving the terminal or breaking your flow.

> **Scope:** Read-only overview. For actual Git operations (commit, push, merge), use your terminal or [lazygit](https://github.com/jesseduffield/lazygit).

---

## Features

| Tab | Key | Source | What you see |
|-----|-----|--------|--------------|
| Status | `1` | `git status -s`, `git diff --stat` | M/A/D/U/?? indicators, staged vs unstaged |
| Log | `2` | `git log --pretty=format:...` | Commit hash · message · author · relative time |
| Graph | `3` | `git log --oneline --graph --decorate --all` | Branch topology |
| PRD | `4` | `PRD.md` | Product spec with section navigation |
| TODO | `5` | `TODO.md` | Task list with `[ ]` `[~]` `[x]` `[-]` status colours |
| DECISION | `6` | `DECISION.md` | Architecture decision log |
| Tokens | `7` | `~/.claude/projects/*.jsonl` | Claude token usage and cost per project |

**Featured projects** — pin active repos to the top with `f`. Persisted across sessions.

**Section jump** — press `n` / `p` inside any doc tab to jump between `##` headings.

**Token tab** — press `7` to see Claude token usage and cost. Shows global summary across all projects or per-project detail (input, output, cache) when a project is selected. Includes commit-to-cost correlation: each git commit is mapped to the Claude sessions that preceded it, so you can see how much AI usage went into each commit.

---

## When is this useful?

- You have 5+ repos open at once and want a single pane of glass
- Quickly spot which repos have uncommitted work before ending a session
- Context-switching — instantly see which branch each project is on
- Check recent commit history or planning docs without opening an editor

---

## Installation

Requires **Python 3.8+**

```bash
python3 -m venv ~/.git-dashboard-venv
~/.git-dashboard-venv/bin/pip install textual
```

Add alias to `~/.bashrc`:

```bash
alias gitdash='~/.git-dashboard-venv/bin/python3 /path/to/dashboard.py'
source ~/.bashrc
```

---

## Configuration

`PROJECTS_DIR` is resolved in priority order:

**1. Environment variable**
```bash
GIT_DASHBOARD_DIR=/path/to/projects gitdash
```

**2. Config file** — create `~/.git-dashboard.json`:
```json
{ "projects_dir": "/path/to/your/projects" }
```

**3. Default** — current working directory when `gitdash` is run.

Featured selections are saved to `~/.git-dashboard-featured.json`.

---

## Project doc conventions

Place these files in any project root to unlock the doc tabs:

| File | Purpose |
|------|---------|
| `PRD.md` | Product spec / feature definitions |
| `TODO.md` | Task list using `[ ]` `[~]` `[x]` `[-]` `[R]` markers |
| `DECISION.md` | Architecture decision log |

### TODO status markers

| Marker | Meaning |
|--------|---------|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[R]` | Ready for review |
| `[x]` | Done |
| `[-]` | On hold |

---

## Keybindings

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate project list |
| `f` | Toggle ★ Featured on selected project |
| `1` | Status tab |
| `2` | Log tab |
| `3` | Graph tab |
| `4` | PRD tab |
| `5` | TODO tab |
| `6` | DECISION tab |
| `7` | Tokens tab (Claude usage) |
| `n` / `p` | Jump to next / previous section in doc tabs |
| `r` | Refresh all projects |
| `q` | Quit |

---

## Layout

```
┌──────────────────────────────────────────────────────────────┐
│ Git Dashboard                                    12:34:56     │
├──────────────────┬───────────────────────────────────────────┤
│  ★ FEATURED      │ Status[1] Log[2] Graph[3] PRD[4] ...      │
│  ★ token-analysis│                                           │
│  ★ polymarket    │  token-analysis  branch: dev              │
│  ─ PROJECTS      │                                           │
│    personal-web  │  ✓ Working tree clean                     │
│    polymarket-cli│                                           │
│                  │  Recent commits:                          │
│                  │   a1b2c3 Add signal panel                 │
│                  │           Joey · 2 hours ago              │
├──────────────────┴───────────────────────────────────────────┤
│ ↑↓ nav  f ★  1 status  2 log  3 graph  4 PRD  5 TODO  q quit │
└──────────────────────────────────────────────────────────────┘
```

---

## Status symbol reference

| Symbol | Meaning |
|--------|---------|
| `M` | Modified |
| `A` | Added (staged) |
| `D` | Deleted |
| `U` | Merge conflict |
| `??` | Untracked |
| `✓` | Clean |
