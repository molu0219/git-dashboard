# Git Dashboard

A terminal-based TUI dashboard for monitoring multiple Git projects at a glance.

![Python](https://img.shields.io/badge/python-3.8+-blue) ![Textual](https://img.shields.io/badge/tui-textual-purple)

## Features

- **Project overview** — see all Git repos, current branch, and uncommitted changes in one view
- **Featured projects** — pin active projects to the top with `f`, persisted across sessions
- **Status tab** — `git status -s` style display with color-coded M/A/D/U/?? indicators, staged and unstaged diff stat
- **Log tab** — recent commits with author and relative time via `--pretty=format`
- **Graph tab** — full branch history with `--oneline --graph --decorate --all`

## Installation

**Requires Python 3.8+**

```bash
python3 -m venv ~/.git-dashboard-venv
~/.git-dashboard-venv/bin/pip install textual
```

Add to `~/.bashrc`:

```bash
alias gitdash='~/.git-dashboard-venv/bin/python3 /path/to/dashboard.py'
```

## Usage

```bash
gitdash
```

## Keybindings

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate projects |
| `f` | Toggle ★ Featured |
| `1` | Status tab |
| `2` | Log tab |
| `3` | Graph tab |
| `r` | Refresh all |
| `q` | Quit |

## Config

By default, scans all Git repos inside:

```
/mnt/c/Users/Joey Chen/Desktop/Joey/Blockchain/claude code
```

Change `PROJECTS_DIR` at the top of `dashboard.py` to your projects directory.

Featured project selections are saved to `~/.git-dashboard-featured.json`.
