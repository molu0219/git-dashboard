#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.widgets import Header, Label, Static, ListView, ListItem, TabbedContent, TabPane
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.binding import Binding
from textual import on
import subprocess
import json
import re
from pathlib import Path

PROJECTS_DIR = Path("/mnt/c/Users/Joey Chen/Desktop/Joey/Blockchain/claude code")
FEATURED_FILE = Path.home() / ".git-dashboard-featured.json"

STATUS_COLORS = {
    "M": "yellow", "A": "green", "D": "red",
    "U": "magenta", "?": "dim", "R": "cyan", "C": "cyan",
}
STATUS_LABELS = {
    "M": "modified", "A": "added   ", "D": "deleted ",
    "U": "conflict", "R": "renamed ", "C": "copied  ", "?": "untrack ",
}


# ── persistence ──────────────────────────────────────────────────────────────

def load_featured():
    if FEATURED_FILE.exists():
        return set(json.loads(FEATURED_FILE.read_text()))
    return set()

def save_featured(featured: set):
    FEATURED_FILE.write_text(json.dumps(list(featured)))


# ── git helpers ───────────────────────────────────────────────────────────────

def get_projects():
    return sorted(
        [d for d in PROJECTS_DIR.iterdir() if d.is_dir() and (d / ".git").exists()],
        key=lambda x: x.name,
    )

def run_git(path, args):
    r = subprocess.run(["git"] + args, cwd=path, capture_output=True, text=True)
    return r.stdout.strip()

def get_project_info(path):
    branch = run_git(path, ["branch", "--show-current"])
    porcelain = run_git(path, ["status", "--porcelain"])
    status_lines = [(l[:2], l[3:]) for l in porcelain.splitlines() if len(l) >= 2]
    return {
        "branch": branch or "?",
        "changes": len(status_lines),
        "status_lines": status_lines,
        "graph_log": run_git(path, ["log", "--oneline", "--graph", "--decorate", "--all", "-15"]),
        "diff_staged": run_git(path, ["diff", "--cached", "--stat"]),
        "diff_unstaged": run_git(path, ["diff", "--stat"]),
        "log_pretty": run_git(path, ["log", "--pretty=format:%h|%an|%ar|%s", "-10"]),
    }

def format_status_line(xy, fname):
    from rich.markup import escape
    x, y = xy[0], xy[1]
    key = x if x != " " else y
    color = STATUS_COLORS.get(key, "white")
    label = STATUS_LABELS.get(key, "unknown ")
    sx = x if x != " " else "-"
    sy = y if y != " " else "-"
    return f"[{color}]{sx}{sy} {label}[/{color}]  {escape(fname)}"


# ── markdown helpers ──────────────────────────────────────────────────────────

def render_md(text: str) -> tuple[str, list[tuple[int, str]]]:
    """Return (rich_markup_string, [(line_index, heading_text), ...])"""
    from rich.markup import escape
    lines_out = []
    headings = []
    for line in text.splitlines():
        m = re.match(r'^(#{1,3})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            title = escape(m.group(2))
            headings.append((len(lines_out), m.group(2)))
            if level == 1:
                lines_out.append(f"[bold cyan]{'━' * 40}[/bold cyan]")
                lines_out.append(f"[bold cyan]  {title}[/bold cyan]")
                lines_out.append(f"[bold cyan]{'━' * 40}[/bold cyan]")
            elif level == 2:
                lines_out.append(f"[bold yellow]  ▸ {title}[/bold yellow]")
            else:
                lines_out.append(f"[yellow]    • {title}[/yellow]")
        elif line.startswith("- ") or line.startswith("* "):
            lines_out.append(f"[dim]  ·[/dim] {escape(line[2:])}")
        elif re.match(r'^\[(.)\]', line):
            # TODO-style checkboxes
            m2 = re.match(r'^\[(.)\]\s*(.*)', line)
            if m2:
                mark, rest = m2.group(1), escape(m2.group(2))
                colors = {"x": "green", "~": "cyan", "R": "yellow", "-": "dim", " ": "white"}
                c = colors.get(mark, "white")
                lines_out.append(f"  [{c}][{mark}] {rest}[/{c}]")
        elif line.startswith("|"):
            lines_out.append(f"[dim]{escape(line)}[/dim]")
        elif line.startswith("```"):
            lines_out.append(f"[dim]{escape(line)}[/dim]")
        elif line.startswith(">"):
            lines_out.append(f"[italic dim]{escape(line)}[/italic dim]")
        elif line == "---":
            lines_out.append("[dim]─────────────────────────────────────[/dim]")
        else:
            lines_out.append(escape(line))
    return "\n".join(lines_out), headings


# ── widgets ───────────────────────────────────────────────────────────────────

class ProjectItem(ListItem):
    def __init__(self, name, branch, changes, featured):
        super().__init__()
        self.project_name = name
        self.branch = branch
        self.changes = changes
        self.featured = featured

    def compose(self) -> ComposeResult:
        star = "[gold1]★[/gold1]" if self.featured else " "
        change_str = f"[red]{self.changes}![/red]" if self.changes > 0 else "[green]✓[/green]"
        bc = "cyan" if self.branch == "dev" else "yellow" if self.branch == "main" else "white"
        yield Label(
            f" {star} {self.project_name:<22} [{bc}]{self.branch:<6}[/{bc}] {change_str}",
            markup=True,
        )


class StatusTab(Static):
    def update_info(self, name, info):
        from rich.markup import escape
        bc = "cyan" if info["branch"] == "dev" else "yellow"
        lines = [f"[bold white]{name}[/bold white]  [{bc}]{info['branch']}[/{bc}]", ""]
        if not info["status_lines"]:
            lines.append("[green]✓ Working tree clean[/green]")
        else:
            lines.append(f"[bold]Changes ({info['changes']}):[/bold]")
            for xy, fname in info["status_lines"]:
                lines.append("  " + format_status_line(xy, fname))
        if info["diff_staged"]:
            lines += ["", "[bold yellow]Staged:[/bold yellow]"]
            for l in info["diff_staged"].splitlines():
                lines.append(f"  [yellow]{escape(l)}[/yellow]")
        if info["diff_unstaged"]:
            lines += ["", "[bold]Unstaged:[/bold]"]
            for l in info["diff_unstaged"].splitlines():
                lines.append(f"  {escape(l)}")
        self.update("\n".join(lines))


class LogTab(Static):
    def update_info(self, info):
        lines = ["[bold]Recent Commits:[/bold]", ""]
        if info["log_pretty"]:
            for entry in info["log_pretty"].splitlines():
                parts = entry.split("|", 3)
                if len(parts) == 4:
                    sha, author, when, msg = parts
                    lines.append(f"  [dim]{sha}[/dim] [cyan]{msg}[/cyan]")
                    lines.append(f"         [dim]{author} · {when}[/dim]")
                    lines.append("")
        else:
            lines.append("  [dim](no commits)[/dim]")
        self.update("\n".join(lines))


class GraphTab(Static):
    def update_info(self, info):
        from rich.markup import escape
        lines = ["[bold]Branch Graph:[/bold]", ""]
        for l in (info["graph_log"].splitlines() if info["graph_log"] else []):
            safe = escape(l)
            safe = safe.replace("\\*", "[cyan]*[/cyan]")
            lines.append(f"  {safe}")
        if not info["graph_log"]:
            lines.append("  [dim](no history)[/dim]")
        self.update("\n".join(lines))


class DocTab(Static):
    """Displays PRD / TODO / DECISION markdown with section jump support."""

    def __init__(self, doc_id: str, **kwargs):
        super().__init__(**kwargs)
        self._doc_id = doc_id
        self._headings: list[tuple[int, str]] = []
        self._heading_idx = 0
        self._project_path: Path | None = None

    def load(self, project_path: Path):
        self._project_path = project_path
        md_file = project_path / f"{self._doc_id}.md"
        if not md_file.exists():
            self.update(f"[dim]No {self._doc_id}.md found in this project.[/dim]")
            self._headings = []
            return
        text = md_file.read_text(encoding="utf-8")
        rendered, headings = render_md(text)
        self._headings = headings
        self._heading_idx = 0
        self.update(rendered)

    def jump_next(self):
        if not self._headings:
            return
        self._heading_idx = (self._heading_idx + 1) % len(self._headings)
        self._scroll_to_heading()

    def jump_prev(self):
        if not self._headings:
            return
        self._heading_idx = (self._heading_idx - 1) % len(self._headings)
        self._scroll_to_heading()

    def _scroll_to_heading(self):
        # Scroll the parent ScrollableContainer to the heading line
        line_no, _ = self._headings[self._heading_idx]
        try:
            container = self.parent
            if hasattr(container, "scroll_to"):
                container.scroll_to(y=line_no, animate=False)
        except Exception:
            pass


# ── app ───────────────────────────────────────────────────────────────────────

class GitDashboard(App):
    CSS = """
    Screen { background: #080c18; }
    Header { background: #0f1428; color: #00d4ff; }

    #left-panel {
        width: 38;
        border: solid #1e2540;
        background: #0b0f1e;
    }
    #section-title {
        background: #0f1428;
        color: #00d4ff;
        padding: 0 1;
        text-style: bold;
    }
    ListView { background: #0b0f1e; }
    ListItem { background: #0b0f1e; color: #c0c8e0; padding: 0; }
    ListItem:hover { background: #141a30; }
    ListItem.--highlight { background: #1a2245; }
    ListItem.-disabled { background: #0b0f1e; opacity: 0.6; padding: 0; }

    #right-panel { border: solid #1e2540; background: #0b0f1e; }
    TabbedContent { background: #0b0f1e; }
    TabPane { padding: 1 2; background: #0b0f1e; color: #c0c8e0; }
    StatusTab, LogTab, GraphTab, DocTab { color: #c0c8e0; }

    #keys-bar {
        height: 1;
        background: #0f1428;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f", "toggle_featured", "★ Featured"),
        Binding("1", "show_tab", "tab-status"),
        Binding("2", "show_tab", "tab-log"),
        Binding("3", "show_tab", "tab-graph"),
        Binding("4", "show_tab", "tab-prd"),
        Binding("5", "show_tab", "tab-todo"),
        Binding("6", "show_tab", "tab-decision"),
        Binding("r", "refresh_all", "Refresh"),
        Binding("]", "section_next", "Next §"),
        Binding("[", "section_prev", "Prev §"),
    ]

    _KEYS_TEXT = (
        " [bold cyan on #1e2540] ↑↓ [/] [#778]nav[/#778]"
        "  [bold cyan on #1e2540] f [/] [#778]★ featured[/#778]"
        "  [bold cyan on #1e2540] 1 [/] [#778]status[/#778]"
        "  [bold cyan on #1e2540] 2 [/] [#778]log[/#778]"
        "  [bold cyan on #1e2540] 3 [/] [#778]graph[/#778]"
        "  [bold cyan on #1e2540] 4 [/] [#778]PRD[/#778]"
        "  [bold cyan on #1e2540] 5 [/] [#778]TODO[/#778]"
        "  [bold cyan on #1e2540] 6 [/] [#778]DECISION[/#778]"
        "  [bold cyan on #1e2540] ]/[ [/] [#778]next/prev §[/#778]"
        "  [bold cyan on #1e2540] r [/] [#778]refresh[/#778]"
        "  [bold cyan on #1e2540] q [/] [#778]quit[/#778]"
    )

    def __init__(self):
        super().__init__()
        self.featured = load_featured()
        self.projects = get_projects()
        self.project_infos: dict = {}
        self._current_project: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="left-panel"):
                yield Label(" Projects", id="section-title")
                yield ListView(id="project-list")
            with Vertical(id="right-panel"):
                with TabbedContent(id="tabs"):
                    with TabPane("Status [1]", id="tab-status"):
                        with ScrollableContainer():
                            yield StatusTab(id="status-view", markup=True)
                    with TabPane("Log [2]", id="tab-log"):
                        with ScrollableContainer():
                            yield LogTab(id="log-view", markup=True)
                    with TabPane("Graph [3]", id="tab-graph"):
                        with ScrollableContainer():
                            yield GraphTab(id="graph-view", markup=True)
                    with TabPane("PRD [4]", id="tab-prd"):
                        with ScrollableContainer(id="scroll-prd"):
                            yield DocTab("PRD", id="prd-view", markup=True)
                    with TabPane("TODO [5]", id="tab-todo"):
                        with ScrollableContainer(id="scroll-todo"):
                            yield DocTab("TODO", id="todo-view", markup=True)
                    with TabPane("DECISION [6]", id="tab-decision"):
                        with ScrollableContainer(id="scroll-decision"):
                            yield DocTab("DECISION", id="decision-view", markup=True)
        yield Static(self._KEYS_TEXT, id="keys-bar", markup=True)

    def on_mount(self):
        self.title = "Git Dashboard"
        self.sub_title = str(PROJECTS_DIR)
        self.load_projects()

    def load_projects(self):
        lv = self.query_one("#project-list", ListView)
        lv.clear()
        self.project_infos = {}
        featured_p = [p for p in self.projects if p.name in self.featured]
        other_p = [p for p in self.projects if p.name not in self.featured]
        for p in featured_p + other_p:
            self.project_infos[p.name] = get_project_info(p)
        if featured_p:
            lv.append(ListItem(Label(" [gold1]★ FEATURED[/gold1]", markup=True), disabled=True))
            for p in featured_p:
                info = self.project_infos[p.name]
                lv.append(ProjectItem(p.name, info["branch"], info["changes"], True))
        if other_p:
            lv.append(ListItem(Label(" [dim]─ PROJECTS[/dim]", markup=True), disabled=True))
            for p in other_p:
                info = self.project_infos[p.name]
                lv.append(ProjectItem(p.name, info["branch"], info["changes"], False))
        for i, item in enumerate(lv._nodes):
            if hasattr(item, "project_name"):
                lv.index = i
                self._show_detail(item.project_name)
                break

    def _show_detail(self, name: str):
        info = self.project_infos.get(name)
        path = PROJECTS_DIR / name
        self._current_project = path
        if not info:
            return
        self.query_one("#status-view", StatusTab).update_info(name, info)
        self.query_one("#log-view", LogTab).update_info(info)
        self.query_one("#graph-view", GraphTab).update_info(info)
        self.query_one("#prd-view", DocTab).load(path)
        self.query_one("#todo-view", DocTab).load(path)
        self.query_one("#decision-view", DocTab).load(path)

    @on(ListView.Highlighted)
    def on_list_highlighted(self, event: ListView.Highlighted):
        if event.item and hasattr(event.item, "project_name"):
            self._show_detail(event.item.project_name)

    def action_toggle_featured(self):
        lv = self.query_one("#project-list", ListView)
        if lv.highlighted_child and hasattr(lv.highlighted_child, "project_name"):
            name = lv.highlighted_child.project_name
            self.featured.discard(name) if name in self.featured else self.featured.add(name)
            save_featured(self.featured)
            self.load_projects()

    def action_refresh_all(self):
        self.load_projects()
        self.notify("Refreshed")

    def action_show_tab(self, tab_id: str = ""):
        # Called via number key bindings — map key to tab id
        key_map = {"1": "tab-status", "2": "tab-log", "3": "tab-graph",
                   "4": "tab-prd", "5": "tab-todo", "6": "tab-decision"}
        # tab_id comes from binding parameter workaround — use pressed key instead
        pass

    def on_key(self, event):
        tab_map = {"1": "tab-status", "2": "tab-log", "3": "tab-graph",
                   "4": "tab-prd", "5": "tab-todo", "6": "tab-decision"}
        if event.key in tab_map:
            self.query_one("#tabs", TabbedContent).active = tab_map[event.key]
        elif event.key == "]":
            self._active_doc_tab_action("jump_next")
        elif event.key == "[":
            self._active_doc_tab_action("jump_prev")

    def _active_doc_tab_action(self, method: str):
        active = self.query_one("#tabs", TabbedContent).active
        doc_map = {"tab-prd": "#prd-view", "tab-todo": "#todo-view", "tab-decision": "#decision-view"}
        if active in doc_map:
            widget = self.query_one(doc_map[active], DocTab)
            getattr(widget, method)()

    def action_section_next(self):
        self._active_doc_tab_action("jump_next")

    def action_section_prev(self):
        self._active_doc_tab_action("jump_prev")


if __name__ == "__main__":
    GitDashboard().run()
