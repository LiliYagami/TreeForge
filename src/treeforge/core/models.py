"""Modèles de données de TreeForge."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class TreeNode:
    """Nœud d'arborescence : peut être un fichier ou un dossier."""
    name: str
    is_dir: bool = False
    children: list["TreeNode"] = field(default_factory=list)
    content: str = ""
    depth: int = 0

    def __repr__(self) -> str:
        kind = "📁" if self.is_dir else "📄"
        return f"{kind} {self.name}"

    def flatten(self) -> list["TreeNode"]:
        result = [self]
        for child in self.children:
            result.extend(child.flatten())
        return result


@dataclass
class ParseResult:
    """Résultat d'un parsing."""
    nodes: list[TreeNode] = field(default_factory=list)
    errors: list[str]     = field(default_factory=list)
    warnings: list[str]   = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0