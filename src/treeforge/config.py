"""Configuration globale de TreeForge."""

APP_TITLE   = "TreeForge"
__version__ = "1.0.0"

MODES_PARSING = ["🔒 Strict", "🔧 Souple", "⚡ Confiant"]
MODES_CONTENU = ["Vide", "Minimal", "Boilerplate"]

# Boilerplate par extension
BOILERPLATE: dict[str, str] = {
    ".html": "<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n  <meta charset=\"UTF-8\">\n  <title>Document</title>\n</head>\n<body>\n\n</body>\n</html>\n",
    ".css":  "/* styles */\n",
    ".js":   "// script\n",
    ".py":   "# -*- coding: utf-8 -*-\n",
    ".ts":   "// TypeScript\n",
    ".jsx":  "// React component\nexport default function Component() {\n  return <div></div>;\n}\n",
    ".tsx":  "// React + TypeScript\nexport default function Component() {\n  return <div></div>;\n}\n",
    ".json": "{}\n",
    ".md":   "# Titre\n",
    ".gitignore": "__pycache__/\n*.pyc\nnode_modules/\n.env\n",
    ".env":  "# Variables d'environnement\n",
    ".sql":  "-- SQL\n",
}