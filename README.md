# 🌳 TreeForge v1.0

**Générateur d'arborescences — Windows — Copier-coller → Générer → Fermer**

TreeForge est un outil complet pour Windows permettant de générer rapidement des structures physiques de répertoires à partir de représentations textuelles, d'exporter un projet entier en un seul fichier récapitulatif pour les IA (ChatGPT, Claude, Gemini), et de reconstruire des projets depuis ces récapitulatifs.

---

## 🚀 Lancement rapide

```powershell
# 1. Activer l'environnement virtuel existant
.\TF_venv\Scripts\Activate.ps1

# (Optionnel) Si vous devez le recréer :
# python -m venv TF_venv
# .\TF_venv\Scripts\Activate.ps1

# 2. Installer toutes les dépendances requises
pip install -r requirements.txt

# 3. Lancer l'application
python Main.py
```

---

## 🛠️ Fonctionnalités clés

1.  **Générateur d'arborescence** : Copiez-collez une structure texte (Unicode `├──`, Windows `tree /f`, Indentation pure ou JSON) et TreeForge génère les dossiers et fichiers sur le disque.
2.  **Aperçu Interactif** : Visualisez la structure avant génération dans un arbre interactif. Excluez ou incluez des éléments à l'aide de la touche **Espace** ou du **clic droit**.
3.  **Boilerplates Personnalisables** : Les fichiers créés peuvent être pré-remplis de codes de démarrage configurables via le fichier externe [boilerplates.json](file:///c:/Users/darec/OneDrive/Desktop/TreeForge_V3.0.0/src/treeforge/resources/stock/boilerplates.json). Un **éditeur de boilerplates graphique** est accessible directement dans les Paramètres.
4.  **Recaper** : Compile l'arborescence et tout le code texte de votre projet dans un fichier unique `.txt` prêt à être envoyé à une IA.
5.  **Restaurer (ReversRecaper)** : Recrée intégralement les dossiers et les fichiers (incluant la reconstruction des fichiers binaires vides) à partir d'un fichier récapitulatif `.txt`.
6.  **Thème & Paramètres avancés** : Changez instantanément l'apparence de l'application (Sombre / Clair / Système), gérez l'affichage des astuces, les modes par défaut et effectuez des réinitialisations d'usine dans les Paramètres (`⚙️`).
7.  **Sélecteur de Prompts IA** : Choisissez instantanément parmi 9 modèles de prompts IA adaptés (Général, Python, Django, React, MySQL, Strict, Souple...) depuis le menu déroulant du panneau Prompt IA de l'onglet Générateur.

---

## 📁 Structure du Projet

```
treeforge/
├── src/treeforge/
│   ├── config.py              # Constantes et configuration globale
│   ├── main.py                # Point d'entrée de l'application
│   ├── core/
│   │   ├── models.py          # Modèles de données (TreeNode, ParseResult)
│   │   ├── parser.py          # Analyseur syntaxique multi-format
│   │   ├── generator.py       # Générateur physique sur le disque
│   │   ├── recaper.py         # Outil d'export de projet -> .txt
│   │   ├── revers_recaper.py  # Outil de restauration de projet <- .txt
│   │   └── template_manager.py # Gestion des modèles JSON intégrés
│   ├── gui/
│   │   ├── main_window.py     # Fenêtre principale et onglets
│   │   ├── tabs/
│   │   │   ├── generator_tab.py       # Onglet de génération directe
│   │   │   ├── recaper_tab.py         # Onglet de compilation de projet
│   │   │   ├── revers_recaper_tab.py  # Onglet de restauration
│   │   │   └── templates_tab.py       # Onglet de modèles pré-intégrés
│   │   └── components/
│   │       ├── preview_modal.py  # Modale d'aperçu pré-génération
│   │       ├── preview_tree.py   # Treeview interactif avec exclusions
│   │       ├── settings_dialog.py # Dialogue des paramètres et thèmes
│   │       ├── consent_dialog.py  # Boîte de dialogue RGPD/Télémétrie
│   │       └── log_panel.py      # Console de logs asynchrone
│   ├── resources/
│   │   ├── templates/         # Fichiers JSON des templates de projets
│   │   └── stock/             # Préférences, prompts et boilerplates
│   └── utils/
│       ├── logger.py          # Gestionnaire de journalisation
│       ├── helpers.py         # Fonctions d'aide (IO, nettoyage, etc.)
│       ├── drag_drop.py       # Fix pour le support du Glisser-Déposer
│       └── context_menu.py    # Gestion du clic droit dans les entrées texte
├── tests/
│   ├── test_audit_fixes.py   # Tests unitaires pour les améliorations v1.0
│   ├── benchmark_generator.py # Mesure des performances du générateur
│   ├── benchmark_recaper.py   # Mesure des performances du recaper
│   └── test_dnd_fix.py        # Test du Glisser-Déposer
├── Main.py                    # Point d'entrée racine
└── requirements.txt           # Dépendances requises
```

---

## 🧪 Tests et Benchmarks

Pour exécuter les tests unitaires et s'assurer que les fonctionnalités sont stables :

```powershell
# Exécuter les tests unitaires
.\TF_venv\Scripts\python -m unittest tests/test_audit_fixes.py

# Exécuter les tests de performances du Générateur
.\TF_venv\Scripts\python -X utf8 tests/benchmark_generator.py

# Exécuter les tests de performances du Recaper
$env:PYTHONPATH="src"; .\TF_venv\Scripts\python -X utf8 tests/benchmark_recaper.py
```