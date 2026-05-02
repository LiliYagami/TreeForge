# 🌳 TreeForge v1.0

**Générateur d'arborescences — Windows — Copier-coller → Générer → Fermer**

## Lancement rapide

```powershell
# 1. Créer et activer l'environnement
python -m venv TForge_ENV
.\TForge_ENV\Scripts\Activate.ps1

# 2. Installer les dépendances
pip install customtkinter tkinterdnd2 pyinstaller

# 3. Lancer
python main.py
```

## Structure

```
src/treeforge/
├── config.py              # Constantes globales
├── main.py                # Point d'entrée
├── core/
│   ├── models.py          # TreeNode, ParseResult
│   ├── parser.py          # Parser texte indenté + JSON
│   ├── generator.py       # Création sur disque
│   ├── recaper.py         # Export projet → .txt
│   └── template_manager.py
├── gui/
│   ├── main_window.py     # Fenêtre principale
│   ├── tabs/
│   │   ├── generator_tab.py
│   │   ├── templates_tab.py
│   │   └── recaper_tab.py
│   └── components/
│       └── log_panel.py
├── resources/
│   └── templates/         # JSON des templates intégrés
└── utils/
    ├── logger.py
    └── helpers.py
```