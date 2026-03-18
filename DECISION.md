# DECISION — git-dashboard

## 2026-03-18 — Use Footer widget instead of custom Static keys bar

**Decision:** Replaced custom `Static` keys bar with Textual's built-in `Footer` widget.

**Why:** Custom Static broke the command palette — Textual's palette button is part of Footer. Footer also handles key display automatically via `BINDINGS` with `show=True`.

**Trade-off:** Less visual control over the keys bar layout, but gains palette functionality and stays compatible with Textual internals.

---

## 2026-03-18 — n/p for section jump instead of ]/[

**Decision:** Changed section navigation keys from `]`/`[` to `n`/`p`.

**Why:** `[` is a Rich markup delimiter — using it as a keybinding caused `MarkupError` in the Footer display. `n`/`p` (next/prev) is also more intuitive.

---

## 2026-03-18 — Read-only, no Git write operations

**Decision:** Dashboard is strictly read-only. No commit, push, or branch operations.

**Why:** Scope is project overview and planning doc access. Write operations belong in the terminal or lazygit. Keeping it read-only removes risk of accidental state changes.

---

## 2026-03-18 — Subprocess git CLI instead of GitPython

**Decision:** Use `subprocess` to call the `git` CLI directly instead of the `GitPython` library.

**Why:** No additional dependency, works with any git version, and the output formats we need (`--porcelain`, `--pretty=format`, `--graph`) are straightforward to parse. GitPython adds complexity without meaningful benefit for this use case.
