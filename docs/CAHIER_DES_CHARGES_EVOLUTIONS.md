# Cahier des charges — Évolutions TreeForge

**Statut** : brouillon de travail
**Périmètre exclu** : intégration API (OpenAI/Anthropic) — décision assumée de rester 100% copier-coller, hors périmètre de ce document.

---

## Vue d'ensemble et priorisation

| # | Chantier | Priorité | Effort estimé | Dépend de |
|---|----------|----------|----------------|-----------|
| 0 | Nettoyage des versions | P0 | XS | — |
| 1 | Protection anti-écrasement + diff avant application | P0 | M | #0 |
| 2 | Mode presse-papiers (copier/coller) | P0 | S | — |
| 3 | Recap sélectif (choix des fichiers) | P1 | S | — |
| 4 | Recap incrémental (git-aware) | P1 | M | #3 |
| 5 | Internationalisation FR/EN/YO | P2 | M/L (traduction + validation yoruba) | — |
| 6 | Galerie de templates communautaires | P3 | L | — |
| 7 | Extension VSCode | P3 | XL | #2, #1 |

Ordre recommandé : 0 → 1 → 2 → 3 → 4 → 5 → (6 et 7 en parallèle, projets à part entière).

---

## 0. Nettoyage des versions (prérequis)

### Problème
Incohérence entre `pyproject.toml` (`1.0.0`), `config.py` (`__version__ = "1.0.0"`), `main_window.py` (`APP_VERSION = "3.0.0"`), `settings_dialog.py` (sa propre constante `APP_VERSION = "1.0.0"` en dur, ligne 14, affichée dans la section "À propos"), le nom du dossier (`v4.0.0`) et le README (chemin `C:/Users/darec/...` obsolète).

### Objectif
Une seule source de vérité pour la version.

### Spécifications
- `config.py::__version__` devient la seule source de vérité.
- `main_window.py` importe `APP_VERSION` depuis `treeforge.config` au lieu de le redéfinir en dur.
- `pyproject.toml::version` synchronisé manuellement à chaque release (ou script de bump si outillage CI ajouté plus tard).
- README : corriger les chemins et exemples obsolètes, remettre le numéro de version affiché en cohérence.

### Critères d'acceptation
- `grep` de tout numéro de version en dur dans `src/` ne renvoie qu'un seul résultat (`config.py`).
- Le titre de la fenêtre affiche la même version que `pyproject.toml`.

---

## 1. Protection anti-écrasement + diff avant application

### Problème actuel
- `generator.py::generate()` écrit avec `write_text()` sans vérifier l'existence préalable ni prévenir l'utilisateur.
- `revers_recaper.py::extract()` a un flag `overwrite` mais aucune UI ne montre *ce qui va changer* avant de l'appliquer.

### Objectif
Transformer la génération/restauration en opération prévisible : l'utilisateur voit ce qui va être créé/modifié/supprimé avant de confirmer, sur les deux flux (Générer et Restaurer).

### Spécifications fonctionnelles
- Avant toute écriture sur un dossier destination non vide, calculer et afficher trois listes :
  - **Nouveaux** : fichiers/dossiers qui n'existent pas encore.
  - **Modifiés** : fichiers existants dont le contenu différerait (comparaison de contenu, pas juste de nom).
  - **Inchangés** : fichiers existants identiques (informatif, non bloquant).
- Aucune suppression automatique de fichiers absents de l'arbo source — TreeForge n'efface jamais un fichier que l'utilisateur n'a pas explicitement demandé de supprimer (pas de mode "miroir" destructif par défaut).
- Pour les fichiers "Modifiés", un aperçu diff textuel (unifié, type `difflib.unified_diff`) consultable en un clic.
- Bouton de confirmation explicite avant écriture réelle ; possibilité de décocher des fichiers individuels dans la liste "Modifiés"/"Nouveaux" pour les exclure de l'application (réutilise le pattern d'exclusion déjà existant dans `preview_tree.py`).

### Spécifications techniques
- Nouveau module `core/diff_engine.py` :
  - `compute_plan(parse_result, destination) -> GenerationPlan` pour le flux Générer.
  - `compute_plan(structure_nodes, entries, destination) -> GenerationPlan` pour le flux Restaurer (réutilise les structures déjà extraites par `revers_recaper._parse_arborescence` / `_parse_recap`).
  - `GenerationPlan` : dataclass avec `new: list[PlanItem]`, `modified: list[PlanItem]`, `unchanged: list[PlanItem]`.
  - `PlanItem` : `path`, `is_dir`, `old_content | None`, `new_content`.
- Nouveau composant GUI `gui/components/diff_preview_modal.py`, réutilisable par `generator_tab.py` et `revers_recaper_tab.py`.
- `generator.py::generate()` et `revers_recaper.py::extract()` acceptent un paramètre optionnel `plan: GenerationPlan | None` — si fourni, n'écrit que les items non désélectionnés par l'utilisateur.
- Comparaison de contenu texte uniquement (les binaires/placeholders restent "nouveau" ou "inchangé" par taille/existence, pas de diff binaire).

### Critères d'acceptation
- Générer sur un dossier contenant déjà des fichiers ne modifie plus aucun fichier sans passage par l'écran de confirmation.
- Un fichier décoché dans le plan n'est pas touché sur le disque.
- Le diff affiché correspond exactement au contenu qui sera écrit.

---

## 2. Mode presse-papiers (copier/coller)

### Problème actuel
Le cycle Recaper/Restaurer passe obligatoirement par un fichier `.txt` sur disque, ce qui ajoute des allers-retours (sauvegarder, retrouver le fichier, le rouvrir) dans une boucle de travail qui se fait en réalité contre une fenêtre de chat.

### Objectif
Permettre un cycle complet copier-coller sans jamais toucher le système de fichiers pour le fichier recap intermédiaire.

### Spécifications fonctionnelles
- Onglet **Recaper** : bouton "📋 Copier dans le presse-papiers" en plus de "Générer le fichier .txt" (les deux options coexistent, l'export fichier reste disponible pour l'archivage).
- Onglet **Restaurer** : bouton "📋 Coller depuis le presse-papiers" qui pré-remplit la zone de saisie existante (ou en crée une si le flux actuel ne part que d'un fichier) et lance l'analyse.
- Onglet **Générer** : le champ de saisie de l'arborescence texte a déjà probablement un collage standard (Ctrl+V) — vérifier/documenter que ça fonctionne, pas de développement si déjà supporté.

### Spécifications techniques
- Utiliser l'API presse-papiers native de Tkinter (`clipboard_clear()` / `clipboard_append()` / `clipboard_get()`), déjà accessible via `self.clipboard_*()` sur n'importe quel widget CTk — pas de nouvelle dépendance nécessaire.
- `recaper_tab.py` : après génération, proposer un choix ou deux boutons distincts (fichier vs presse-papiers) plutôt qu'un flux à étapes.
- `revers_recaper_tab.py` : bouton presse-papiers qui appelle `clipboard_get()`, gère l'absence de contenu (`TclError` si presse-papiers vide) avec un message utilisateur clair.

### Critères d'acceptation
- Un cycle complet (recap → coller dans un chat → copier la réponse → restaurer) est réalisable sans jamais sauvegarder de fichier `.txt` intermédiaire.
- Message d'erreur clair si le presse-papiers est vide ou ne contient pas un recap valide (réutilise la détection de section `ARBORESCENCE` déjà présente dans le parser).

---

## 3. Recap sélectif (choix des fichiers à inclure)

### Problème actuel
`recap()` inclut systématiquement tous les fichiers texte non exclus par `DEFAULT_EXCLUDE_DIRS` — pas de contrôle fin par l'utilisateur avant génération.

### Objectif
Donner à l'utilisateur le même niveau de contrôle sur l'export (Recaper) que sur la génération (`preview_tree.py` le permet déjà côté Générer, avec exclusion par Espace/clic droit).

### Spécifications fonctionnelles
- Avant de lancer `recap()`, afficher un arbre interactif du dossier source (même composant que `preview_tree.py`, adapté en lecture du disque réel plutôt que d'un `ParseResult`).
- Chaque fichier/dossier peut être exclu individuellement (Espace / clic droit / case à cocher).
- Les exclusions par défaut (`DEFAULT_EXCLUDE_DIRS`) restent pré-décochées mais visibles et modifiables ponctuellement (sans changer la config globale).
- Indicateur de taille estimée du recap final (nombre de fichiers, taille en Ko/tokens approximatifs) pour aider à rester sous une limite de contexte IA.

### Spécifications techniques
- Nouvelle fonction `core/recaper.py::scan_tree(root, exclude_dirs) -> TreeNode` qui construit un `TreeNode` (réutilise le modèle existant de `models.py`) à partir du disque, avec le champ `excluded` déjà présent dans `TreeNode`.
- `recap()` accepte un paramètre `include_paths: set[str] | None` — si fourni, ne traite que ces chemins relatifs (sinon comportement actuel inchangé, rétrocompatible).
- `recaper_tab.py` : ajout d'un écran de prévisualisation avant génération (miroir du `preview_modal.py` côté Générer).
- Estimation de taille : `len(content) // 4` comme proxy simple de comptage de tokens (heuristique, pas de dépendance à un tokenizer réel).

### Critères d'acceptation
- Un fichier décoché dans l'arbre n'apparaît ni dans l'arborescence ni dans le contenu du recap généré.
- Le compteur de taille estimée se met à jour en direct quand on coche/décoche.

---

## 4. Recap incrémental (git-aware)

### Problème actuel
Sur un projet réel de taille moyenne à grande, le recap complet dépasse rapidement la fenêtre de contexte d'un chat IA. Aucune notion de "ce qui a changé depuis la dernière fois".

### Objectif
Permettre de ne recaper que les fichiers modifiés depuis un point de référence (dernier commit, dernier recap, ou plage de commits), pour des itérations de revue ciblées.

### Spécifications fonctionnelles
- Dans l'onglet Recaper, si le dossier source est un dépôt git, proposer un mode "Modifications uniquement" avec un sélecteur :
  - Depuis le dernier commit (`git diff --name-only HEAD`).
  - Fichiers non trackés + modifiés (`git status --porcelain`).
  - Depuis une référence choisie (branche/commit, saisie libre).
- Le mode par défaut reste "Projet complet" — le mode incrémental est une option, pas un remplacement.
- Si le dossier n'est pas un dépôt git, l'option est simplement grisée/masquée (pas d'erreur bloquante).

### Spécifications techniques
- `GitPython` est déjà une dépendance du projet (`requirements.txt`) — l'utiliser plutôt que de spawn `git` en subprocess.
- Nouvelle fonction `core/recaper.py::git_changed_files(root, ref="HEAD") -> set[str] | None` — retourne `None` si le dossier n'est pas un repo git (détection via `git.Repo(root, search_parent_directories=False)` avec catch de `InvalidGitRepositoryError`).
- Combine avec le paramètre `include_paths` introduit au chantier #3 : le mode git-aware pré-coche les fichiers modifiés dans l'arbre de sélection plutôt que de contourner l'UI de sélection.
- Le fichier recap généré en mode incrémental porte une mention explicite dans son en-tête (`MODE : Incrémental depuis <ref>`) pour que l'IA et l'utilisateur sachent que ce n'est pas le projet complet — évite les restaurations accidentelles qui videraient le reste du projet en mode `ReversRecaper` (le chantier #1 protège déjà contre ça, mais la mention reste utile en documentation du fichier lui-même).

### Critères d'acceptation
- Sur un repo avec 3 fichiers modifiés et 200 fichiers inchangés, le mode incrémental ne recape que les 3 fichiers modifiés.
- Sur un dossier non-git, aucune erreur, l'option est simplement indisponible.

---

## 5. Internationalisation (FR/EN/YO)

### Problème actuel
Toute l'UI, les 9 prompts IA et les messages sont écrits en dur en français dans le code (`main_window.py`, tous les fichiers `gui/tabs/*.py`, `prompts.json`). Ferme de facto l'accès au public anglophone et aux locuteurs yoruba, alors que le yoruba (~45M de locuteurs, Nigéria/Bénin/Togo) est une cible explicite du projet.

### Objectif
Ajouter un mode anglais **et un mode yoruba** sélectionnables, sans réécrire l'architecture existante. Le yoruba est traité comme langue de première classe, pas comme un ajout accessoire — mêmes critères de qualité que le français et l'anglais.

### Spécifications fonctionnelles
- **État actuel (vérifié dans le code) : aucun sélecteur de langue n'existe.** `settings_dialog.py` ne contient qu'un menu de thème (Sombre/Clair/Système) dans la section "Apparence" — à construire entièrement.
- Sélecteur de langue dans les Paramètres (`settings_dialog.py`), dans la même section "Apparence", juste sous le menu de thème existant : **Français / English / Yorùbá**.
- Persisté dans les préférences utilisateur existantes (`load_prefs()`/`user_prefs.json`, déjà utilisé pour le thème).

### Implémentation concrète dans `settings_dialog.py`

Le sélecteur de thème donne déjà le patron exact à reproduire (même fichier, lignes ~91-110) :

```python
self._theme_map = {"Sombre": "dark", "Clair": "light", "Système": "system"}
self._theme_reverse_map = {v: k for k, v in self._theme_map.items()}
self._theme_var = ctk.StringVar(value=initial_value)
self._theme_menu = ctk.CTkOptionMenu(scroll, values=["Sombre", "Clair", "Système"],
                                       variable=self._theme_var, command=self._on_theme_change, ...)
```

À dupliquer à l'identique pour la langue, juste après le bloc thème (avant le switch "Astuces rotatives") :
- `self._lang_map = {"Français": "fr", "English": "en", "Yorùbá": "yo"}` + `self._lang_reverse_map`.
- `self._lang_var` + `self._lang_menu` (`CTkOptionMenu`), valeur initiale lue depuis `self._prefs.get("language", "fr")`.
- `_on_language_change(self, val)` : écrit `self._prefs["language"] = self._lang_map[val]`, appelle `save_prefs(self._prefs)`, puis déclenche le rechargement des `t()` (module `utils/i18n.py`) et `self.master.refresh_settings()` (le hook existe déjà — `MainWindow.refresh_settings()` est appelé automatiquement à la fermeture du dialogue via `destroy()`, ligne 39-44).
- Ajouter `"language": "fr"` à `DEFAULT_PREFS` (`utils/helpers.py`) pour que `_reset_factory()` (ligne 348) le réinitialise correctement, comme il le fait déjà pour `theme`.
- Corriger au passage la constante `APP_VERSION = "1.0.0"` en dur (ligne 14) pour qu'elle importe `treeforge.config.__version__` — cf. chantier #0, c'est le quatrième endroit où la version est dupliquée en dur.
- Couvre : tous les libellés d'UI (boutons, onglets, messages de statut/log), et une version des 9 prompts IA de `prompts.json` dans les trois langues.
- Redémarrage non requis pour le changement de langue si raisonnablement faisable ; sinon message "redémarrage nécessaire" (cohérent avec le comportement actuel du thème, à vérifier).

### Spécifications techniques
- Externaliser les chaînes d'UI dans des fichiers de ressources par langue : `resources/i18n/fr.json`, `resources/i18n/en.json`, `resources/i18n/yo.json` (clé → texte), sur le modèle déjà utilisé pour `prompts.json`/`tips.json`.
- `prompts.json` restructuré par langue : trois fichiers (`prompts_fr.json`, `prompts_en.json`, `prompts_yo.json`) plutôt qu'une clé `lang` imbriquée — cohérent avec le pattern JSON existant du projet et plus simple à confier à un traducteur externe fichier par fichier.
- Nouveau module `utils/i18n.py` : fonction `t(key: str) -> str` chargeant le bon fichier selon la préférence utilisateur, avec **repli en cascade langue choisie → français** si une clé manque (jamais de crash ni de clé brute affichée pour une traduction incomplète — utile en particulier pour un déploiement progressif du yoruba, traduit petit à petit).
- Remplacement progressif des chaînes en dur dans les fichiers `gui/` par des appels à `t("clé")` — chantier mécanique mais volumineux, à faire fichier par fichier.

### Spécification spécifique au yoruba — rendu des caractères

Le yoruba en écriture latine utilise des lettres à sous-point (ẹ, ọ, ṣ — Unicode Latin Extended Additional / précomposé) combinées à des marques de ton (accent aigu = ton haut, grave = ton bas, absence de marque = ton moyen), parfois cumulées sur une même lettre (ọ́, ẹ̀). Pas d'écriture RTL, pas de liaison de glyphes (contrairement à l'arabe ou aux scripts indiens) — donc pas de complexité de moteur de rendu type Harfbuzz nécessaire, seulement une question de **couverture de police**.

- Étape de validation avant tout développement : tester le rendu de ces caractères avec la police par défaut de CustomTkinter (généralement une police système Windows type Segoe UI) — sous-points et tons combinés doivent s'afficher correctement, sans glyphe manquant (☐) ni chevauchement.
- Si la couverture système n'est pas fiable sur toutes les machines cibles : bundler une police libre couvrant le yoruba (ex. **Noto Sans**, couverture Unicode confirmée pour le yoruba) dans `resources/fonts/` et la charger explicitement via `ctk.CTkFont(family=...)` quand la langue active est le yoruba — indépendant de ce qui est installé sur le poste utilisateur.
- Normalisation Unicode : stocker les fichiers `yo.json` en NFC (forme composée) pour éviter les incohérences d'affichage entre caractères précomposés et combinaisons base+diacritique équivalentes visuellement mais différentes en octets.

### Spécification spécifique au yoruba — qualité de traduction

Risque distinct de la simple UI : les 9 prompts IA contiennent des **instructions impératives destinées au modèle** ("Réponds UNIQUEMENT avec l'arborescence, sans explication ni commentaire"). Une traduction mécanique ou approximative de ces consignes peut changer le comportement du LLM en sortie et casser le parseur en aval (`core/parser.py`), silencieusement.

- Traduction des prompts IA (et idéalement de toute l'UI) relue par un locuteur natif yoruba avant intégration — pas de mise en production d'une traduction non relue pour cette section précise.
- Tester chaque prompt yoruba traduit contre un vrai modèle (ChatGPT/Claude/Gemini) pour vérifier que la sortie reste bien une arborescence parsable dans le format attendu, avant de le livrer — critère de recette, pas juste de traduction.
- Le repli en cascade vers le français (voir specs techniques ci-dessus) permet de livrer l'UI générale en yoruba avant que les 9 prompts soient validés, sans bloquer l'un sur l'autre.

### Critères d'acceptation
- Basculer la langue dans les Paramètres (FR/EN/YO) change tous les libellés visibles (onglets, boutons, statuts) et la liste de prompts proposée.
- Les caractères ẹ, ọ, ṣ et leurs combinaisons avec marques de ton s'affichent correctement dans l'UI, sans glyphe manquant, sur une installation Windows standard non modifiée.
- Une clé de traduction manquante en yoruba affiche le texte français (jamais une erreur ni une clé brute type `missing_key`).
- Chaque prompt IA yoruba a été testé contre au moins un LLM réel et produit une sortie parsable par `core/parser.py`.

---

## 6. Galerie de templates communautaires

### Problème actuel
Les templates (`resources/templates/*.json`) sont figés dans l'application — ajouter un template nécessite d'éditer le code source et de reconstruire l'exécutable.

### Objectif
Permettre à un utilisateur d'importer un template tiers sans mise à jour de l'application, et de partager les siens.

### Spécifications fonctionnelles
- Dans l'onglet Templates, bouton "Importer un template" acceptant :
  - Un fichier JSON local (déjà trivial, `Path.read_text` + validation du schéma).
  - Une URL directe vers un JSON brut (ex. lien "raw" GitHub Gist).
- Validation du template importé avant ajout : structure conforme au schéma attendu par `template_manager.py::_node_from_json` (champs `name`, `children`, `content` optionnel), rejet avec message clair si invalide.
- Les templates importés sont stockés dans un dossier utilisateur séparé (`~/.treeforge/templates/`), distinct de `resources/templates/` (qui reste réservé aux templates officiels livrés avec l'app) — évite tout conflit lors des mises à jour de l'application.
- `template_manager.py::list_templates()` fusionne les deux sources, avec un marqueur visuel (ex. badge "communautaire") pour distinguer templates officiels et importés.

### Spécifications techniques
- Téléchargement d'URL : utiliser `urllib.request` (stdlib, déjà pas de nouvelle dépendance) avec timeout explicite et limite de taille (ex. 1 Mo max) pour éviter tout téléchargement abusif.
- **Sécurité** : un template JSON ne contient que de la structure + du contenu texte statique (pas de code exécuté à l'import) — le risque est limité, mais valider strictement le schéma avant tout `json.loads` → `_node_from_json` pour éviter qu'un JSON malformé ne fasse planter l'app.
- Pas d'hébergement d'une "galerie" centralisée dans un premier temps (hors périmètre — ça impliquerait un backend) : le partage se fait via gist/URL fournie par l'utilisateur lui-même. Une galerie centralisée hébergée est un chantier ultérieur distinct, à ne considérer que si l'usage de l'import URL décolle.

### Critères d'acceptation
- Importer un JSON valide depuis un lien Gist raw l'ajoute à la liste des templates disponibles sans redémarrage.
- Un JSON malformé ou une URL injoignable affiche un message d'erreur explicite, sans crash de l'application.

---

## 7. Extension VSCode

### Problème actuel
TreeForge est une application desktop séparée — un utilisateur qui travaille déjà dans VSCode doit changer de fenêtre pour recaper/restaurer.

### Objectif
Offrir le cycle Recap/Restore directement dans VSCode via la palette de commandes, pour l'audience de développeurs (par opposition à l'audience non-technique qui reste mieux servie par l'app desktop).

### Spécifications fonctionnelles
- Commandes de palette :
  - `TreeForge: Recap workspace to clipboard` — équivalent du chantier #2/#3 côté VSCode, avec sélection de fichiers via la vue Explorer (clic droit → "Exclude from recap" ou coche dans un QuickPick multi-select).
  - `TreeForge: Apply recap from clipboard` — équivalent restauration, avec le même écran de diff que le chantier #1 (adapté en `vscode.diff` natif, VSCode a déjà un viewer de diff intégré — pas besoin de le redévelopper).
- Pas de duplication de logique : l'extension doit consommer le même moteur que l'app desktop.

### Spécifications techniques
- **Prérequis architectural** : extraire la logique métier pure (`core/recaper.py`, `core/revers_recaper.py`, `core/parser.py`, `core/diff_engine.py` du chantier #1) dans un package Python autonome sans dépendance GUI, publiable indépendamment — c'est déjà globalement le cas (le dossier `core/` n'importe pas `customtkinter`), à vérifier et durcir.
- Deux options d'implémentation, à trancher explicitement avant de démarrer (impact fort sur l'effort) :
  1. **Extension TypeScript pure** qui réimplémente le parsing/diff en JS/TS — duplique la logique, risque de divergence entre les deux implémentations, mais zéro dépendance runtime Python côté utilisateur VSCode.
  2. **Extension TypeScript fine + backend Python local** (le `core/` existant exposé en CLI ou via un petit serveur local) — réutilise le moteur existant tel quel, mais impose que Python soit installé sur la machine de l'utilisateur VSCode (déjà probable pour un dev, mais pas garanti pour tous types de projets).
- Recommandation : option 2, avec une commande CLI (`python -m treeforge.core.recaper` existe déjà comme point de départ) invoquée en sous-processus par l'extension — évite la duplication de logique métier, cohérent avec le CLI standalone déjà présent dans `recaper.py`.
- Publication : `vsce package` / Marketplace VSCode, projet et dépôt séparés du repo desktop principal.

### Critères d'acceptation
- Le recap généré depuis VSCode est byte-identique à celui généré depuis l'app desktop sur le même dossier.
- Aucune logique de parsing/diff n'est dupliquée entre les deux (l'extension appelle le même moteur `core/`).

### Note
Chantier le plus lourd du lot (nouveau projet, nouvelle stack TS, packaging/publication séparés) — à ne lancer qu'une fois les chantiers #1, #2 et #3 stabilisés côté desktop, puisque l'extension en dépend directement.

---

## Hors périmètre (rappel)

- Intégration API IA directe (OpenAI/Anthropic) — écarté explicitement, positionnement du produit reste 100% copier-coller / sans accès réseau au code de l'utilisateur.
- Galerie communautaire centralisée hébergée (backend dédié) — évoqué comme extension possible du chantier #6, non spécifié ici.
- Portage multi-plateforme (macOS/Linux) — non demandé, application actuellement pensée et brandée "Windows".
