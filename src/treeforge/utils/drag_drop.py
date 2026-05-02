"""
drag_drop.py — Gestion du Drag & Drop pour TreeForge.

Stratégie : import conditionnel avec fallback total.
Si tkinterdnd2 est absent ou cassé → DND_AVAILABLE = False
et l'appli continue de fonctionner normalement sans D&D.

Usage depuis generator_tab.py :
    from treeforge.utils.drag_drop import setup_drop_target, DND_AVAILABLE
    setup_drop_target(widget, callback=mon_handler)
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Callable

# ── Tentative d'import tkinterdnd2 ───────────────────────────────────────────
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD   # noqa: F401
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False


# ── Extensions de fichiers acceptées en D&D ──────────────────────────────────
_ACCEPTED_EXTENSIONS = {".txt", ".json", ".md", ".text"}


def _parse_drop_data(raw: str) -> list[Path]:
    """
    Nettoie la chaîne brute retournée par tkinterdnd2.
    Peut contenir : un chemin simple, ou plusieurs entre accolades.
    Exemples :
        "C:/Users/foo/arbo.txt"
        "{C:/Users/foo/mon fichier.txt} {C:/autre.json}"
    """
    raw = raw.strip()
    paths: list[Path] = []

    if raw.startswith("{"):
        # Plusieurs fichiers ou chemin avec espaces → split sur }  {
        import re
        parts = re.findall(r"\{([^}]+)\}", raw)
        for p in parts:
            paths.append(Path(p.strip()))
    else:
        paths.append(Path(raw))

    return paths


def setup_drop_target(
    widget,
    on_drop: Callable[[str], None],
) -> bool:
    """
    Enregistre `widget` comme cible de drag & drop.

    Paramètres
    ----------
    widget   : CTkTextbox ou tout widget tkinter
    on_drop  : callback(contenu: str) appelé avec le contenu du fichier déposé

    Retourne True si le D&D a été activé, False sinon (fallback silencieux).
    """
    if not DND_AVAILABLE:
        return False

    try:
        from tkinterdnd2 import DND_FILES

        def _on_drop_event(event):
            paths = _parse_drop_data(event.data)
            if not paths:
                return

            path = paths[0]  # on ne prend que le premier fichier

            # Vérification extension
            if path.suffix.lower() not in _ACCEPTED_EXTENSIONS:
                # Feedback visuel discret — on ne bloque pas
                widget.event_generate("<<DropRejected>>")
                return

            # Lecture du fichier
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                on_drop(content)
            except Exception as e:
                widget.event_generate("<<DropError>>")
                print(f"[TreeForge D&D] Erreur lecture : {e}")

        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<Drop>>", _on_drop_event)
        return True

    except Exception as e:
        print(f"[TreeForge D&D] Activation échouée (mode sans D&D) : {e}")
        return False