# Graph Report - .  (2026-04-07)

## Corpus Check
- Corpus is ~4,971 words - fits in a single context window. You may not need a graph.

## Summary
- 103 nodes · 173 edges · 14 communities detected
- Extraction: 58% EXTRACTED · 42% INFERRED · 0% AMBIGUOUS · INFERRED: 73 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `GitDashboard` - 15 edges
2. `TokenGlobal` - 9 edges
3. `parse_project_detail()` - 8 edges
4. `DocTab` - 8 edges
5. `parse_token_data()` - 7 edges
6. `ProjectItem` - 7 edges
7. `App (GitDashboard)` - 7 edges
8. `_load_tokens_worker()` - 6 edges
9. `_fmt_tok()` - 5 edges
10. `_parse_jsonl_dir()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `CLAUDE.md Project Instructions` --references--> `dashboard.py (Single-File App)`  [EXTRACTED]
  CLAUDE.md → dashboard.py
- `README.md Documentation` --references--> `dashboard.py (Single-File App)`  [EXTRACTED]
  README.md → dashboard.py
- `SPEC.md Specification` --references--> `dashboard.py (Single-File App)`  [EXTRACTED]
  SPEC.md → dashboard.py
- `Read-Only Constraint` --rationale_for--> `dashboard.py (Single-File App)`  [EXTRACTED]
  DECISION.md → dashboard.py
- `Single-File App Decision` --rationale_for--> `dashboard.py (Single-File App)`  [EXTRACTED]
  DECISION.md → dashboard.py

## Hyperedges (group relationships)
- **Core Decisions Shape Architecture** — decision_read_only, decision_subprocess_git, decision_single_file, decision_inline_css, decision_threading_model [EXTRACTED 1.00]
- **Token Usage Feature Group** — spec_token_helpers, widget_token_global, widget_usage_summary, spec_f001, spec_f002 [EXTRACTED 0.90]
- **Dashboard Architecture Layers** — spec_config, spec_git_helpers, spec_token_helpers, spec_markdown_renderer, spec_widgets, spec_app [EXTRACTED 1.00]

## Communities

### Community 0 - "Architecture Decisions"
Cohesion: 0.15
Nodes (15): ~/.git-dashboard.json Config, Footer Widget Decision, Inline CSS Decision, Subprocess Git CLI (No GitPython), Threading Model (@work + call_from_thread), Single TokenGlobal Widget Decision, App (GitDashboard), Config (load_config) (+7 more)

### Community 1 - "App Actions & Navigation"
Cohesion: 0.26
Nodes (3): App, GitDashboard, _load_usage_summary_worker()

### Community 2 - "Git & Config Helpers"
Cohesion: 0.24
Nodes (9): _correlate_commits(), format_status_line(), get_project_info(), get_projects(), load_featured(), _load_git_info_worker(), Map each session to the next git commit after it, group by commit., run_git() (+1 more)

### Community 3 - "Tab Widgets (Graph/Log/Status)"
Cohesion: 0.24
Nodes (5): GraphTab, LogTab, StatusTab, UsageSummary, Static

### Community 4 - "ProjectItem Widget"
Cohesion: 0.27
Nodes (3): ProjectItem, SectionHeader, ListItem

### Community 5 - "Token Parsing & Cost"
Cohesion: 0.39
Nodes (8): _compute_cost(), _decode_project_name(), find_project_claude_dir(), _parse_jsonl_dir(), parse_project_detail(), parse_token_data(), Match a project folder name to its ~/.claude/projects/ directory., Returns (usage_totals, tool_counts, sessions_list).

### Community 6 - "DocTab Markdown Viewer"
Cohesion: 0.32
Nodes (3): DocTab, Returns (rich_markup_string, [(line_index, heading_text), ...]), render_md()

### Community 7 - "TokenGlobal Widget"
Cohesion: 0.5
Nodes (2): _fmt_tok(), TokenGlobal

### Community 8 - "Project Documentation"
Cohesion: 0.4
Nodes (6): CLAUDE.md Project Instructions, dashboard.py (Single-File App), Read-Only Constraint, Single-File App Decision, README.md Documentation, SPEC.md Specification

### Community 9 - "Tab Activation & Stats"
Cohesion: 0.5
Nodes (3): _load_tokens_worker(), parse_stats_cache(), Parse ~/.claude/stats-cache.json for global usage stats.

### Community 10 - "Token Loading Workers"
Cohesion: 0.5
Nodes (4): _load_project_tokens_worker(), on_list_highlighted(), parse_session_metas(), Parse session-meta/*.json, optionally filter by project_path.

### Community 11 - "Keybinding & Renderer"
Cohesion: 1.0
Nodes (2): n/p Keybinding Decision, Markdown Renderer (render_md)

### Community 12 - "Featured Projects Config"
Cohesion: 1.0
Nodes (2): ~/.git-dashboard-featured.json, Featured Projects Feature

### Community 13 - "Decision Log"
Cohesion: 1.0
Nodes (1): DECISION.md Technical Decisions

## Knowledge Gaps
- **21 isolated node(s):** `Parse ~/.claude/stats-cache.json for global usage stats.`, `Parse session-meta/*.json, optionally filter by project_path.`, `Match a project folder name to its ~/.claude/projects/ directory.`, `Returns (usage_totals, tool_counts, sessions_list).`, `Map each session to the next git commit after it, group by commit.` (+16 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Keybinding & Renderer`** (2 nodes): `n/p Keybinding Decision`, `Markdown Renderer (render_md)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Featured Projects Config`** (2 nodes): `~/.git-dashboard-featured.json`, `Featured Projects Feature`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Decision Log`** (1 nodes): `DECISION.md Technical Decisions`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GitDashboard` connect `App Actions & Navigation` to `Tab Activation & Stats`, `Git & Config Helpers`, `Tab Widgets (Graph/Log/Status)`, `ProjectItem Widget`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Why does `TokenGlobal` connect `TokenGlobal Widget` to `Git & Config Helpers`, `Tab Widgets (Graph/Log/Status)`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `DocTab` connect `DocTab Markdown Viewer` to `Git & Config Helpers`, `Tab Widgets (Graph/Log/Status)`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `parse_project_detail()` (e.g. with `find_project_claude_dir()` and `_parse_jsonl_dir()`) actually correct?**
  _`parse_project_detail()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `parse_token_data()` (e.g. with `_parse_jsonl_dir()` and `_decode_project_name()`) actually correct?**
  _`parse_token_data()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Parse ~/.claude/stats-cache.json for global usage stats.`, `Parse session-meta/*.json, optionally filter by project_path.`, `Match a project folder name to its ~/.claude/projects/ directory.` to the rest of the system?**
  _21 weakly-connected nodes found - possible documentation gaps or missing edges._