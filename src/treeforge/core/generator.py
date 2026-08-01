"""
Générateur de fichiers et dossiers sur le disque.
Prend un ParseResult et crée la structure à la destination choisie.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from treeforge.core.models import TreeNode, ParseResult
from treeforge.config import BOILERPLATE

if TYPE_CHECKING:
    from treeforge.core.diff_engine import GenerationPlan


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
    plan: "GenerationPlan | None" = None,
) -> tuple[int, int, list[str]]:
    """
    Génère la structure sur le disque.

    Si `plan` est fourni (calculé par core.diff_engine.compute_plan_for_generate
    sur ce même parse_result/destination/content_mode), les nœuds dont le
    PlanItem correspondant a `included=False` sont ignorés (décochés par
    l'utilisateur dans la modale de confirmation), et les fichiers dont le
    contenu est déjà identique sur disque (`status="unchanged"`) ne sont pas
    réécrits. Sans plan, comportement inchangé (écrase tout sans distinction).

    Returns:
        (nb_dossiers, nb_fichiers, liste_erreurs)
    """
    dest = Path(destination)
    if not dest.exists():
        dest.mkdir(parents=True)

    nb_dirs = 0
    nb_files = 0
    errors: list[str] = []

    def _create(node: TreeNode, parent: Path, parent_rel: str) -> None:
        if node.excluded:
            return
        nonlocal nb_dirs, nb_files
        rel_path = f"{parent_rel}/{node.name}" if parent_rel else node.name
        path = parent / node.name

        item = plan.get(rel_path) if plan is not None else None
        if item is not None and not item.included:
            if on_progress:
                on_progress(f"⏭️  Ignoré (désélectionné) : {path}")
            return

        try:
            if node.is_dir:
                path.mkdir(parents=True, exist_ok=True)
                nb_dirs += 1
                if on_progress:
                    on_progress(f"📁 Dossier créé : {path}")
                for child in node.children:
                    _create(child, path, rel_path)
            else:
                if item is not None and item.status == "unchanged":
                    if on_progress:
                        on_progress(f"⏭️  Déjà à jour : {path}")
                    return
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
        _create(root_node, dest, "")

    return nb_dirs, nb_files, errors