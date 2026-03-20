#!/usr/bin/env python3
"""
git-dashboard — terminal dashboard for managing multiple Git repositories.

Configuration (in priority order):
  1. Environment variable:  GIT_DASHBOARD_DIR=/path/to/projects gitdash
  2. Config file:           ~/.git-dashboard.json  →  { "projects_dir": "/path" }
  3. Default:               current working directory
"""
import os
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rich.markup import escape
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static, TabbedContent, TabPane


# ── config ────────────────────────────────────────────────────────────────────

CONFIG_FILE = Path.home() / ".git-dashboard.json"
FEATURED_FILE = Path.home() / ".git-dashboard-featured.json"


def load_config() -> Path:
    if "GIT_DASHBOARD_DIR" in os.environ:
        return Path(os.environ["GIT_DASHBOARD_DIR"]).expanduser()
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text())
            if "projects_dir" in cfg:
                return Path(cfg["projects_dir"]).expanduser()
        except Exception:
            pass
    return Path.cwd()


PROJECTS_DIR = load_config()
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
CLAUDE_STATS_CACHE = Path.home() / ".claude" / "stats-cache.json"
CLAUDE_SESSION_META_DIR = Path.home() / ".claude" / "usage-data" / "session-meta"

# Token pricing per million (claude-sonnet-4-6) — update if model changes
TOKEN_PRICE = {
    "input": 3.00, "output": 15.00,
    "cache_create": 3.75, "cache_read": 0.30,
}


def load_featured() -> set:
    if FEATURED_FILE.exists():
        try:
            return set(json.loads(FEATURED_FILE.read_text()))
        except Exception:
            pass
    return set()


def save_featured(featured: set):
    FEATURED_FILE.write_text(json.dumps(list(featured)))


# ── git helpers ───────────────────────────────────────────────────────────────

STATUS_COLORS = {
    "M": "yellow", "A": "green", "D": "red",
    "U": "magenta", "?": "dim", "R": "cyan", "C": "cyan",
}
STATUS_LABELS = {
    "M": "modified", "A": "added   ", "D": "deleted ",
    "U": "conflict", "R": "renamed ", "C": "copied  ", "?": "untrack ",
}


def get_projects() -> list[Path]:
    try:
        return sorted(
            [d for d in PROJECTS_DIR.iterdir() if d.is_dir() and (d / ".git").exists()],
            key=lambda x: x.name,
        )
    except Exception:
        return []


def run_git(path: Path, args: list[str]) -> str:
    try:
        r = subprocess.run(
            ["git"] + args, cwd=path, capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()
    except Exception:
        return ""


def get_project_info(path: Path) -> dict:
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


# ── Claude stats helpers ──────────────────────────────────────────────────────

def parse_stats_cache() -> dict | None:
    """Parse ~/.claude/stats-cache.json for global usage stats."""
    if not CLAUDE_STATS_CACHE.exists():
        return None
    try:
        return json.loads(CLAUDE_STATS_CACHE.read_text())
    except Exception:
        return None


def parse_session_metas(project_path: str | None = None) -> list[dict]:
    """Parse session-meta/*.json, optionally filter by project_path."""
    if not CLAUDE_SESSION_META_DIR.exists():
        return []
    metas = []
    for f in CLAUDE_SESSION_META_DIR.iterdir():
        if not f.suffix == ".json":
            continue
        try:
            m = json.loads(f.read_text())
            if project_path and m.get("project_path") != project_path:
                continue
            metas.append(m)
        except Exception:
            continue
    metas.sort(key=lambda x: x.get("start_time", ""), reverse=True)
    return metas


# ── token consumption helpers ─────────────────────────────────────────────────

def _decode_project_name(dir_name: str) -> str:
    skip = {"mnt", "c", "d", "e", "Users", "home", "usr", "Desktop", "Documents", "AppData", "Local"}
    parts = dir_name.lstrip("-").split("-")
    meaningful = [p for p in parts if p and p not in skip]
    if not meaningful:
        return dir_name
    return "/".join(meaningful[-2:]) if len(meaningful) >= 2 else meaningful[-1]


def _compute_cost(usage: dict) -> float:
    return sum(usage.get(k, 0) / 1_000_000 * TOKEN_PRICE[k] for k in TOKEN_PRICE)


def _fmt_tok(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def find_project_claude_dir(project_name: str) -> Path | None:
    """Match a project folder name to its ~/.claude/projects/ directory."""
    if not CLAUDE_PROJECTS_DIR.exists():
        return None
    # Exact suffix match first (most reliable)
    for d in CLAUDE_PROJECTS_DIR.iterdir():
        if not d.is_dir():
            continue
        if d.name.endswith(f"-{project_name}") or d.name == project_name:
            return d
    # Fallback: decoded name contains project name
    for d in CLAUDE_PROJECTS_DIR.iterdir():
        if not d.is_dir():
            continue
        if project_name in _decode_project_name(d.name):
            return d
    return None


def _parse_jsonl_dir(project_dir: Path) -> tuple[dict, dict[str, int], list[dict]]:
    """Returns (usage_totals, tool_counts, sessions_list)."""
    usage = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0}
    tools: dict[str, int] = {}
    sessions = []

    for fpath in set(list(project_dir.glob("*.jsonl")) + list(project_dir.glob("**/*.jsonl"))):
        s_usage = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0}
        s_tools: dict[str, int] = {}
        s_agents: dict[str, int] = {}
        s_ts = None
        try:
            with open(fpath, errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = obj.get("timestamp")
                    if ts and (s_ts is None or ts > s_ts):
                        s_ts = ts
                    if obj.get("type") == "assistant":
                        u = obj.get("message", {}).get("usage", {})
                        s_usage["input"] += u.get("input_tokens", 0)
                        s_usage["output"] += u.get("output_tokens", 0)
                        s_usage["cache_create"] += u.get("cache_creation_input_tokens", 0)
                        s_usage["cache_read"] += u.get("cache_read_input_tokens", 0)
                        for c in obj.get("message", {}).get("content", []):
                            if isinstance(c, dict) and c.get("type") == "tool_use":
                                n = c.get("name", "?")
                                s_tools[n] = s_tools.get(n, 0) + 1
                                if n == "Agent":
                                    agent_type = c.get("input", {}).get("subagent_type", "unknown")
                                    s_agents[agent_type] = s_agents.get(agent_type, 0) + 1
        except Exception:
            continue

        if sum(s_usage.values()) == 0:
            continue

        for k in usage:
            usage[k] += s_usage[k]
        for t, c in s_tools.items():
            tools[t] = tools.get(t, 0) + c

        sessions.append({
            "file": fpath.name,
            "usage": s_usage,
            "cost": _compute_cost(s_usage),
            "tools": s_tools,
            "agents": s_agents,
            "date": s_ts[:16].replace("T", " ") if s_ts else "—",
            "raw_ts": s_ts or "",
        })

    sessions.sort(key=lambda x: x["date"], reverse=True)
    return usage, tools, sessions


def _correlate_commits(project_path: Path, sessions: list[dict]) -> list[dict]:
    """Map each session to the next git commit after it, group by commit."""
    raw = run_git(project_path, ["log", "--format=%h|%s|%aI", "-80"])
    if not raw:
        return []

    commits = []
    for line in raw.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            sha, msg, ts = parts
            commits.append({"sha": sha, "msg": msg.strip(), "ts": ts.strip()})
    # Sort oldest → newest for matching
    commits.sort(key=lambda x: x["ts"])

    # For each session find first commit with ts >= session raw_ts
    groups: dict[str, dict] = {}
    for s in sessions:
        if not s["raw_ts"]:
            continue
        matched = next((c for c in commits if c["ts"] >= s["raw_ts"]), None)
        key = matched["sha"] if matched else "__uncommitted__"
        label = matched["msg"] if matched else "(uncommitted work)"
        if key not in groups:
            groups[key] = {"sha": key[:7] if matched else "—", "msg": label, "sessions": 0, "cost": 0.0,
                           "input": 0, "output": 0, "agents": {}}
        groups[key]["sessions"] += 1
        groups[key]["cost"] += s["cost"]
        groups[key]["input"] += s["usage"]["input"]
        groups[key]["output"] += s["usage"]["output"]
        for a, cnt in s.get("agents", {}).items():
            groups[key]["agents"][a] = groups[key]["agents"].get(a, 0) + cnt

    return sorted(groups.values(), key=lambda x: -x["cost"])


def parse_project_detail(project_name: str, global_data: dict | None = None) -> dict | None:
    d = find_project_claude_dir(project_name)
    if not d:
        return None
    usage, tools, sessions = _parse_jsonl_dir(d)
    project_path = PROJECTS_DIR / project_name
    commits_cost = _correlate_commits(project_path, sessions) if project_path.exists() else []
    cost = _compute_cost(usage)

    # Daily cost aggregation (last 14 days)
    daily: dict[str, float] = {}
    all_agents: dict[str, int] = {}
    for s in sessions:
        if s.get("raw_ts"):
            day = s["raw_ts"][:10]
            daily[day] = daily.get(day, 0) + s["cost"]
        for a, cnt in s.get("agents", {}).items():
            all_agents[a] = all_agents.get(a, 0) + cnt
    daily_14d = []
    for i in range(14):
        d_str = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_14d.append({"date": d_str[5:], "cost": daily.get(d_str, 0)})
    daily_14d.reverse()

    # Rank info
    rank = None
    decoded_name = _decode_project_name(d.name)
    if global_data and "projects" in global_data:
        total_cost = global_data.get("total_cost", 0)
        for idx, p in enumerate(global_data["projects"]):
            if p["name"] == decoded_name:
                rank = {"pos": idx + 1, "total": len(global_data["projects"]),
                        "pct": (cost / total_cost * 100) if total_cost else 0}
                break

    return {
        "name": project_name,
        "usage": usage,
        "cost": cost,
        "tools": dict(sorted(tools.items(), key=lambda x: -x[1])[:10]),
        "sessions": sessions,
        "commits_cost": commits_cost,
        "daily_14d": daily_14d,
        "all_agents": dict(sorted(all_agents.items(), key=lambda x: -x[1])),
        "rank": rank,
    }


def parse_token_data() -> dict:
    if not CLAUDE_PROJECTS_DIR.exists():
        return {"error": f"{CLAUDE_PROJECTS_DIR} not found"}

    all_projects = []
    all_sessions: list[dict] = []
    g_usage = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0}
    g_tools: dict[str, int] = {}
    g_sessions = 0

    for project_dir in sorted(CLAUDE_PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        usage, tools, sessions = _parse_jsonl_dir(project_dir)
        if sum(usage.values()) == 0:
            continue
        for k in g_usage:
            g_usage[k] += usage[k]
        for t, c in tools.items():
            g_tools[t] = g_tools.get(t, 0) + c
        g_sessions += len(sessions)
        all_sessions.extend(sessions)
        latest_ts = sessions[0]["date"] if sessions else None
        all_projects.append({
            "name": _decode_project_name(project_dir.name),
            "usage": usage,
            "cost": _compute_cost(usage),
            "sessions": len(sessions),
            "latest_ts": latest_ts,
        })

    all_projects.sort(key=lambda x: -x["cost"])

    # Date-grouped usage summary (today / 7d / 30d)
    now = datetime.now(timezone.utc)
    cutoffs = {"today": now.replace(hour=0, minute=0, second=0, microsecond=0),
               "week": now - timedelta(days=7),
               "month": now - timedelta(days=30)}
    period_stats: dict[str, dict] = {k: {"cost": 0.0, "sessions": 0} for k in cutoffs}
    for s in all_sessions:
        if not s.get("raw_ts"):
            continue
        try:
            ts = datetime.fromisoformat(s["raw_ts"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        for period, cutoff in cutoffs.items():
            if ts >= cutoff:
                period_stats[period]["cost"] += s["cost"]
                period_stats[period]["sessions"] += 1

    return {
        "global": g_usage,
        "total_cost": _compute_cost(g_usage),
        "sessions": g_sessions,
        "tools": dict(sorted(g_tools.items(), key=lambda x: -x[1])[:10]),
        "projects": all_projects,
        "period_stats": period_stats,
    }


def format_status_line(xy: str, fname: str) -> str:
    x, y = xy[0], xy[1]
    key = x if x != " " else y
    color = STATUS_COLORS.get(key, "white")
    label = STATUS_LABELS.get(key, "unknown ")
    sx = x if x != " " else "-"
    sy = y if y != " " else "-"
    return f"[{color}]{sx}{sy} {label}[/{color}]  {escape(fname)}"


# ── markdown renderer ─────────────────────────────────────────────────────────

def render_md(text: str) -> tuple[str, list[tuple[int, str]]]:
    """Returns (rich_markup_string, [(line_index, heading_text), ...])"""
    lines_out: list[str] = []
    headings: list[tuple[int, str]] = []

    for line in text.splitlines():
        m = re.match(r'^(#{1,3})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            title = escape(m.group(2))
            headings.append((len(lines_out), m.group(2)))
            if level == 1:
                lines_out.append(f"[bold cyan]{'━' * 40}[/]")
                lines_out.append(f"[bold cyan]  {title}[/]")
                lines_out.append(f"[bold cyan]{'━' * 40}[/]")
            elif level == 2:
                lines_out.append(f"[bold yellow]  ▸ {title}[/]")
            else:
                lines_out.append(f"[yellow]    • {title}[/]")
        elif line.startswith("- ") or line.startswith("* "):
            lines_out.append(f"[dim]  ·[/] {escape(line[2:])}")
        elif re.match(r'^\[(.)\]', line):
            m2 = re.match(r'^\[(.)\]\s*(.*)', line)
            if m2:
                mark = m2.group(1)
                rest = escape(m2.group(2))
                c = {"x": "green", "~": "cyan", "R": "yellow", "-": "dim", " ": "white"}.get(mark, "white")
                lines_out.append(f"  [{c}][{mark}] {rest}[/]")
        elif line.startswith("|"):
            lines_out.append(f"[dim]{escape(line)}[/]")
        elif line.startswith("```"):
            lines_out.append(f"[dim]{escape(line)}[/]")
        elif line.startswith(">"):
            lines_out.append(f"[dim italic]{escape(line)}[/]")
        elif line == "---":
            lines_out.append("[dim]─────────────────────────────────────[/]")
        else:
            lines_out.append(escape(line))

    return "\n".join(lines_out), headings


# ── widgets ───────────────────────────────────────────────────────────────────

class SectionHeader(ListItem):
    def __init__(self, text: str):
        super().__init__(disabled=True)
        self._text = text

    def compose(self) -> ComposeResult:
        yield Label(self._text, markup=True)


class ProjectItem(ListItem):
    def __init__(self, name: str, branch: str, changes: int, featured: bool):
        super().__init__()
        self.project_name = name
        self.branch = branch
        self.changes = changes
        self.featured = featured

    def compose(self) -> ComposeResult:
        yield Label(self._make_label(), markup=True)

    def _make_label(self) -> str:
        star = "[gold1]★[/gold1]" if self.featured else " "
        change_str = f"[red]{self.changes}![/red]" if self.changes > 0 else "[green]✓[/green]"
        bc = "cyan" if self.branch == "dev" else "yellow" if self.branch == "main" else "white"
        return f" {star} {self.project_name:<22} [{bc}]{self.branch:<6}[/{bc}] {change_str}"

    def refresh_label(self):
        self.query_one(Label).update(self._make_label())


class StatusTab(Static):
    def update_info(self, name: str, info: dict):
        bc = "cyan" if info["branch"] == "dev" else "yellow"
        lines = [f"[bold]{escape(name)}[/bold]  [{bc}]{info['branch']}[/{bc}]", ""]
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
    def update_info(self, info: dict):
        lines = ["[bold]Recent Commits:[/bold]", ""]
        if info["log_pretty"]:
            for entry in info["log_pretty"].splitlines():
                parts = entry.split("|", 3)
                if len(parts) == 4:
                    sha, author, when, msg = parts
                    lines.append(f"  [dim]{escape(sha)}[/dim] [cyan]{escape(msg)}[/cyan]")
                    lines.append(f"         [dim]{escape(author)} · {escape(when)}[/dim]")
                    lines.append("")
        else:
            lines.append("  [dim](no commits)[/dim]")
        self.update("\n".join(lines))


class GraphTab(Static):
    def update_info(self, info: dict):
        lines = ["[bold]Branch Graph:[/bold]", ""]
        for l in (info["graph_log"].splitlines() if info["graph_log"] else []):
            # escape first, then highlight commit markers
            safe = escape(l).replace("*", "[cyan]*[/cyan]")
            lines.append(f"  {safe}")
        if not info["graph_log"]:
            lines.append("  [dim](no history)[/dim]")
        self.update("\n".join(lines))


class DocTab(Static):
    def __init__(self, doc_id: str, **kwargs):
        super().__init__(**kwargs)
        self._doc_id = doc_id
        self._headings: list[tuple[int, str]] = []
        self._heading_idx = 0

    def load(self, project_path: Path):
        md_file = project_path / f"{self._doc_id}.md"
        if not md_file.exists():
            self.update(f"[dim]No {self._doc_id}.md in this project.[/dim]")
            self._headings = []
            return
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception as e:
            self.update(f"[red]Error reading file: {escape(str(e))}[/red]")
            return
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
        line_no, _ = self._headings[self._heading_idx]
        try:
            if hasattr(self.parent, "scroll_to"):
                self.parent.scroll_to(y=line_no, animate=False)
        except Exception:
            pass



class UsageSummary(Static):
    def show_loading(self):
        self.update("[dim]Loading…[/dim]")

    def load_data(self, data: dict, stats: dict | None = None):
        if "error" in data:
            self.update("")
            return
        ps = data.get("period_stats", {})
        total_cost = data.get("total_cost", 0)
        total_sessions = data.get("sessions", 0)
        num_projects = len(data.get("projects", []))
        lines = [
            "[bold dim]USAGE[/bold dim]",
            f"  [dim]Today[/dim]   [magenta]{'${:.2f}'.format(ps.get('today', {}).get('cost', 0)):>7}[/magenta] [dim]{ps.get('today', {}).get('sessions', 0):>3}s[/dim]",
            f"  [dim]Week[/dim]    [magenta]{'${:.2f}'.format(ps.get('week', {}).get('cost', 0)):>7}[/magenta] [dim]{ps.get('week', {}).get('sessions', 0):>3}s[/dim]",
            f"  [dim]Month[/dim]   [magenta]{'${:.2f}'.format(ps.get('month', {}).get('cost', 0)):>7}[/magenta] [dim]{ps.get('month', {}).get('sessions', 0):>3}s[/dim]",
            f"  [dim]Total[/dim]   [bold magenta]{'${:.2f}'.format(total_cost):>7}[/bold magenta] [dim]{total_sessions:>3}s[/dim]",
            f"  [dim]Projects[/dim] [cyan]{num_projects:>4}[/cyan]",
        ]
        if stats:
            total_msgs = stats.get("totalMessages", 0)
            lines.append(f"  [dim]Messages[/dim] [cyan]{total_msgs:>4}[/cyan]")
            # Model breakdown
            for model, mu in stats.get("modelUsage", {}).items():
                short = model.replace("claude-", "")
                out_tok = mu.get("outputTokens", 0)
                lines.append(f"  [dim]{short}[/dim] [green]{_fmt_tok(out_tok):>6}[/green] [dim]out[/dim]")
        self.update("\n".join(lines))


class TokenGlobal(Static):
    def show_loading(self):
        self.update("[dim]Loading…[/dim]")

    def _usage_lines(self, usage: dict, total_cost: float) -> list[str]:
        return [
            f"  [yellow]Input        {_fmt_tok(usage['input']):>8}[/yellow]  [dim]${usage['input']/1e6*TOKEN_PRICE['input']:.4f}[/dim]",
            f"  [green]Output       {_fmt_tok(usage['output']):>8}[/green]  [dim]${usage['output']/1e6*TOKEN_PRICE['output']:.4f}[/dim]",
            f"  [blue]Cache write  {_fmt_tok(usage['cache_create']):>8}[/blue]  [dim]${usage['cache_create']/1e6*TOKEN_PRICE['cache_create']:.4f}[/dim]",
            f"  [cyan]Cache read   {_fmt_tok(usage['cache_read']):>8}[/cyan]  [dim]${usage['cache_read']/1e6*TOKEN_PRICE['cache_read']:.4f}[/dim]",
            f"  [bold magenta]Total cost   {'${:.4f}'.format(total_cost):>8}[/bold magenta]",
        ]

    def _fmt_agents(self, agents: dict) -> str:
        if not agents:
            return ""
        parts = [f"{escape(a)}×{c}" for a, c in sorted(agents.items(), key=lambda x: -x[1])]
        return "  [dim]agents:[/dim] [cyan]" + "  ".join(parts) + "[/cyan]"

    def _tools_lines(self, tools: dict) -> list[str]:
        if not tools:
            return []
        max_c = max(tools.values())
        lines = ["", "[bold]Top Tools[/bold]"]
        for tool, count in tools.items():
            bar = "█" * int(count / max_c * 16)
            lines.append(f"  [cyan]{escape(tool):<26}[/cyan] [dim]{count:>4}  {bar}[/dim]")
        return lines

    def load_global(self, data: dict, stats: dict | None = None):
        if "error" in data:
            self.update(f"[red]{escape(data['error'])}[/red]")
            return
        g = data["global"]
        total_msgs = stats.get("totalMessages", 0) if stats else 0
        lines = [
            f"[bold cyan]Global Summary[/bold cyan]  [dim]{data['sessions']} sessions · {len(data['projects'])} projects · {total_msgs} messages[/dim]",
            "[dim]Select a project on the left to see its detail.[/dim]",
            "",
        ]
        lines += self._usage_lines(g, data["total_cost"])

        # Model breakdown from stats-cache
        if stats and stats.get("modelUsage"):
            lines += ["", "[bold]Model Usage[/bold]"]
            for model, mu in stats["modelUsage"].items():
                short = model.replace("claude-", "")
                inp = _fmt_tok(mu.get("inputTokens", 0))
                out = _fmt_tok(mu.get("outputTokens", 0))
                cr = _fmt_tok(mu.get("cacheReadInputTokens", 0))
                cw = _fmt_tok(mu.get("cacheCreationInputTokens", 0))
                lines.append(f"  [cyan]{short:<18}[/cyan] [yellow]in:{inp:>7}[/yellow] [green]out:{out:>7}[/green] [blue]cw:{cw:>7}[/blue] [dim]cr:{cr:>7}[/dim]")

        # Active hours from stats-cache
        if stats and stats.get("hourCounts"):
            hc = stats["hourCounts"]
            max_h = max(hc.values()) if hc else 1
            lines += ["", "[bold]Active Hours[/bold]"]
            for h in range(24):
                c = hc.get(str(h), 0)
                if c == 0:
                    continue
                bar = "█" * int(c / max_h * 12)
                lines.append(f"  [dim]{h:02d}:00[/dim]  [cyan]{bar:<12}[/cyan] [dim]{c}[/dim]")

        lines += self._tools_lines(data["tools"])

        if data["projects"]:
            lines += ["", "[bold]All Projects  (by cost)[/bold]",
                      f"[dim]  {'Project':<26} {'Input':>7} {'Output':>7} {'Cost':>9} {'Sessions':>5}[/dim]",
                      f"[dim]  {'─'*26} {'─'*7} {'─'*7} {'─'*9} {'─'*5}[/dim]"]
            for p in data["projects"]:
                u = p["usage"]
                lines.append(
                    f"  [cyan]{escape(p['name']):<26}[/cyan]"
                    f" [yellow]{_fmt_tok(u['input']):>7}[/yellow]"
                    f" [green]{_fmt_tok(u['output']):>7}[/green]"
                    f" [magenta]{'${:.4f}'.format(p['cost']):>9}[/magenta]"
                    f" [dim]{p['sessions']:>5}[/dim]"
                )
        self.update("\n".join(lines))

    def load_project(self, detail: dict | None, project_name: str, session_metas: list | None = None):
        if detail is None:
            self.update(f"[dim]No Claude session data found for[/dim] [cyan]{escape(project_name)}[/cyan]")
            return
        # Session meta stats
        meta_info = ""
        if session_metas:
            total_mins = sum(m.get("duration_minutes", 0) for m in session_metas)
            total_msgs = sum(m.get("user_message_count", 0) + m.get("assistant_message_count", 0) for m in session_metas)
            total_commits = sum(m.get("git_commits", 0) for m in session_metas)
            meta_info = f" · {total_mins}min · {total_msgs} msgs · {total_commits} commits"
        lines = [
            f"[bold cyan]{escape(detail['name'])}[/bold cyan]  [dim]{len(detail['sessions'])} sessions{meta_info}[/dim]",
            "",
        ]
        lines += self._usage_lines(detail["usage"], detail["cost"])

        # Averages
        n_sessions = len(detail["sessions"])
        if n_sessions:
            avg_session = detail["cost"] / n_sessions
            daily_14d = detail.get("daily_14d", [])
            active_days = sum(1 for d in daily_14d if d["cost"] > 0)
            avg_day = detail["cost"] / active_days if active_days else 0
            lines += [
                "",
                "[bold]Averages[/bold]",
                f"  [dim]Per session[/dim]   [magenta]${avg_session:.4f}[/magenta]",
                f"  [dim]Per day[/dim]       [magenta]${avg_day:.4f}[/magenta]  [dim]({active_days} active days in 14d)[/dim]",
            ]

        # Daily trend (14 days)
        daily_14d = detail.get("daily_14d", [])
        if daily_14d and any(d["cost"] > 0 for d in daily_14d):
            max_cost = max(d["cost"] for d in daily_14d) or 1
            lines += ["", "[bold]Daily Trend  (14d)[/bold]"]
            for d in daily_14d:
                bar_len = int(d["cost"] / max_cost * 20) if max_cost else 0
                bar = "█" * bar_len
                cost_str = f"${d['cost']:.2f}" if d["cost"] > 0 else ""
                lines.append(f"  [dim]{d['date']}[/dim]  [cyan]{bar:<20}[/cyan]  [magenta]{cost_str}[/magenta]")

        # Agent types
        all_agents = detail.get("all_agents", {})
        if all_agents:
            max_a = max(all_agents.values())
            lines += ["", "[bold]Agent Types[/bold]"]
            for agent, count in all_agents.items():
                bar = "█" * int(count / max_a * 16)
                lines.append(f"  [cyan]{escape(agent):<26}[/cyan] [dim]{count:>4}  {bar}[/dim]")

        # Rank
        rank = detail.get("rank")
        if rank:
            lines += ["", "[bold]Rank[/bold]",
                       f"  [cyan]#{rank['pos']}[/cyan] of {rank['total']} projects  [dim]({rank['pct']:.1f}% of total spend)[/dim]"]

        lines += self._tools_lines(detail["tools"])

        if detail.get("commits_cost"):
            lines += ["", "[bold]Cost by Commit[/bold]",
                      f"[dim]  {'Commit':<38} {'Sessions':>8} {'Input':>7} {'Output':>7} {'Cost':>9}[/dim]",
                      f"[dim]  {'─'*38} {'─'*8} {'─'*7} {'─'*7} {'─'*9}[/dim]"]
            for c in detail["commits_cost"]:
                sha_label = f"[dim]{c['sha']}[/dim] " if c["sha"] != "—" else "  "
                msg = escape(c["msg"])
                # Truncate long messages
                if len(c["msg"]) > 32:
                    msg = escape(c["msg"][:31]) + "[dim]…[/dim]"
                lines.append(
                    f"  {sha_label}[cyan]{msg:<33}[/cyan]"
                    f" [dim]{c['sessions']:>5}[/dim]"
                    f" [yellow]{_fmt_tok(c['input']):>7}[/yellow]"
                    f" [green]{_fmt_tok(c['output']):>7}[/green]"
                    f" [magenta]{'${:.4f}'.format(c['cost']):>9}[/magenta]"
                )
                agent_str = self._fmt_agents(c.get("agents", {}))
                if agent_str:
                    lines.append(agent_str)

        if detail["sessions"]:
            lines += ["", "[bold]Sessions  (recent first)[/bold]",
                      f"[dim]  {'Date':<17} {'In':>6} {'Out':>6} {'Cost':>9}[/dim]",
                      f"[dim]  {'─'*17} {'─'*6} {'─'*6} {'─'*9}[/dim]"]
            for s in detail["sessions"][:15]:
                u = s["usage"]
                lines.append(
                    f"  [dim]{s['date']:<17}[/dim]"
                    f" [yellow]{_fmt_tok(u['input']):>6}[/yellow]"
                    f" [green]{_fmt_tok(u['output']):>6}[/green]"
                    f" [magenta]{'${:.4f}'.format(s['cost']):>9}[/magenta]"
                )
                agent_str = self._fmt_agents(s.get("agents", {}))
                if agent_str:
                    lines.append(agent_str)
        self.update("\n".join(lines))


# ── app ───────────────────────────────────────────────────────────────────────

class GitDashboard(App):
    CSS = """
    Screen { background: #080c18; }
    Header { background: #0f1428; color: #00d4ff; }
    Footer { background: #0f1428; }
    Footer > .footer--key { background: #1e2540; color: #00d4ff; }
    Footer > .footer--description { color: #778; }
    Footer > .footer--highlight { background: #2a3560; color: #fff; }

    #left-panel { width: 38; border: solid #1e2540; background: #0b0f1e; }
    #section-title { background: #0f1428; color: #00d4ff; padding: 0 1; text-style: bold; }

    ListView { background: #0b0f1e; }
    ListItem { background: #0b0f1e; color: #c0c8e0; padding: 0; }
    ListItem:hover { background: #141a30; }
    ListItem.--highlight { background: #1a2245; color: #00d4ff; text-style: bold; }
    ListItem.selected { background: #1a2245; color: #00d4ff; text-style: bold; }
    ListItem.-disabled { background: #0b0f1e; padding: 0; }
    SectionHeader { background: #0f1428; padding: 0; border-top: solid #1e2540; }
    SectionHeader Label { padding: 0 1; color: #445; }

    #right-panel { border: solid #1e2540; background: #0b0f1e; }
    TabbedContent { background: #0b0f1e; }
    TabPane { padding: 1 2; background: #0b0f1e; color: #c0c8e0; }
    StatusTab, LogTab, GraphTab, DocTab, TokenGlobal { color: #c0c8e0; }
    #usage-summary { background: #0b0f1e; color: #c0c8e0; padding: 1 1 0 1; border-top: solid #1e2540; height: auto; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("f", "toggle_featured", "★ Featured", show=True),
        Binding("r", "refresh_all", "Refresh", show=True),
        Binding("n", "section_next", "Next section", show=True),
        Binding("p", "section_prev", "Prev section", show=True),
    ]

    _TAB_MAP = {
        "1": "tab-status", "2": "tab-log", "3": "tab-graph",
        "4": "tab-prd", "5": "tab-todo", "6": "tab-decision", "7": "tab-tokens",
    }
    _DOC_MAP = {
        "tab-prd": "#prd-view", "tab-todo": "#todo-view", "tab-decision": "#decision-view"
    }

    def __init__(self):
        super().__init__()
        self.featured = load_featured()
        self.projects: list[Path] = []
        self.project_infos: dict = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="left-panel"):
                yield Label(" Projects", id="section-title")
                yield ListView(id="project-list")
                yield UsageSummary(id="usage-summary", markup=True)
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
                    with TabPane("Tokens [7]", id="tab-tokens"):
                        with ScrollableContainer(id="scroll-tokens-global"):
                            yield TokenGlobal(id="tokens-global", markup=True)
        yield Footer()

    def on_mount(self):
        self.title = "Git Dashboard"
        self.sub_title = str(PROJECTS_DIR)
        self.load_projects()
        self._load_usage_summary_worker()

    def load_projects(self):
        self.projects = get_projects()
        lv = self.query_one("#project-list", ListView)
        lv.clear()
        self.project_infos = {}

        featured_p = [p for p in self.projects if p.name in self.featured]
        other_p = [p for p in self.projects if p.name not in self.featured]

        if featured_p:
            lv.append(SectionHeader(" ★  FEATURED"))
            for p in featured_p:
                lv.append(ProjectItem(p.name, "…", 0, True))
        if other_p:
            lv.append(SectionHeader(" ─  PROJECTS"))
            for p in other_p:
                lv.append(ProjectItem(p.name, "…", 0, False))

        for i, item in enumerate(lv._nodes):
            if hasattr(item, "project_name"):
                lv.index = i
                break

        self._load_git_info_worker(featured_p + other_p)

    @work(thread=True)
    def _load_git_info_worker(self, projects: list[Path]):
        for p in projects:
            info = get_project_info(p)
            self.call_from_thread(self._update_project_item, p.name, info)

    def _update_project_item(self, name: str, info: dict):
        self.project_infos[name] = info
        lv = self.query_one("#project-list", ListView)
        for item in lv._nodes:
            if hasattr(item, "project_name") and item.project_name == name:
                item.branch = info["branch"]
                item.changes = info["changes"]
                item.refresh_label()
                break
        highlighted = lv.highlighted_child
        if highlighted and getattr(highlighted, "project_name", None) == name:
            self._show_detail(name)

    def _show_detail(self, name: str):
        info = self.project_infos.get(name)
        if not info:
            return
        path = PROJECTS_DIR / name
        self.query_one("#status-view", StatusTab).update_info(name, info)
        self.query_one("#log-view", LogTab).update_info(info)
        self.query_one("#graph-view", GraphTab).update_info(info)
        self.query_one("#prd-view", DocTab).load(path)
        self.query_one("#todo-view", DocTab).load(path)
        self.query_one("#decision-view", DocTab).load(path)

    @on(ListView.Highlighted)
    def on_list_highlighted(self, event: ListView.Highlighted):
        if event.item and hasattr(event.item, "project_name"):
            for item in self.query("#project-list ProjectItem"):
                item.remove_class("selected")
            event.item.add_class("selected")
            name = event.item.project_name
            self._show_detail(name)
            active = self.query_one("#tabs", TabbedContent).active
            if active == "tab-tokens":
                self._load_project_tokens_worker(name)

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated):
        if event.tab and event.tab.id == "tab-tokens":
            self._load_tokens_worker()

    def on_key(self, event):
        if event.key in self._TAB_MAP:
            self.query_one("#tabs", TabbedContent).active = self._TAB_MAP[event.key]
        elif event.key == "n":
            self._doc_action("jump_next")
        elif event.key == "p":
            self._doc_action("jump_prev")

    def _doc_action(self, method: str):
        active = self.query_one("#tabs", TabbedContent).active
        if active in self._DOC_MAP:
            getattr(self.query_one(self._DOC_MAP[active], DocTab), method)()

    def action_toggle_featured(self):
        lv = self.query_one("#project-list", ListView)
        name = getattr(lv.highlighted_child, "project_name", None)
        if name:
            self.featured.discard(name) if name in self.featured else self.featured.add(name)
            save_featured(self.featured)
            self.load_projects()

    def action_refresh_all(self):
        self.load_projects()
        self._load_usage_summary_worker()
        self.notify("Refreshed")

    @work(thread=True)
    def _load_usage_summary_worker(self):
        self.call_from_thread(self.query_one("#usage-summary", UsageSummary).show_loading)
        data = parse_token_data()
        stats = parse_stats_cache()
        self.call_from_thread(self.query_one("#usage-summary", UsageSummary).load_data, data, stats)

    @work(thread=True)
    def _load_tokens_worker(self):
        self.call_from_thread(self.query_one("#tokens-global", TokenGlobal).show_loading)
        lv = self.query_one("#project-list", ListView)
        selected = getattr(lv.highlighted_child, "project_name", None)
        if selected:
            global_data = parse_token_data()
            detail = parse_project_detail(selected, global_data)
            project_path = str(PROJECTS_DIR / selected)
            metas = parse_session_metas(project_path)
            self.call_from_thread(self.query_one("#tokens-global", TokenGlobal).load_project, detail, selected, metas)
        else:
            data = parse_token_data()
            stats = parse_stats_cache()
            self.call_from_thread(self.query_one("#tokens-global", TokenGlobal).load_global, data, stats)

    @work(thread=True)
    def _load_project_tokens_worker(self, project_name: str):
        self.call_from_thread(self.query_one("#tokens-global", TokenGlobal).show_loading)
        global_data = parse_token_data()
        detail = parse_project_detail(project_name, global_data)
        project_path = str(PROJECTS_DIR / project_name)
        metas = parse_session_metas(project_path)
        self.call_from_thread(self.query_one("#tokens-global", TokenGlobal).load_project, detail, project_name, metas)

    def action_section_next(self):
        self._doc_action("jump_next")

    def action_section_prev(self):
        self._doc_action("jump_prev")


if __name__ == "__main__":
    GitDashboard().run()
