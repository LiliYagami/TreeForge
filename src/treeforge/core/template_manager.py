"""
Gestionnaire de templates JSON intégrés.
Charge les templates depuis resources/templates/*.json
"""
from __future__ import annotations
import json
from pathlib import Path

from treeforge.core.models import TreeNode
from treeforge.core.parser import _node_from_json  # réutilise le parser JSON


TEMPLATES_DIR = Path(__file__).parent.parent / "resources" / "templates"


def list_templates() -> list[str]:
    """Retourne les noms des templates disponibles (sans extension)."""
    if not TEMPLATES_DIR.exists():
        return []
    return sorted(p.stem for p in TEMPLATES_DIR.glob("*.json"))


def load_template(name: str) -> list[TreeNode]:
    """Charge un template par son nom et retourne la liste de nœuds racines."""
    path = TEMPLATES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Template introuvable : {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]
    return [_node_from_json(obj) for obj in data]