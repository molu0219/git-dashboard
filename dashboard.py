#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Label, Static, ListView, ListItem, TabbedContent, TabPane, Rule
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.binding import Binding
from textual.reactive import reactive
from textual import on
import subprocess
import json
from pathlib import Path

PROJECTS_DIR = Path("/mnt/c/Users/Joey Chen/Desktop/Joey/Blockchain/claude code")
FEATURED_FILE = Path.home() / ".git-dashboard-featured.json"

STATUS_COLORS = {
    "M": "yellow",
    "A": "green",
    "D": "red",
    "U": "magenta",
    "?": "dim",
    "R": "cyan",
    "C": "cyan",
}


def load_featured():
    if FEATURED_FILE.exists():
        return set(json.loads(FEATURED_FILE.read_text()))
    return set()


def save_featured(featured: set):
    FEATURED_FILE.write_text(json.dumps(list(featured)))


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
    changes = len([l for l in porcelain.splitlines() if l.strip()])

    # Parse status lines with XY codes
    status_lines = []
    for line in porcelain.splitlines():
        if len(line) >= 2:
            xy = line[:2]
            fname = line[3:]
            status_lines.append((xy, fname))

    # Graph log
    graph_log = run_git(path, ["log", "--oneline", "--graph", "--decorate", "--all", "-15"])

    # Verbose diff (staged)
    diff_staged = run_git(path, ["diff", "--cached", "--stat"])
    # Unstaged diff stat
    diff_unstaged = run_git(path, ["diff", "--stat"])

    # Recent commits formatted
    log_pretty = run_git(path, ["log", "--pretty=format:%h|%an|%ar|%s", "-10"])

    return {
        "branch": branch or "?",
        "changes": changes,
        "status_lines": status_lines,
        "graph_log": graph_log,
        "diff_staged": diff_staged,
        "diff_unstaged": diff_unstaged,
        "log_pretty": log_pretty,
    }


def format_status_line(xy: str, fname: str) -> str:
    from rich.markup import escape
    x, y = xy[0], xy[1]
    staged_sym = x if x != " " else "-"
    unstaged_sym = y if y != " " else "-"
    color = STATUS_COLORS.get(x if x != " " else y, "white")
    label = {
        "M": "modified",
        "A": "added   ",
        "D": "deleted ",
        "U": "conflict",
        "R": "renamed ",
        "C": "copied  ",
        "?": "untrack ",
    }.get(x if x != " " else y, "unknown ")
    return f"[{color}]{staged_sym}{unstaged_sym} {label}[/{color}]  {escape(fname)}"


class ProjectItem(ListItem):
    def __init__(self, name: str, branch: str, changes: int, featured: bool):
        super().__init__()
        self.project_name = name
        self.branch = branch
        self.changes = changes
        self.featured = featured

    def compose(self) -> ComposeResult:
        star = "[gold1]★[/gold1]" if self.featured else " "
        if self.changes > 0:
            change_str = f"[red]{self.changes}![/red]"
        else:
            change_str = "[green]✓[/green]"
        bc = "cyan" if self.branch == "dev" else "yellow" if self.branch == "main" else "white"
        yield Label(
            f" {star} {self.project_name:<22} [{bc}]{self.branch:<6}[/{bc}] {change_str}",
            markup=True,
        )


class StatusTab(Static):
    def update_info(self, name: str, info: dict):
        bc = "cyan" if info["branch"] == "dev" else "yellow"
        lines = [f"[bold white]{name}[/bold white]  [{bc}]  {info['branch']}[/{bc}]", ""]

        if not info["status_lines"]:
            lines.append("[green]✓ Working tree clean[/green]")
        else:
            lines.append(f"[bold]Changes ({info['changes']}):[/bold]")
            for xy, fname in info["status_lines"]:
                lines.append("  " + format_status_line(xy, fname))

        if info["diff_staged"]:
            from rich.markup import escape
            lines += ["", "[bold yellow]Staged diff stat:[/bold yellow]"]
            for l in info["diff_staged"].splitlines():
                lines.append(f"  [yellow]{escape(l)}[/yellow]")

        if info["diff_unstaged"]:
            from rich.markup import escape
            lines += ["", "[bold]Unstaged diff stat:[/bold]"]
            for l in info["diff_unstaged"].splitlines():
                lines.append(f"  {escape(l)}")

        self.update("\n".join(lines))


class LogTab(Static):
    def update_info(self, info: dict):
        lines = ["[bold]Recent Commits:[/bold]", ""]
        if info["log_pretty"]:
            for entry in info["log_pretty"].splitlines():
                parts = entry.split("|", 3)
                if len(parts) == 4:
                    sha, author, when, msg = parts
                    lines.append(
                        f"  [dim]{sha}[/dim] [cyan]{msg}[/cyan]"
                    )
                    lines.append(f"         [dim]{author} · {when}[/dim]")
                    lines.append("")
        else:
            lines.append("  [dim](no commits)[/dim]")
        self.update("\n".join(lines))


class GraphTab(Static):
    def update_info(self, info: dict):
        from rich.markup import escape
        lines = ["[bold]Branch Graph:[/bold]", ""]
        if info["graph_log"]:
            for l in info["graph_log"].splitlines():
                # Separate graph prefix from commit message to color safely
                safe = escape(l)
                # Highlight commit markers after escaping
                safe = safe.replace("\\*", "[cyan]*[/cyan]")
                lines.append(f"  {safe}")
        else:
            lines.append("  [dim](no history)[/dim]")
        self.update("\n".join(lines))


class GitDashboard(App):
    CSS = """
    Screen { background: #080c18; }
    Header { background: #0f1428; color: #00d4ff; }
    Footer {
        background: #0f1428;
        color: #aab;
    }
    Footer > .footer--key {
        background: #1e2540;
        color: #00d4ff;
    }
    Footer > .footer--highlight {
        background: #2a3560;
        color: #ffffff;
    }

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
    ListItem {
        background: #0b0f1e;
        color: #c0c8e0;
        padding: 0;
    }
    ListItem:hover { background: #141a30; }
    ListItem.--highlight { background: #1a2245; }
    ListItem.-disabled {
        background: #0b0f1e;
        opacity: 0.6;
        padding: 0;
    }

    #right-panel {
        border: solid #1e2540;
        background: #0b0f1e;
    }
    TabbedContent { background: #0b0f1e; }
    TabPane { padding: 1 2; background: #0b0f1e; color: #c0c8e0; }

    StatusTab, LogTab, GraphTab { color: #c0c8e0; }

    #keys-bar {
        height: 1;
        background: #0f1428;
        color: #556;
        padding: 0 1;
    }
    .key-hint-key {
        background: #1e2540;
        color: #00d4ff;
        padding: 0 1;
    }
    .key-hint-desc {
        color: #778;
        padding: 0 1 0 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("f", "toggle_featured", "★ Featured", show=True),
        Binding("r", "refresh_all", "Refresh", show=True),
        Binding("1", "show_tab_status", "Status", show=True),
        Binding("2", "show_tab_log", "Log", show=True),
        Binding("3", "show_tab_graph", "Graph", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.featured = load_featured()
        self.projects = get_projects()
        self.project_infos: dict = {}

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
        yield Static(
            " [on #1e2540][#00d4ff] ↑↓ [/][/#00d4ff][/on #1e2540][#778] navigate [/#778]"
            "  [on #1e2540][#00d4ff] f [/][/#00d4ff][/on #1e2540][#778] toggle ★ featured [/#778]"
            "  [on #1e2540][#00d4ff] 1 [/][/#00d4ff][/on #1e2540][#778] status [/#778]"
            "  [on #1e2540][#00d4ff] 2 [/][/#00d4ff][/on #1e2540][#778] log [/#778]"
            "  [on #1e2540][#00d4ff] 3 [/][/#00d4ff][/on #1e2540][#778] graph [/#778]"
            "  [on #1e2540][#00d4ff] r [/][/#00d4ff][/on #1e2540][#778] refresh [/#778]"
            "  [on #1e2540][#00d4ff] q [/][/#00d4ff][/on #1e2540][#778] quit [/#778]",
            id="keys-bar", markup=True
        )

    def on_mount(self):
        self.title = "Git Dashboard"
        self.sub_title = str(PROJECTS_DIR)
        self.load_projects()

    def load_projects(self):
        lv = self.query_one("#project-list", ListView)
        lv.clear()
        self.project_infos = {}

        featured_projects = [p for p in self.projects if p.name in self.featured]
        other_projects = [p for p in self.projects if p.name not in self.featured]

        for p in featured_projects + other_projects:
            info = get_project_info(p)
            self.project_infos[p.name] = info

        if featured_projects:
            lv.append(ListItem(Label(" [gold1]★ FEATURED[/gold1]", markup=True), disabled=True))
            for p in featured_projects:
                info = self.project_infos[p.name]
                lv.append(ProjectItem(p.name, info["branch"], info["changes"], True))

        if other_projects:
            lv.append(ListItem(Label(" [dim]─ PROJECTS[/dim]", markup=True), disabled=True))
            for p in other_projects:
                info = self.project_infos[p.name]
                lv.append(ProjectItem(p.name, info["branch"], info["changes"], False))

        # Focus first selectable item
        for i, item in enumerate(lv._nodes):
            if hasattr(item, "project_name"):
                lv.index = i
                self._show_detail(item.project_name)
                break

    def _show_detail(self, name: str):
        info = self.project_infos.get(name)
        if not info:
            return
        self.query_one("#status-view", StatusTab).update_info(name, info)
        self.query_one("#log-view", LogTab).update_info(info)
        self.query_one("#graph-view", GraphTab).update_info(info)

    @on(ListView.Highlighted)
    def on_list_highlighted(self, event: ListView.Highlighted):
        if event.item and hasattr(event.item, "project_name"):
            self._show_detail(event.item.project_name)

    def action_toggle_featured(self):
        lv = self.query_one("#project-list", ListView)
        if lv.highlighted_child and hasattr(lv.highlighted_child, "project_name"):
            name = lv.highlighted_child.project_name
            if name in self.featured:
                self.featured.discard(name)
            else:
                self.featured.add(name)
            save_featured(self.featured)
            self.load_projects()

    def action_refresh_all(self):
        self.load_projects()
        self.notify("Refreshed")

    def action_show_tab_status(self):
        self.query_one("#tabs", TabbedContent).active = "tab-status"

    def action_show_tab_log(self):
        self.query_one("#tabs", TabbedContent).active = "tab-log"

    def action_show_tab_graph(self):
        self.query_one("#tabs", TabbedContent).active = "tab-graph"


if __name__ == "__main__":
    GitDashboard().run()
