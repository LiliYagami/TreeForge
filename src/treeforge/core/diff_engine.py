"""
core/diff_engine.py — Calcul d'un plan avant écriture disque.

Compare ce qui serait écrit (depuis un ParseResult pour Générer, ou un recap
.txt pour Restaurer) avec l'état réel de la destination, pour que l'utilisateur
valide les changements avant application plutôt que de les subir en silence.

Réutilise volontairement les fonctions internes de generator.py et
revers_recaper.py (mêmes règles de contenu/format, un seul endroit qui sait
comment un nœud se traduit en fichier).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from treeforge.core.models import TreeNode, ParseResult
from treeforge.core.generator import _get_content
from treeforge.core.recaper import _safe_read as _read_text_safe
from treeforge.core.revers_recaper import _parse_arborescence, _parse_recap, _safe_resolve

Status = Literal["new", "modified", "unchanged"]


@dataclass
class PlanItem:
    rel_path:    str
    is_dir:      bool
    status:      Status
    old_content: str | None = None   # contenu actuel sur disque (fichiers "modified" uniquement)
    new_content: str | None = None   # contenu qui serait écrit (None = dossier, ou placeholder binaire sans texte)
    included:    bool = True         # décoché dans la modale = ignoré à l'application


@dataclass
class GenerationPlan:
    items: list[PlanItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._index: dict[str, PlanItem] = {i.rel_path: i for i in self.items}

    @property
    def new(self) -> list[PlanItem]:
        return [i for i in self.items if i.status == "new"]

    @property
    def modified(self) -> list[PlanItem]:
        return [i for i in self.items if i.status == "modified"]

    @property
    def unchanged(self) -> list[PlanItem]:
        return [i for i in self.items if i.status == "unchanged"]

    def is_included(self, rel_path: str) -> bool:
        """True si le chemin n'est pas dans le plan (rien à filtrer) ou coché."""
        item = self._index.get(rel_path)
        return item.included if item else True

    def get(self, rel_path: str) -> PlanItem | None:
        return self._index.get(rel_path)


# ─────────────────────────────────────────────────────────────────────────────
# Flux Générer
# ─────────────────────────────────────────────────────────────────────────────

def compute_plan_for_generate(
    parse_result: ParseResult,
    destination: str | Path,
    content_mode: str = "Vide",
) -> GenerationPlan:
    dest = Path(destination)
    items: list[PlanItem] = []

    def _walk(node: TreeNode, parent_rel: str, parent_abs: Path) -> None:
        if node.excluded:
            return

        rel_path = f"{parent_rel}/{node.name}" if parent_rel else node.name
        abs_path = parent_abs / node.name

        if node.is_dir:
            status = "unchanged" if abs_path.is_dir() else "new"
            items.append(PlanItem(rel_path=rel_path, is_dir=True, status=status))
            for child in node.children:
                _walk(child, rel_path, abs_path)
        else:
            new_content = _get_content(node, content_mode)
            if not abs_path.exists():
                old_content, status = None, "new"
            else:
                old_content = _read_text_safe(abs_path)
                status = "unchanged" if old_content == new_content else "modified"
            items.append(PlanItem(
                rel_path=rel_path, is_dir=False, status=status,
                old_content=old_content, new_content=new_content,
            ))

    for root_node in parse_result.nodes:
        _walk(root_node, "", dest)

    return GenerationPlan(items=items)


# ─────────────────────────────────────────────────────────────────────────────
# Flux Restaurer
# ─────────────────────────────────────────────────────────────────────────────

def compute_plan_for_restore(recap_text: str, destination: str | Path) -> GenerationPlan:
    dest = Path(destination).resolve()
    items: list[PlanItem] = []

    structure_nodes = _parse_arborescence(recap_text)
    # Dernière occurrence gagne, comme l'écriture séquentielle de extract()
    entries = dict(_parse_recap(recap_text))

    arbo_dirs  = {n.rel_path for n in structure_nodes if n.is_dir}
    arbo_files = {n.rel_path for n in structure_nodes if not n.is_dir}

    for rel in sorted(arbo_dirs):
        target = _safe_resolve(dest, rel)
        if target is None:
            continue  # chemin suspect (path traversal) — ignoré silencieusement, comme extract()
        status = "unchanged" if target.is_dir() else "new"
        items.append(PlanItem(rel_path=rel, is_dir=True, status=status))

    for rel_path, content in entries.items():
        target = _safe_resolve(dest, rel_path)
        if target is None:
            continue
        if not target.exists():
            old_content, status = None, "new"
        else:
            old_content = _read_text_safe(target)
            status = "unchanged" if old_content == content else "modified"
        items.append(PlanItem(
            rel_path=rel_path, is_dir=False, status=status,
            old_content=old_content, new_content=content,
        ))

    # Fichiers présents dans l'arborescence mais sans bloc texte (placeholders binaires) :
    # pas de contenu à comparer, juste "existe déjà" ou "sera créé vide".
    for rel in sorted(arbo_files - entries.keys()):
        target = _safe_resolve(dest, rel)
        if target is None:
            continue
        status = "unchanged" if target.exists() else "new"
        items.append(PlanItem(rel_path=rel, is_dir=False, status=status))

    return GenerationPlan(items=items)
