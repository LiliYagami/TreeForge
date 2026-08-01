# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

TreeForge is a Windows desktop GUI app (CustomTkinter) that bridges chat-based AI coding (ChatGPT/Claude/Gemini web UIs) and the local filesystem. It has three core workflows: **Générer** (parse a text tree pasted from an AI chat → create real folders/files), **Recaper** (compile an entire real project into one `.txt` for pasting into an AI chat), and **Restaurer/ReversRecaper** (parse that `.txt` back and reconstruct the project). The UI and all in-app content (prompts, labels, tips) are in French.

## Commands

```powershell
# Activate the venv (created per project — see conversation history, not committed)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the app
python Main.py

# Run unit tests (unittest, not pytest)
.\.venv\Scripts\python -m unittest tests/test_audit_fixes.py
.\.venv\Scripts\python -m unittest discover tests

# Run a single test case
.\.venv\Scripts\python -m unittest tests.test_audit_fixes.TestAuditFixes.test_improvement_1_boilerplates_io

# Benchmarks (not part of the unittest suite, run standalone, print/CSV output)
.\.venv\Scripts\python -X utf8 tests/benchmark_generator.py
$env:PYTHONPATH="src"; .\.venv\Scripts\python -X utf8 tests/benchmark_recaper.py

# Recaper CLI standalone (no GUI)
python -m treeforge.core.recaper [dossier] [--output dossier_sortie]
```

There is no lint/format config (no ruff/black/flake8 config file) and no PyInstaller `.spec` file yet, despite `pyinstaller`/`pyinstaller-hooks-contrib` being in `requirements.txt` — packaging to a standalone `.exe` is intended but not yet wired up.

Python `>=3.10` required (`pyproject.toml`); developed against 3.12.

## Architecture

### `core/` — pure logic, no GUI imports (importable/testable standalone)

- **`models.py`** — `TreeNode` (recursive: `name`, `is_dir`, `children`, `content`, `excluded`) and `ParseResult` (`nodes`, `errors`, `warnings`). The shared vocabulary every other module speaks.
- **`parser.py`** — turns pasted text into `TreeNode` trees. Auto-detects one of three ASCII-tree dialects (`unicode` "├── └──", `wintree` = Windows `tree /f` output, `indent` = plain whitespace indentation) plus a `json` format, and parses under one of three leniency modes (`🔒 Strict` / `🔧 Souple` / `⚡ Confiant`) that control how parent/child mismatches are handled. Also strips AI-added annotations (✅⚠️❓ etc.) and detects/strips a leading absolute path line. `_node_from_json` here is reused directly by `template_manager.py`.
- **`generator.py`** — walks a `ParseResult` and writes real dirs/files to disk. Content mode (`Vide`/`Minimal`/`Boilerplate`) decides what gets written into new files; boilerplate content comes from `config.BOILERPLATE`. **No overwrite protection or diffing** — `write_text` is unconditional on existing files.
- **`recaper.py`** — walks a real project on disk and serializes it into one `.txt`: an ASCII tree section (its own tree-printing logic, independent of `parser.py`) followed by per-file blocks delimited by the literal marker `<<TREEFORGE_FILE_BLOCK>>`. Has its own `DEFAULT_EXCLUDE_DIRS` and `TEXT_EXTENSIONS` allowlist deciding what gets included as text.
- **`revers_recaper.py`** — the inverse of `recaper.py`. Parses the same `.txt` format back into a project: `_parse_arborescence()` reconstructs the directory structure from the tree section (its own depth/format-detection logic, **not** shared with `core/parser.py` — a third, independent tree parser), `_parse_recap()` extracts the file blocks, and `extract()` merges the two (files present in the tree but with no text block, e.g. binaries, become empty placeholder files). Path traversal is guarded via `_safe_resolve()`.
- **`template_manager.py`** — loads canned project skeletons from `resources/templates/*.json` via `parser._node_from_json`.
- **`telemetry.py`** — PostHog (analytics) + Sentry (crash reporting), both **consent-gated** and currently inert (placeholder API keys). Consent state lives in `~/.treeforge/settings.json` (user home dir) — a *different* location from the app's other preferences (see below). Sentry events are scrubbed of local file paths before sending.

### `gui/` — CustomTkinter, imports from `core/` only

- `main_window.py` builds the tab bar (`Prompt IA`, `Générer`, `Recaper`, `Restaurer`, `Templates`) plus a collapsible log console and settings button; each tab lives in `gui/tabs/`, reusable widgets in `gui/components/`.
- `SettingsDialog` (`gui/components/settings_dialog.py`) currently only exposes theme/tips/parsing-mode/content-mode/telemetry toggles — has its own separately hardcoded `APP_VERSION` constant (see below).
- Drag & drop wraps `tkinterdnd2`; the window class conditionally inherits `TkinterDnD.DnDWrapper` only if the import succeeds (`DND_WINDOW` flag), so D&D failures degrade gracefully rather than crashing.

### Preferences vs. telemetry consent — two different storage locations

- App preferences (theme, parsing mode, content mode, destination history, etc.) load/save via `utils/helpers.py::load_prefs()`/`save_prefs()` to **`src/treeforge/resources/stock/user_prefs.json`** — inside the package/repo tree, not the user's home directory.
- Telemetry consent lives separately in `~/.treeforge/settings.json` (see `core/telemetry.py`).
Don't assume these are the same file when tracing preference-related bugs.

### Known version drift

The app version string is currently duplicated and out of sync in at least four places: `pyproject.toml` (`1.0.0`), `config.py::__version__` (`1.0.0`), `main_window.py::APP_VERSION` (`3.0.0`), and `settings_dialog.py::APP_VERSION` (`1.0.0`, its own separate constant). When touching versioning, check all four rather than assuming one is authoritative.

### Entry point

`Main.py` inserts `src/` onto `sys.path` manually (the package is not installed editable) before importing `treeforge.main.main`. Don't assume `pip install -e .` has been run.

## Testing the GUI (manual verification, not automated)

There is no reliable automated UI-click testing on this machine:
- **Visual checks work**: launch the app (`Start-Process .venv\Scripts\python.exe Main.py`), then screenshot the window (Win32 `GetWindowRect` + `System.Drawing.Graphics.CopyFromScreen` via PowerShell — see conversation history for a working script). Restore the window first if minimized (`ShowWindow(hwnd, 9)`), it starts minimized when launched this way.
- **Coordinate-based click automation (`pywinauto`, installed in `requirements-dev.txt`) is unreliable when launched from a background/non-interactive process**: Windows' foreground-lock-timeout prevents `SetForegroundWindow`/`set_focus()` from actually raising the target window, so simulated clicks land wherever the mouse physically is on screen — verified to silently hit an unrelated terminal window twice, harmlessly, during testing. `pywinauto` is still useful for read-only inspection (`print_control_identifiers()`), but don't rely on it to drive clicks/typing without a human keeping the app window in the foreground.
- CustomTkinter draws its own widgets on a canvas, so the accessibility tree (`uia`/`win32` backends) only exposes generic `Pane`/`TkChild` nodes for app content — no name-based control targeting ("click the button called Générer") is possible even when focus works.
- For behavior/logic testing, prefer calling `core/` functions directly (as `tests/test_audit_fixes.py` already does) over driving the GUI.
