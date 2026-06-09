"""
Générateur de fichiers et dossiers sur le disque.
Prend un ParseResult et crée la structure à la destination choisie.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Callable

from treeforge.core.models import TreeNode, ParseResult
from treeforge.config import BOILERPLATE


def _get_content(node: TreeNode, content_mode: str) -> str:
    """Retourne le contenu à écrire selon le mode choisi."""
    if content_mode == "Vide":
        return ""
    if content_mode == "Minimal":
        return node.content  # contenu fourni dans l'arborescence
    if content_mode == "Boilerplate":
        suffix = Path(node.name).suffix.lower()
        return BOILERPLATE.get(suffix, "")
    return ""


def generate(
    parse_result: ParseResult,
    destination: str | Path,
    content_mode: str = "Vide",
    on_progress: Callable[[str], None] | None = None,
) -> tuple[int, int, list[str]]:
    """
    Génère la structure sur le disque.

    Returns:
        (nb_dossiers, nb_fichiers, liste_erreurs)
    """
    dest = Path(destination)
    if not dest.exists():
        dest.mkdir(parents=True)

    nb_dirs = 0
    nb_files = 0
    errors: list[str] = []

    def _create(node: TreeNode, parent: Path) -> None:
        if node.excluded:
            return
        nonlocal nb_dirs, nb_files
        path = parent / node.name

        try:
            if node.is_dir:
                path.mkdir(parents=True, exist_ok=True)
                nb_dirs += 1
                if on_progress:
                    on_progress(f"📁 Dossier créé : {path}")
                for child in node.children:
                    _create(child, path)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                content = _get_content(node, content_mode)
                path.write_text(content, encoding="utf-8")
                nb_files += 1
                if on_progress:
                    on_progress(f"📄 Fichier créé : {path}")
        except OSError as e:
            errors.append(f"Erreur sur « {path} » : {e}")
            if on_progress:
                on_progress(f"❌ Erreur : {e}")

    for root_node in parse_result.nodes:
        _create(root_node, dest)

    return nb_dirs, nb_files, errors