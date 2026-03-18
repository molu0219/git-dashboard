# git-dashboard

A terminal dashboard for developers who maintain **multiple Git repositories**.
Gives you an instant read on every project's status without switching directories.

> **Scope:** Read-only overview. For actual Git operations (commit, merge, rebase), use your terminal or [lazygit](https://github.com/jesseduffield/lazygit).

---

## What it does

| Panel | Source command | What you see |
|-------|---------------|--------------|
| Project list | `git branch`, `git status --porcelain` | Branch, uncommitted change count |
| Status tab | `git status -s`, `git diff --stat` | M/A/D/U/?? indicators, staged vs unstaged |
| Log tab | `git log --pretty=format:...` | Commit hash · message · author · relative time |
| Graph tab | `git log --oneline --graph --decorate --all` | Branch topology (subway-map style) |

**Featured projects** — pin the repos you're actively working on.
They float to the top of the list and are persisted across sessions (`~/.git-dashboard-featured.json`).

---

## When is this useful?

- You have 5+ repos open at once and want a single pane of glass
- You want to quickly spot which repos have uncommitted work before ending a session
- You're context-switching and need to remember which branch each project is on
- Team standup or PR review — quickly check recent commit history across repos

---

## Installation

Requires **Python 3.8+**

```bash
# Create a virtual environment
python3 -m venv ~/.git-dashboard-venv
~/.git-dashboard-venv/bin/pip install textual

# Clone or download dashboard.py, then add alias to ~/.bashrc
echo "alias gitdash='~/.git-dashboard-venv/bin/python3 /path/to/dashboard.py'" >> ~/.bashrc
source ~/.bashrc
```

---

## Configuration

Open `dashboard.py` and set `PROJECTS_DIR` to your projects root:

```python
PROJECTS_DIR = Path("/path/to/your/projects")
```

All subdirectories containing a `.git` folder will appear in the list automatically.

---

## Usage

```bash
gitdash
```

### Keybindings

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate project list |
| `f` | Toggle ★ Featured on selected project |
| `1` | Status tab — file-level changes |
| `2` | Log tab — recent commit history |
| `3` | Graph tab — branch topology |
| `r` | Refresh all projects |
| `q` | Quit |

---

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Git Dashboard                              12:34:56          │
├──────────────────┬──────────────────────────────────────────┤
│  ★ FEATURED      │ ┌ Status ┐ Log   Graph                   │
│  ★ token-analysis│ │                                        │
│  ★ polymarket    │ │ token-analysis  branch: dev            │
│  ─ PROJECTS      │ │                                        │
│    personal-web  │ │ ✓ Working tree clean                   │
│    polymarket-cli│ │                                        │
│                  │ │ Recent commits:                        │
│                  │ │  a1b2c3 Add signal panel               │
│                  │ │         Joey · 2 hours ago             │
│                  │ │                                        │
├──────────────────┴──────────────────────────────────────────┤
│  ↑↓  navigate   f  toggle ★   1  status   2  log   3  graph │
└─────────────────────────────────────────────────────────────┘
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
| `✓` | Clean — nothing to commit |
