# tests/benchmark_recaper.py
"""
Benchmark réel du module Recaper de TreeForge.
Mesure le temps de génération d'un recap pour différents types de projets.

Usage :
    $env:PYTHONPATH = "src"
    python tests/benchmark_recaper.py

Résultats exportés dans : tests/benchmark_recaper_results.csv
"""
from __future__ import annotations

import platform
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

# ── Accès au package src ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from treeforge.core.recaper import recap


# ─────────────────────────────────────────────────────────────────────────────
# Infos machine
# ─────────────────────────────────────────────────────────────────────────────

def _print_system_info() -> None:
    try:
        import psutil
        ram = psutil.virtual_memory().total // (1024 ** 3)
    except ImportError:
        ram = "? (pip install psutil)"

    print(f"  OS      : {platform.system()} {platform.release()}")
    print(f"  CPU     : {platform.processor()}")
    print(f"  RAM     : {ram} Go")
    print(f"  Python  : {platform.python_version()}")


# ─────────────────────────────────────────────────────────────────────────────
# Générateurs de projets synthétiques sur disque
# ─────────────────────────────────────────────────────────────────────────────

# Contenu par extension : taille réaliste pour un vrai projet
_CONTENT: dict[str, str] = {
    ".py": (
        "# -*- coding: utf-8 -*-\n"
        '"""\nModule synthétique généré par le benchmark TreeForge.\n"""\n'
        "from __future__ import annotations\n\n\n"
        "class BenchClass:\n"
        "    \"\"\"Classe de remplissage.\"\"\"\n\n"
        "    def __init__(self, value: int = 0) -> None:\n"
        "        self.value = value\n\n"
        "    def compute(self) -> int:\n"
        "        \"\"\"Retourne une valeur calculée.\"\"\"\n"
        "        return self.value * 2 + 1\n\n\n"
        "def helper_function(x: int, y: int) -> int:\n"
        "    \"\"\"Fonction utilitaire de remplissage.\"\"\"\n"
        "    return x + y\n"
    ),
    ".js": (
        "// Module synthétique\n"
        "'use strict';\n\n"
        "class BenchModule {\n"
        "  constructor(value = 0) {\n"
        "    this.value = value;\n"
        "  }\n\n"
        "  compute() {\n"
        "    return this.value * 2 + 1;\n"
        "  }\n"
        "}\n\n"
        "module.exports = { BenchModule };\n"
    ),
    ".html": (
        "<!DOCTYPE html>\n"
        '<html lang="fr">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "  <title>Page bench</title>\n"
        '  <link rel="stylesheet" href="style.css">\n'
        "</head>\n"
        "<body>\n"
        '  <header><h1>Titre principal</h1></header>\n'
        '  <main><p>Contenu de benchmark.</p></main>\n'
        '  <footer><p>Footer</p></footer>\n'
        '  <script src="app.js"></script>\n'
        "</body>\n</html>\n"
    ),
    ".css": (
        "/* Feuille de styles synthétique */\n\n"
        "* { box-sizing: border-box; margin: 0; padding: 0; }\n\n"
        "body {\n  font-family: sans-serif;\n  line-height: 1.6;\n  color: #333;\n}\n\n"
        "header { background: #2c3e50; color: #fff; padding: 1rem 2rem; }\n\n"
        "main { max-width: 960px; margin: 2rem auto; padding: 0 1rem; }\n\n"
        "footer { text-align: center; padding: 1rem; color: #999; }\n"
    ),
    ".json": (
        '{\n  "name": "bench-project",\n  "version": "1.0.0",\n'
        '  "description": "Projet synthétique de benchmark",\n'
        '  "main": "index.js",\n  "scripts": {\n'
        '    "start": "node index.js",\n    "test": "jest"\n  },\n'
        '  "dependencies": {},\n  "devDependencies": {}\n}\n'
    ),
    ".md": (
        "# Module de benchmark\n\n"
        "Ce fichier est généré automatiquement par le benchmark TreeForge.\n\n"
        "## Description\n\nContenu synthétique de taille réaliste.\n\n"
        "## Usage\n\n```python\nfrom module import BenchClass\nobj = BenchClass(42)\n```\n\n"
        "## Notes\n\nAucune dépendance externe requise.\n"
    ),
    ".ts": (
        "// TypeScript synthétique\n\n"
        "interface BenchInterface {\n  value: number;\n  compute(): number;\n}\n\n"
        "class BenchClass implements BenchInterface {\n"
        "  constructor(public value: number = 0) {}\n\n"
        "  compute(): number {\n    return this.value * 2 + 1;\n  }\n}\n\n"
        "export { BenchClass };\n"
    ),
    ".sql": (
        "-- Script SQL synthétique\n\n"
        "CREATE TABLE IF NOT EXISTS bench_table (\n"
        "    id      INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "    name    TEXT NOT NULL,\n"
        "    value   INTEGER DEFAULT 0,\n"
        "    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n\n"
        "INSERT INTO bench_table (name, value) VALUES ('item_1', 10);\n"
        "INSERT INTO bench_table (name, value) VALUES ('item_2', 20);\n\n"
        "SELECT * FROM bench_table ORDER BY created DESC;\n"
    ),
    ".txt": "Fichier texte synthétique de benchmark.\nContenu de remplissage.\n",
    ".gitignore": "__pycache__/\n*.pyc\nnode_modules/\n.env\ndist/\nbuild/\n",
    ".env": "# Variables d'environnement\nDEBUG=false\nPORT=8000\nSECRET_KEY=bench\n",
}

_FALLBACK_CONTENT = "# Contenu synthétique de benchmark\n"


def _write_file(path: Path, ext: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _CONTENT.get(ext, _FALLBACK_CONTENT)
    path.write_text(content, encoding="utf-8")


# ── Profils de projets ────────────────────────────────────────────────────────

def _make_python_simple(root: Path) -> None:
    """
    Projet Python simple type 'calculator' : ~15 fichiers texte, ~45 Ko.
    Structure : src/ + tests/ + config
    """
    files = [
        ("src/calculator/__init__.py",    ".py"),
        ("src/calculator/core.py",        ".py"),
        ("src/calculator/operations.py",  ".py"),
        ("src/calculator/utils.py",       ".py"),
        ("src/calculator/exceptions.py",  ".py"),
        ("tests/__init__.py",             ".py"),
        ("tests/test_core.py",            ".py"),
        ("tests/test_operations.py",      ".py"),
        ("tests/test_utils.py",           ".py"),
        ("docs/README.md",                ".md"),
        ("docs/CHANGELOG.md",             ".md"),
        ("setup.py",                      ".py"),
        ("README.md",                     ".md"),
        (".gitignore",                    ".gitignore"),
        ("requirements.txt",              ".txt"),
    ]
    for rel, ext in files:
        _write_file(root / rel, ext)


def _make_web_small(root: Path) -> None:
    """
    Petit projet web HTML/CSS/JS : ~32 fichiers, ~120 Ko.
    Structure classique frontend.
    """
    files = [
        ("index.html",              ".html"),
        ("about.html",              ".html"),
        ("contact.html",            ".html"),
        ("404.html",                ".html"),
        ("css/main.css",            ".css"),
        ("css/reset.css",           ".css"),
        ("css/components.css",      ".css"),
        ("css/responsive.css",      ".css"),
        ("css/theme.css",           ".css"),
        ("js/app.js",               ".js"),
        ("js/utils.js",             ".js"),
        ("js/api.js",               ".js"),
        ("js/router.js",            ".js"),
        ("js/components/nav.js",    ".js"),
        ("js/components/modal.js",  ".js"),
        ("js/components/form.js",   ".js"),
        ("js/components/table.js",  ".js"),
        ("assets/README.md",        ".md"),
        ("docs/API.md",             ".md"),
        ("docs/DEPLOY.md",          ".md"),
        ("docs/CONTRIBUTING.md",    ".md"),
        ("tests/unit/test_app.js",  ".js"),
        ("tests/unit/test_utils.js",".js"),
        ("tests/e2e/smoke.js",      ".js"),
        ("config/webpack.js",       ".js"),
        ("config/babel.js",         ".js"),
        ("package.json",            ".json"),
        ("package-lock.json",       ".json"),
        ("tsconfig.json",           ".json"),
        ("README.md",               ".md"),
        (".gitignore",              ".gitignore"),
        (".env",                    ".env"),
    ]
    for rel, ext in files:
        _write_file(root / rel, ext)


def _make_treeforge_like(root: Path) -> None:
    """
    Projet Python moyen type 'TreeForge lui-même' : ~65 fichiers, ~200 Ko.
    Reproduit la structure src/pkg/core + gui + utils + tests.
    """
    # src/pkg/core
    core_modules = ["models", "parser", "generator", "recaper",
                    "template_manager", "telemetry", "config", "helpers"]
    for m in core_modules:
        _write_file(root / f"src/pkg/core/{m}.py", ".py")
    _write_file(root / "src/pkg/core/__init__.py", ".py")

    # src/pkg/gui
    gui_tabs = ["main_tab", "editor_tab", "settings_tab", "preview_tab"]
    gui_components = ["toolbar", "statusbar", "dialog", "log_panel",
                      "tree_widget", "styled_btn"]
    for t in gui_tabs:
        _write_file(root / f"src/pkg/gui/tabs/{t}.py", ".py")
    for c in gui_components:
        _write_file(root / f"src/pkg/gui/components/{c}.py", ".py")
    _write_file(root / "src/pkg/gui/__init__.py", ".py")
    _write_file(root / "src/pkg/gui/main_window.py", ".py")

    # src/pkg/utils
    utils = ["logger", "helpers", "context_menu", "drag_drop", "validators"]
    for u in utils:
        _write_file(root / f"src/pkg/utils/{u}.py", ".py")
    _write_file(root / "src/pkg/utils/__init__.py", ".py")

    # resources
    templates = ["django", "flask", "react-vite", "vue-vite",
                 "nodejs-api", "python-package"]
    for t in templates:
        _write_file(root / f"src/pkg/resources/templates/{t}.json", ".json")
    _write_file(root / "src/pkg/resources/stock/user_prefs.json", ".json")
    _write_file(root / "src/pkg/resources/stock/tips.json", ".json")

    # tests
    tests = ["test_parser", "test_generator", "test_recaper",
             "test_models", "test_helpers", "test_template_manager",
             "benchmark_generator", "conftest"]
    for t in tests:
        _write_file(root / f"tests/{t}.py", ".py")

    # racine
    for f, ext in [
        ("README.md", ".md"),
        ("CHANGELOG.md", ".md"),
        ("CONTRIBUTING.md", ".md"),
        ("pyproject.toml", ".txt"),
        ("requirements.txt", ".txt"),
        ("Main.py", ".py"),
        (".gitignore", ".gitignore"),
        (".env", ".env"),
    ]:
        _write_file(root / f, ext)


def _make_django_intermediate(root: Path) -> None:
    """
    Projet Django intermédiaire : ~120 fichiers, ~450 Ko.
    Structure typique d'une app Django avec plusieurs modules métier.
    """
    apps = ["users", "products", "orders", "payments", "notifications"]
    django_files = ["models", "views", "serializers", "urls",
                    "admin", "forms", "signals", "tasks", "utils"]

    for app in apps:
        for f in django_files:
            _write_file(root / f"apps/{app}/{f}.py", ".py")
        _write_file(root / f"apps/{app}/__init__.py", ".py")
        _write_file(root / f"apps/{app}/tests/test_{f}.py", ".py")
        _write_file(root / f"apps/{app}/migrations/0001_initial.py", ".py")
        _write_file(root / f"apps/{app}/migrations/__init__.py", ".py")

    # config Django
    config_files = ["settings/base", "settings/dev", "settings/prod",
                    "urls", "wsgi", "asgi", "celery"]
    for f in config_files:
        _write_file(root / f"config/{f}.py", ".py")

    # templates HTML
    templates_html = ["base", "index", "login", "register",
                      "dashboard", "profile", "404", "500"]
    for t in templates_html:
        _write_file(root / f"templates/{t}.html", ".html")

    # static
    static_css = ["base", "components", "dashboard", "auth"]
    for s in static_css:
        _write_file(root / f"static/css/{s}.css", ".css")

    static_js = ["app", "utils", "api", "charts"]
    for s in static_js:
        _write_file(root / f"static/js/{s}.js", ".js")

    # docs
    docs = ["API.md", "INSTALL.md", "DEPLOY.md", "CONTRIBUTING.md", "README.md"]
    for d in docs:
        _write_file(root / f"docs/{d}", ".md")

    # SQL migrations / scripts
    for i in range(1, 4):
        _write_file(root / f"scripts/migration_{i:02d}.sql", ".sql")

    # racine
    for f, ext in [
        ("manage.py", ".py"),
        ("requirements.txt", ".txt"),
        ("requirements-dev.txt", ".txt"),
        ("README.md", ".md"),
        ("CHANGELOG.md", ".md"),
        (".gitignore", ".gitignore"),
        (".env", ".env"),
        ("docker-compose.yml", ".txt"),
        ("Makefile", ".txt"),
    ]:
        _write_file(root / f, ext)


# Catalogue des profils disponibles
PROFILES: dict[str, callable] = {
    "python_simple":       _make_python_simple,
    "web_small":           _make_web_small,
    "treeforge_like":      _make_treeforge_like,
    "django_intermediate": _make_django_intermediate,
}


# ─────────────────────────────────────────────────────────────────────────────
# Comptage des fichiers et taille totale
# ─────────────────────────────────────────────────────────────────────────────

def _count_project(root: Path) -> tuple[int, int]:
    """Retourne (nb_fichiers_texte, taille_totale_ko)."""
    from treeforge.core.recaper import _is_text_file, DEFAULT_EXCLUDE_DIRS

    total_size = 0
    nb_files   = 0
    for p in root.rglob("*"):
        if p.is_file() and _is_text_file(p):
            # Exclure les dossiers listés dans DEFAULT_EXCLUDE_DIRS
            parts = set(p.parts)
            if parts & DEFAULT_EXCLUDE_DIRS:
                continue
            nb_files  += 1
            total_size += p.stat().st_size

    return nb_files, total_size // 1024  # → Ko


# ─────────────────────────────────────────────────────────────────────────────
# Mesure d'un seul run
# ─────────────────────────────────────────────────────────────────────────────

def _measure_once(project_root: Path) -> float:
    """
    Appelle recap() sur project_root et retourne le temps en ms.
    Le recap est écrit dans un sous-dossier temporaire séparé.
    """
    out_tmp = Path(tempfile.mkdtemp(prefix="treeforge_recap_out_"))
    try:
        t0 = time.perf_counter()
        recap(root=project_root, output_dir=out_tmp)
        t1 = time.perf_counter()
        return (t1 - t0) * 1_000  # → ms
    finally:
        shutil.rmtree(out_tmp, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# Série de mesures
# ─────────────────────────────────────────────────────────────────────────────

def _benchmark_profile(
    profile_name: str,
    n_runs: int = 10,
    warmup: int = 2,
) -> dict:
    """
    Crée le projet synthétique UNE seule fois, puis mesure n_runs fois.
    Le projet reste intact entre les runs (seule la sortie recap change).
    """
    build_fn = PROFILES[profile_name]

    # Créer le projet synthétique dans un dossier temporaire permanent
    project_tmp = Path(tempfile.mkdtemp(prefix=f"treeforge_proj_{profile_name}_"))
    try:
        build_fn(project_tmp)
        nb_files, size_ko = _count_project(project_tmp)

        # Warmup
        for _ in range(warmup):
            _measure_once(project_tmp)

        # Runs réels
        samples = [_measure_once(project_tmp) for _ in range(n_runs)]

    finally:
        shutil.rmtree(project_tmp, ignore_errors=True)

    return {
        "profile"   : profile_name,
        "nb_files"  : nb_files,
        "size_ko"   : size_ko,
        "n_runs"    : n_runs,
        "mean_ms"   : statistics.mean(samples),
        "median_ms" : statistics.median(samples),
        "stdev_ms"  : statistics.stdev(samples) if len(samples) > 1 else 0.0,
        "min_ms"    : min(samples),
        "max_ms"    : max(samples),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Libellés humains pour l'affichage
# ─────────────────────────────────────────────────────────────────────────────

LABELS = {
    "python_simple"      : "Projet Python simple   (ex: calculator)",
    "web_small"          : "Petit projet web       (HTML/CSS/JS)    ",
    "treeforge_like"     : "TreeForge lui-même     (référence)      ",
    "django_intermediate": "Projet Django          (intermédiaire)  ",
}


# ─────────────────────────────────────────────────────────────────────────────
# Export CSV
# ─────────────────────────────────────────────────────────────────────────────

def _export_csv(results: list[dict]) -> None:
    import csv
    out = Path(__file__).parent / "benchmark_recaper_results.csv"
    fieldnames = [
        "profile", "nb_files", "size_ko", "n_runs",
        "mean_ms", "median_ms", "stdev_ms", "min_ms", "max_ms",
    ]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)
    print(f"\n  Fichier exporté : {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    N_RUNS = 10
    WARMUP = 2

    print("\n" + "=" * 78)
    print("  TREEFORGE — Benchmark Recaper")
    print("=" * 78)
    _print_system_info()
    print(f"  Runs par profil : {N_RUNS}  |  Warmup : {WARMUP}")
    print("=" * 78)

    print(
        f"\n  {'Profil':<45}  {'Fichiers':>8}  {'Ko':>6}"
        f"  {'Moy (ms)':>9}  {'Méd (ms)':>9}  {'σ (ms)':>7}"
        f"  {'Min':>7}  {'Max':>7}"
    )
    print("  " + "-" * 106)

    results: list[dict] = []

    for profile_name in PROFILES:
        label = LABELS[profile_name]
        print(f"  {label:<45}", end="", flush=True)

        r = _benchmark_profile(profile_name, n_runs=N_RUNS, warmup=WARMUP)
        results.append(r)

        print(
            f"  {r['nb_files']:>8}"
            f"  {r['size_ko']:>6}"
            f"  {r['mean_ms']:>9.1f}"
            f"  {r['median_ms']:>9.1f}"
            f"  {r['stdev_ms']:>7.1f}"
            f"  {r['min_ms']:>7.1f}"
            f"  {r['max_ms']:>7.1f}"
        )

    _export_csv(results)

    print("\n" + "=" * 78)
    print("  Résultats pour le rapport :")
    print("=" * 78)
    print(
        f"  {'Type de projet':<45}  {'Nb fichiers':>11}  {'Taille':>8}"
        f"  {'Temps moy.':>10}  {'Observation'}"
    )
    print("  " + "-" * 106)
    for r in results:
        label    = LABELS[r["profile"]]
        mean_s   = r["mean_ms"] / 1000
        obs      = f"< {mean_s:.1f} s"
        print(
            f"  {label:<45}  {r['nb_files']:>11}  {r['size_ko']:>6} Ko"
            f"  {r['mean_ms']:>8.0f} ms  {obs}"
        )
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()