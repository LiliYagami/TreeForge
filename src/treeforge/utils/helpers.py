"""Fonctions utilitaires diverses."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

# ── Chemin ressources ─────────────────────────────────────────────────────────

RESOURCES_DIR = Path(__file__).parent.parent / "resources" / "stock"

# Constantes par défaut
DEFAULT_PREFS = {
    "last_destination": "",
    "destination_history": [],
    "parsing_mode": "🔒 Strict",
    "content_mode": "Vide",
    "format_mode": "Auto",
    "theme": "dark",
    "last_prompt_key": "general",
    "tips_enabled": True,
    "prompt_panel_open": False,
    "telemetry_enabled": False,
}



# ── Format tree ───────────────────────────────────────────────────────────────

def format_tree(nodes, indent: int = 0) -> str:
    """Retourne une représentation texte d'une liste de TreeNode."""
    from treeforge.core.models import TreeNode
    lines = []
    for node in nodes:
        prefix = "    " * indent
        icon = "📁" if node.is_dir else "📄"
        lines.append(f"{prefix}{icon} {node.name}")
        if node.children:
            lines.append(format_tree(node.children, indent + 1))
    return "\n".join(lines)

def safe_name(name: str) -> str:
    """Nettoie un nom de fichier/dossier des caractères interdits sur Windows."""
    forbidden = r'\/:*?"<>|'
    for ch in forbidden:
        name = name.replace(ch, "_")
    return name.strip(". ")

# ── Chargement JSON ───────────────────────────────────────────────────────────

def load_tips() -> list[str]:
    """Charge les astuces depuis resources/stock/tips.json"""
    try:
        tips_file = RESOURCES_DIR / "tips.json"
        if tips_file.exists():
            return json.loads(tips_file.read_text(encoding="utf-8"))
        else:
            return ["💡 TreeForge — Générateur d'arborescences"]
    except Exception as e:
        print(f"[helpers] Erreur lors du chargement de tips.json : {e}")
        return ["💡 TreeForge — Générateur d'arborescences"]


def load_prompts() -> dict[str, dict[str, str]]:
    """Charge les prompts IA depuis resources/stock/prompts.json"""
    try:
        prompts_file = RESOURCES_DIR / "prompts.json"
        if prompts_file.exists():
            return json.loads(prompts_file.read_text(encoding="utf-8"))
        else:
            return {}
    except Exception as e:
        print(f"[helpers] Erreur lors du chargement de prompts.json : {e}")
        return {}


def load_prefs() -> dict[str, Any]:
    """
    Charge les préférences utilisateur depuis resources/stock/user_prefs.json.
    Retourne DEFAULT_PREFS en cas d'absence ou d'erreur.
    """
    try:
        prefs_file = RESOURCES_DIR / "user_prefs.json"
        if prefs_file.exists():
            loaded = json.loads(prefs_file.read_text(encoding="utf-8"))
            # Fusionner avec les défauts (au cas où des clés manquent)
            return {**DEFAULT_PREFS, **loaded}
        else:
            return DEFAULT_PREFS.copy()
    except Exception as e:
        print(f"[helpers] Erreur lors du chargement de user_prefs.json : {e}")
        return DEFAULT_PREFS.copy()


def save_prefs(prefs: dict[str, Any]) -> bool:
    """
    Sauvegarde les préférences utilisateur dans resources/stock/user_prefs.json.
    Retourne True en cas de succès, False sinon.
    """
    try:
        RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
        prefs_file = RESOURCES_DIR / "user_prefs.json"
        prefs_file.write_text(
            json.dumps(prefs, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        return True
    except Exception as e:
        print(f"[helpers] Erreur lors de la sauvegarde de user_prefs.json : {e}")
        return False
