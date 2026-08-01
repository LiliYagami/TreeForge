"""
core/recaper.py — Module TreeForge
===================================
Reconstruit l'intégralité d'un projet en un seul fichier .txt.

Séparateur de bloc : <<TREEFORGE_FILE_BLOCK>>
Parsé par : core/revers_recaper.py

Usage CLI :
    python -m treeforge.core.recaper [dossier] [--output dossier_sortie]

Usage Python :
    from treeforge.core.recaper import recap, DEFAULT_EXCLUDE_DIRS
    out_path = recap(root="C:/mon/projet", on_progress=print)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from treeforge.core.models import TreeNode

# Forcer UTF-8 pour la console Windows
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetConsoleOutputCP(65001)


# ─────────────────────────────────────────────────────────────────────────────
# Extensions texte à inclure
# ─────────────────────────────────────────────────────────────────────────────

TEXT_EXTENSIONS: set[str] = {
    # Langages principaux
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".scss", ".sass",
    ".php", ".rb", ".go", ".rs", ".c", ".cpp", ".h",".java",
    # Config / Data
    ".json", ".xml", ".yml", ".yaml", ".toml",
    ".ini", ".cfg", ".env",
    # Docs
    ".txt", ".md", ".rst",
    # SQL
    ".sql",
    # Scripts
    ".sh", ".bat", ".ps1",
    # Git / dotfiles (nom entier — pas une extension au sens strict)
    ".gitignore", ".gitattributes", ".editorconfig",
}


# ─────────────────────────────────────────────────────────────────────────────
# Dossiers à exclure par défaut
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_EXCLUDE_DIRS: set[str] = {
    "recaps",
    "__pycache__", "node_modules", ".git", ".venv", "venv",
    "TForge_ENV", "TForge_ENV_py312","TF_venv", "dist", "build",
    ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_text_file(file_path: Path) -> bool:
    """
    Retourne True si le fichier doit être inclus dans le recap.

    FIX dotfiles : os.path.splitext('.gitignore') → ext='' → non détecté.
    On vérifie donc le nom entier pour les fichiers commençant par '.'.
    """
    name = file_path.name
    ext  = file_path.suffix.lower()

    if not ext and name.startswith("."):
        return name.lower() in TEXT_EXTENSIONS  # .gitignore, .env, etc.

    return ext in TEXT_EXTENSIONS


def _safe_read(filepath: Path) -> str:
    """
    Tente plusieurs encodages avant de se rabattre sur utf-8 errors=replace.
    Robuste face aux fichiers legacy Windows (cp1252, latin-1, utf-16).
    """
    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1", "cp1252"):
        try:
            return filepath.read_text(encoding=enc, errors="strict")
        except Exception:
            pass
    return filepath.read_text(encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────────
# Arborescence ASCII
# ─────────────────────────────────────────────────────────────────────────────

def _tree_lines(
    path: Path,
    out: list[str],
    exclude_dirs: set[str],
    prefix: str = "",
    include_paths: set[str] | None = None,
    rel_prefix: str = "",
) -> None:
    """
    Construit récursivement les lignes d'arborescence unicode.
    Dossiers affichés avant les fichiers dans chaque niveau.

    Si include_paths est fourni, seuls les chemins relatifs (posix, "/")
    présents dans cet ensemble sont affichés — utilisé par la sélection
    Recaper pour ne montrer/inclure que les éléments cochés.
    """
    try:
        entries = sorted(
            path.iterdir(),
            key=lambda p: (p.is_file(), p.name.lower())  # dossiers d'abord
        )
    except PermissionError:
        out.append(f"{prefix}└── [Permission Denied]")
        return

    entries = [e for e in entries if e.name not in exclude_dirs]
    if include_paths is not None:
        entries = [e for e in entries if f"{rel_prefix}{e.name}" in include_paths]

    for i, entry in enumerate(entries):
        is_last   = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        out.append(f"{prefix}{connector}{entry.name}")

        if entry.is_dir():
            extension = "    " if is_last else "│   "
            _tree_lines(
                entry, out, exclude_dirs, prefix + extension,
                include_paths, f"{rel_prefix}{entry.name}/",
            )


# ─────────────────────────────────────────────────────────────────────────────
# Construction du contenu — partagée entre recap() (fichier) et recap_text() (mémoire)
# ─────────────────────────────────────────────────────────────────────────────

def _build_lines(
    root: Path,
    exclude_dirs: set[str],
    exclude_files: set[str],
    timestamp: str,
    skip_path: Path | None,
    on_progress: Callable[[str], None] | None,
    include_paths: set[str] | None = None,
) -> list[str]:
    # Séparateur de bloc — parsé par revers_recaper.py
    # IMPORTANT : ne PAS utiliser "-" * 80 (présent dans le code source lui-même)
    SEP  = "=" * 80
    BLOC = "<<TREEFORGE_FILE_BLOCK>>"

    lines: list[str] = []

    # ── 1) En-tête ────────────────────────────────────────────────────────────
    lines += [
        SEP,
        "RECAP PROJECT",
        SEP,
        f"Racine du projet : {root}",
        f"Date             : {timestamp}",
        "",
    ]

    # ── 2) Arborescence ───────────────────────────────────────────────────────
    lines += [
        SEP,
        "ARBORESCENCE",
        SEP,
        f"Structure du dossier : {root.name}",
        "",
    ]
    _tree_lines(root, lines, exclude_dirs, prefix="", include_paths=include_paths)
    lines.append("")

    # ── 3) Contenu des fichiers ───────────────────────────────────────────────
    lines += [SEP, "CONTENU DES FICHIERS", SEP, ""]

    for current_dir, dirs, files in os.walk(root):
        # Élagage en place → os.walk ne descend pas dans les dossiers exclus
        dirs[:] = [d for d in sorted(dirs) if d not in exclude_dirs]
        if include_paths is not None:
            current_rel = Path(current_dir).relative_to(root)
            prefix = "" if str(current_rel) == "." else f"{current_rel.as_posix()}/"
            dirs[:] = [d for d in dirs if f"{prefix}{d}" in include_paths]

        for file_name in sorted(files):
            file_path = Path(current_dir) / file_name

            # Ignorer le fichier recap lui-même (évite la récursion) — sans
            # objet si on ne génère pas de fichier (skip_path=None)
            if skip_path is not None and file_path.resolve() == skip_path.resolve():
                continue

            # Ignorer les fichiers exclus explicitement
            if file_name in exclude_files:
                continue

            # Ignorer les fichiers non textuels
            if not _is_text_file(file_path):
                continue

            rel_path = file_path.relative_to(root)

            if include_paths is not None and rel_path.as_posix() not in include_paths:
                continue

            if on_progress:
                on_progress(f"  📄 {rel_path}")

            # ── En-tête du bloc ───────────────────────────────────────────────
            lines += [
                BLOC,
                f"FICHIER : {rel_path}",
                f"PROVENANCE : {file_path}",
                BLOC,
                "",
            ]

            # ── Contenu du fichier ────────────────────────────────────────────
            try:
                content = _safe_read(file_path)
                lines.append(content)
                if not content.strip():
                    lines.append("[Ce fichier est vide]")
            except Exception as e:
                lines.append(f"[ERREUR LECTURE] {e}")

            lines.append("")

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# Fonctions principales — API publique
# ─────────────────────────────────────────────────────────────────────────────

def recap_text(
    root: str | Path,
    exclude_dirs: set[str] | None = None,
    exclude_files: set[str] | None = None,
    on_progress: Callable[[str], None] | None = None,
    include_paths: set[str] | None = None,
) -> tuple[str, Path]:
    """
    Construit le texte recap d'un projet en mémoire, sans écrire de fichier
    .txt sur disque — destiné au mode presse-papiers (copier direct, sans
    passer par un fichier intermédiaire).

    Args:
        root          : Racine du projet à analyser.
        exclude_dirs  : Dossiers supplémentaires à ignorer (fusionné avec DEFAULT_EXCLUDE_DIRS).
        exclude_files : Fichiers spécifiques à ignorer (noms exacts).
        on_progress   : Callback(message: str) appelé pour chaque fichier traité.
        include_paths : si fourni, limite le recap à ces chemins relatifs (posix,
                        "/") — fichiers ET dossiers. Calculé via scan_tree() +
                        included_paths_from_tree() depuis la sélection utilisateur.

    Returns:
        (texte_recap, racine_résolue)
    """
    root          = Path(root).resolve()
    exclude_dirs  = (exclude_dirs or set()) | DEFAULT_EXCLUDE_DIRS
    exclude_files = exclude_files or set()
    timestamp     = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lines = _build_lines(root, exclude_dirs, exclude_files, timestamp, skip_path=None,
                          on_progress=on_progress, include_paths=include_paths)
    text  = "\n".join(lines)

    if on_progress:
        on_progress("✅ Recap généré en mémoire (presse-papiers)")

    return text, root


def recap(
    root: str | Path,
    output_dir: str | Path | None = None,
    exclude_dirs: set[str] | None = None,
    exclude_files: set[str] | None = None,
    on_progress: Callable[[str], None] | None = None,
    include_paths: set[str] | None = None,
) -> Path:
    """
    Génère le fichier recap d'un projet.

    Args:
        root          : Racine du projet à analyser.
        output_dir    : Dossier de sortie (défaut : root/recaps/).
        exclude_dirs  : Dossiers supplémentaires à ignorer (fusionné avec DEFAULT_EXCLUDE_DIRS).
        exclude_files : Fichiers spécifiques à ignorer (noms exacts).
        on_progress   : Callback(message: str) appelé pour chaque fichier traité.
        include_paths : si fourni, limite le recap à ces chemins relatifs (posix,
                        "/") — fichiers ET dossiers. Calculé via scan_tree() +
                        included_paths_from_tree() depuis la sélection utilisateur.

    Returns:
        Path vers le fichier .txt généré.
    """
    root          = Path(root).resolve()
    exclude_dirs  = (exclude_dirs or set()) | DEFAULT_EXCLUDE_DIRS
    exclude_files = exclude_files or set()
    output_dir    = Path(output_dir).resolve() if output_dir else root / "recaps"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_name  = f"recap_{root.name}_{timestamp}.txt"
    out_path  = output_dir / out_name

    lines = _build_lines(root, exclude_dirs, exclude_files, timestamp, skip_path=out_path,
                          on_progress=on_progress, include_paths=include_paths)

    # ── Écriture du fichier recap ─────────────────────────────────────────────
    out_path.write_text("\n".join(lines), encoding="utf-8")

    if on_progress:
        on_progress(f"✅ Recap généré : {out_path}")

    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# Sélection interactive avant recap
# ─────────────────────────────────────────────────────────────────────────────

def scan_tree(
    root: str | Path,
    exclude_dirs: set[str] | None = None,
    exclude_files: set[str] | None = None,
) -> list[TreeNode]:
    """
    Construit un arbre TreeNode à partir du contenu réel d'un dossier sur
    disque — pour la sélection interactive avant recap (inclusion/exclusion
    par fichier/dossier via TreeNode.excluded, même modèle que le générateur).

    Retourne les nœuds de premier niveau (le contenu de `root`, pas `root`
    lui-même — il n'apparaît pas comme une ligne dans l'arborescence recap).
    Les dossiers de DEFAULT_EXCLUDE_DIRS sont exclus du scan (jamais affichés),
    pas juste pré-décochés — un projet avec node_modules/ ne doit pas ramer
    à l'ouverture de la modale.
    """
    root          = Path(root).resolve()
    exclude_dirs  = (exclude_dirs or set()) | DEFAULT_EXCLUDE_DIRS
    exclude_files = exclude_files or set()

    def _scan_dir(path: Path) -> list[TreeNode]:
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return []

        nodes: list[TreeNode] = []
        for entry in entries:
            if entry.is_dir():
                if entry.name in exclude_dirs:
                    continue
                node = TreeNode(name=entry.name, is_dir=True)
                node.children = _scan_dir(entry)
                nodes.append(node)
            else:
                if entry.name in exclude_files:
                    continue
                size = 0
                if _is_text_file(entry):
                    try:
                        size = entry.stat().st_size
                    except OSError:
                        size = 0
                nodes.append(TreeNode(name=entry.name, is_dir=False, size=size))
        return nodes

    return _scan_dir(root)


def included_paths_from_tree(nodes: list[TreeNode]) -> set[str]:
    """
    Aplatit un arbre de sélection (TreeNode.excluded, coché/décoché dans la
    modale) en l'ensemble des chemins relatifs — fichiers ET dossiers — à
    passer à recap()/recap_text() via include_paths.

    Un nœud exclu (et donc tous ses descendants) est simplement absent du
    résultat, comme le générateur le fait déjà pour node.excluded.
    """
    included: set[str] = set()

    def _walk(node: TreeNode, parent_rel: str) -> None:
        if node.excluded:
            return
        rel = f"{parent_rel}/{node.name}" if parent_rel else node.name
        included.add(rel)
        for child in node.children:
            _walk(child, rel)

    for root_node in nodes:
        _walk(root_node, "")

    return included


# ─────────────────────────────────────────────────────────────────────────────
# CLI standalone
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TForge Recaper — standalone")
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Racine du projet (défaut : dossier courant)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Dossier de sortie pour le recap",
    )
    args = parser.parse_args()

    result = recap(
        root=args.root,
        output_dir=args.output,
        on_progress=print,
    )
    print(f"\n[OK] {result}")