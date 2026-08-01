"""Configuration globale de TreeForge."""

APP_TITLE   = "TreeForge"
__version__ = "4.0.0"

MODES_PARSING = ["🔒 Strict", "🔧 Souple", "⚡ Confiant"]
MODES_CONTENU = ["Vide", "Minimal", "Boilerplate"]

# Boilerplate par extension
from treeforge.utils.helpers import load_boilerplates
BOILERPLATE: dict[str, str] = load_boilerplates()