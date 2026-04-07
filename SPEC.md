# SPEC.md

> 專案架構 + 功能規格 + 任務定義。進度在 checkbox，驗收條件全 [x] = 功能完成。
> 完成的功能搬到 SPEC-archive.md。

## Architecture

Everything lives in `dashboard.py` (single-file app). Sections in order:

1. **Config** — `load_config()` resolves `PROJECTS_DIR` via env → `~/.git-dashboard.json` → cwd
2. **Git helpers** — `run_git()` wraps subprocess; `get_project_info()` collects status/log/diff
3. **Token helpers** — parse `~/.claude/projects/**/*.jsonl` to compute Claude API usage and costs; `_correlate_commits()` maps sessions to subsequent git commits
4. **Markdown renderer** — `render_md()` converts SPEC/DECISION markdown to Rich markup with heading index for `n`/`p` navigation
5. **Widgets** — `ProjectItem`, `StatusTab`, `LogTab`, `GraphTab`, `DocTab`, `TokenGlobal`, `UsageSummary` (all Textual widgets)
6. **App** — `GitDashboard(App)` wires everything; workers (`@work(thread=True)`) load git info and token data off the main thread

**Key constraints:**
- Read-only: no git write operations
- No extra git libraries: subprocess only
- Token pricing: hardcoded in `TOKEN_PRICE` dict; update when switching models
- Featured projects: persisted at `~/.git-dashboard-featured.json`
- Tab switching: keys `1`–`9` via `_TAB_MAP`; doc tabs (`4`/`5`/`6`/`7`/`8`) support `n`/`p` section jump via `_DOC_MAP`
- CSS is inline: all styling in `GitDashboard.CSS` class attribute
- Threading: git info and token data load via `@work(thread=True)` workers; UI updates use `call_from_thread()`

---

## F001 Usage Summary 邊欄 ✅

### 規格
在左側 sidebar 底部顯示固定的 global usage summary widget，啟動時即載入，不隨專案切換而改變。使用者啟動 dashboard 後立刻看到 Today / Week / Month / Total 四個時間區間的花費與 session 數，以及有紀錄的專案總數。

### 驗收條件
- [x] 啟動後 sidebar 底部出現 usage summary
- [x] 顯示 Today / Week / Month / Total 四行，各帶花費 + session 數
- [x] 顯示 Projects 數量
- [x] 按 `r` 後 summary 跟著刷新
- [x] 切換專案時 summary 不變

### 範圍限制
- 不改變現有 `TokenGlobal` 的邏輯

### 任務
- [x] F001-T01: `parse_token_data()` 新增日期分組欄位（today/7d/30d 的 cost + sessions）
- [x] F001-T02: 新增 `UsageSummary(Static)` widget，渲染 Today/Week/Month/Total 四行
- [x] F001-T03: `compose()` 中 `#left-panel` 加入 UsageSummary（ListView 下方）
- [x] F001-T04: `on_mount` 觸發 token 載入 worker，完成後更新 UsageSummary
- [x] F001-T05: `action_refresh_all` 同步刷新 UsageSummary
- [x] F001-T06: CSS：UsageSummary 樣式與 sidebar 一致

---

## F002 Tokens Tab 專案統計擴充 ✅

### 規格
在 Tokens tab 的 per-project view 加入更多統計維度：session 平均成本、每日成本趨勢（14 天 ASCII bar chart）、agent 類型使用分布、專案在全局的成本排名與佔比。

### 驗收條件
- [x] Per-project view 顯示 session 平均與日均成本
- [x] 顯示 14 天每日成本 ASCII bar chart
- [x] 顯示 agent 類型統計（全 sessions 加總）
- [x] 顯示專案排名（第 N / 共 M，佔 X%）

### 範圍限制
- 不改變 `load_global()` 的行為

### 任務
- [x] F002-T01: `parse_project_detail()` 新增日聚合（14d）、agent 總計、排名資訊
- [x] F002-T02: `TokenGlobal.load_project()` 渲染 session 平均 + 日均成本
- [x] F002-T03: `TokenGlobal.load_project()` 渲染 14 天每日成本 ASCII bar chart
- [x] F002-T04: `TokenGlobal.load_project()` 渲染 agent 類型分布
- [x] F002-T05: `TokenGlobal.load_project()` 渲染專案排名 + 佔比

---

## F003 Graphify Report Tab

### 規格
在 SPEC [5] 後面新增 KnowledgeGraph [6] tab，用 DocTab 渲染選中專案的 `graphify-out/GRAPH_REPORT.md`。支援 `n`/`p` section 跳轉。專案沒有 `graphify-out/GRAPH_REPORT.md` 時顯示灰色提示文字。插入後 Archive→7, DECISION→8, Tokens→9，快捷鍵對應更新。

### 驗收條件
- [x] Tab 出現在 SPEC [5] 之後，標題 `KGraph [6]`
- [x] 選中專案有 `graphify-out/GRAPH_REPORT.md` 時正確渲染內容
- [x] `n`/`p` section 跳轉正常運作
- [x] 沒有 report 時顯示 `No graph — run /graphify in project to generate`
- [x] 按 `6` 切到此 tab，後續 tab 快捷鍵 7/8/9 正確對應
- [x] 切換專案時內容跟著更新

### 範圍限制
- 不改變 DocTab 本身邏輯，只新增一個 instance
- 不解析 graph.json，只渲染 GRAPH_REPORT.md

### 任務
- [x] F003-T01: compose() 新增 KGraph TabPane + DocTab instance（SPEC 後面）
- [x] F003-T02: _TAB_MAP / _DOC_MAP 更新，後續 tab 快捷鍵 +1
- [x] F003-T03: DocTab.load() 支援 graphify-out/GRAPH_REPORT.md 路徑解析
- [x] F003-T04: 無 report 時顯示灰色提示
- [x] F003-T05: 驗證 n/p 跳轉 + 專案切換更新

---

<!-- Backlog (未規格化，需人類提出後走新功能 SOP)
- Filter project list by featured only (toggle)
- Show ahead/behind count vs remote (e.g. ↑2 ↓1)
- Stash count indicator per project
- `o` key to open project in new terminal tab
-->
