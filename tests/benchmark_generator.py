# tests/benchmark_generator.py
"""
Benchmark réel du générateur TreeForge.
Mesure le temps de génération pour N nœuds sur disque.

Usage :
    python tests/benchmark_generator.py
"""
from __future__ import annotations
import sys
import time
import statistics
import tempfile
import shutil
from pathlib import Path

# ── Accès au package src ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from treeforge.core.models import TreeNode, ParseResult
from treeforge.core.generator import generate


# ─────────────────────────────────────────────────────────────────────────────
# Générateurs de structures synthétiques
# ─────────────────────────────────────────────────────────────────────────────

def _make_flat_tree(n_files: int) -> ParseResult:
    """
    Structure plate : 1 dossier racine contenant n_files fichiers.
    Chaque nœud = 1 fichier .py vide.
    Nœuds totaux = 1 (racine) + n_files.
    """
    root = TreeNode(name="bench_root", is_dir=True, depth=0)
    for i in range(n_files):
        root.children.append(
            TreeNode(name=f"file_{i:04d}.py", is_dir=False, depth=1)
        )
    return ParseResult(nodes=[root])


def _make_deep_tree(n_target: int) -> ParseResult:
    """
    Structure réaliste : arbre à plusieurs niveaux.
    Ratio approximatif : 30 % dossiers / 70 % fichiers.
    Reproduit un vrai projet Python (src/, tests/, docs/, etc.)
    """
    dirs_budget  = max(1, n_target * 30 // 100)
    files_budget = n_target - dirs_budget

    root = TreeNode(name="bench_project", is_dir=True, depth=0)
    current_dirs = [root]
    dir_count    = 1
    file_count   = 0

    # Remplissage en largeur d'abord
    i = 0
    while file_count < files_budget:
        parent = current_dirs[i % len(current_dirs)]

        # Ajouter des sous-dossiers si budget restant
        if dir_count < dirs_budget:
            sub = TreeNode(
                name=f"pkg_{dir_count:03d}",
                is_dir=True,
                depth=parent.depth + 1,
            )
            parent.children.append(sub)
            current_dirs.append(sub)
            dir_count += 1

        # Ajouter 3 fichiers par passage
        for j in range(3):
            if file_count >= files_budget:
                break
            parent.children.append(
                TreeNode(
                    name=f"module_{file_count:04d}.py",
                    is_dir=False,
                    depth=parent.depth + 1,
                )
            )
            file_count += 1

        i += 1

    return ParseResult(nodes=[root])


# ─────────────────────────────────────────────────────────────────────────────
# Mesure d'un seul run
# ─────────────────────────────────────────────────────────────────────────────

def _measure_once(
    parse_result: ParseResult,
    content_mode: str = "Vide",
) -> float:
    """
    Génère dans un dossier temporaire et retourne le temps en ms.
    Le dossier est supprimé après chaque run pour éviter les
    effets de cache OS (fichiers déjà existants → exist_ok).
    """
    tmp = tempfile.mkdtemp(prefix="treeforge_bench_")
    try:
        t0 = time.perf_counter()
        generate(parse_result, tmp, content_mode=content_mode)
        t1 = time.perf_counter()
        return (t1 - t0) * 1_000  # → millisecondes
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# Série de mesures (warmup + N runs)
# ─────────────────────────────────────────────────────────────────────────────

def _benchmark(
    n_nodes: int,
    tree_type: str = "deep",   # "flat" | "deep"
    n_runs: int    = 10,
    warmup: int    = 2,
    content_mode: str = "Vide",
) -> dict:
    """
    Retourne un dict avec mean, median, stdev, min, max (en ms).
    """
    build_fn = _make_flat_tree if tree_type == "flat" else _make_deep_tree

    # ── Warmup : évite que le 1er run soit pénalisé (import, caches OS) ──────
    for _ in range(warmup):
        _measure_once(build_fn(n_nodes), content_mode)

    # ── Runs réels ────────────────────────────────────────────────────────────
    samples = [
        _measure_once(build_fn(n_nodes), content_mode)
        for _ in range(n_runs)
    ]

    return {
        "n_nodes"     : n_nodes,
        "tree_type"   : tree_type,
        "content_mode": content_mode,
        "n_runs"      : n_runs,
        "mean_ms"     : statistics.mean(samples),
        "median_ms"   : statistics.median(samples),
        "stdev_ms"    : statistics.stdev(samples) if len(samples) > 1 else 0.0,
        "min_ms"      : min(samples),
        "max_ms"      : max(samples),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def main():

    # ── Infos machine ──────────────────────────────────────────────
    import platform
    try:
        import psutil
        ram = f"{psutil.virtual_memory().total // (1024**3)} Go"
    except ImportError:
        ram = "? (pip install psutil)"

    def _print_system_info():
        print(f"  OS      : {platform.system()} {platform.release()}")
        print(f"  CPU     : {platform.processor()}")
        print(f"  RAM     : {ram}")
        print(f"  Python  : {platform.python_version()}")

    _print_system_info()
    # ───────────────────────────────────────────────────────────────
    
    SIZES       = [10, 50, 100, 150, 200, 300]
    TREE_TYPES  = ["flat", "deep"]
    MODES       = ["Vide", "Boilerplate"]
    N_RUNS      = 10
    WARMUP      = 2

    results: list[dict] = []

    print("\n" + "=" * 70)
    print("  TREEFORGE — Benchmark générateur")
    print("=" * 70)
    print(f"  Runs par config : {N_RUNS}  |  Warmup : {WARMUP}")
    print("=" * 70)

    for tree_type in TREE_TYPES:
        for mode in MODES:
            print(f"\n  [{tree_type.upper()} / mode={mode}]")
            print(f"  {'Nœuds':>6}  {'Moy (ms)':>10}  {'Méd (ms)':>10}"
                  f"  {'σ (ms)':>8}  {'Min':>8}  {'Max':>8}")
            print("  " + "-" * 62)

            for n in SIZES:
                r = _benchmark(
                    n_nodes      = n,
                    tree_type    = tree_type,
                    n_runs       = N_RUNS,
                    warmup       = WARMUP,
                    content_mode = mode,
                )
                results.append(r)
                print(
                    f"  {r['n_nodes']:>6}"
                    f"  {r['mean_ms']:>10.1f}"
                    f"  {r['median_ms']:>10.1f}"
                    f"  {r['stdev_ms']:>8.1f}"
                    f"  {r['min_ms']:>8.1f}"
                    f"  {r['max_ms']:>8.1f}"
                )

    # ── Export CSV ────────────────────────────────────────────────────────────
    _export_csv(results)

    print("\n" + "=" * 70)
    print("  Fichier exporté : benchmark_results.csv")
    print("=" * 70 + "\n")


def _export_csv(results: list[dict]) -> None:
    import csv
    out = Path(__file__).parent / "benchmark_results.csv"
    fieldnames = [
        "n_nodes", "tree_type", "content_mode", "n_runs",
        "mean_ms", "median_ms", "stdev_ms", "min_ms", "max_ms",
    ]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)


if __name__ == "__main__":
    main()
