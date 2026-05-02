"""
revers_recaper.py — Restauration de projet depuis un fichier recap .txt

Stratégie hybride :
  1. Parse la section ARBORESCENCE → reconstruit TOUS les nœuds (dossiers inclus)
  2. Parse les blocs FICHIER       → écrit le contenu texte
  3. Fusion : les nœuds de l'arbre sans contenu sont créés vides (dossiers ou fichiers)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Modèles
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StructureNode:
    rel_path: str   # ex: "zuma-clone/assets/audio"
    is_dir:   bool  # True = dossier, False = fichier

@dataclass
class ExtractResult:
    dirs_created:   list[str] = field(default_factory=list)
    files_created:  list[str] = field(default_factory=list)
    files_skipped:  list[str] = field(default_factory=list)
    errors:         list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        lines = [
            f"📁 Dossiers créés   : {len(self.dirs_created)}",
            f"✅ Fichiers créés   : {len(self.files_created)}",
            f"⏭️  Fichiers ignorés : {len(self.files_skipped)}",
        ]
        if self.errors:
            lines.append(f"❌ Erreurs          : {len(self.errors)}")
            for e in self.errors:
                lines.append(f"   • {e}")
        return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# Constantes de parsing
# ─────────────────────────────────────────────────────────────────────────────

_BLOC        = "<<TREEFORGE_FILE_BLOCK>>"
_RE_FICHIER  = re.compile(r"^FICHIER\s*:\s*(.+)$")
_RE_PROV     = re.compile(r"^PROVENANCE\s*:\s*(.+)$")

# Caractères de l'arbre Unicode à supprimer pour isoler le nom
_TREE_CHARS  = re.compile(r"^[│├└─\s]+")

# Extensions connues → si un nœud en a une, c'est un fichier
_FILE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".scss", ".sass",
    ".php", ".rb", ".go", ".rs", ".c", ".cpp", ".h",
    ".json", ".xml", ".yml", ".yaml", ".toml",
    ".ini", ".cfg", ".env",
    ".txt", ".md", ".rst", ".sql",
    ".sh", ".bat", ".ps1",
    ".gitignore", ".gitattributes", ".editorconfig",
    # Binaires connus (présents dans l'arbre mais sans contenu texte)
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".ico",
    ".mp3", ".wav", ".ogg", ".mp4",
    ".ttf", ".otf", ".woff", ".woff2",
    ".zip", ".tar", ".gz",
    ".pdf", ".exe", ".dll",
}

# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Parser la section ARBORESCENCE
# ─────────────────────────────────────────────────────────────────────────────

def _parse_arborescence(text: str) -> list[StructureNode]:
    """
    Extrait tous les nœuds (dossiers et fichiers) depuis la section ARBORESCENCE.

    Algorithme :
      - Localise la section entre "ARBORESCENCE" et "CONTENU DES FICHIERS"
      - Pour chaque ligne avec un caractère arbre (├ └ │) :
        * Calcule la profondeur via la longueur du préfixe (4 chars par niveau)
        * Détermine si c'est un fichier (a une extension) ou un dossier
        * Maintient une pile de parents pour reconstruire le chemin relatif
    """
    nodes: list[StructureNode] = []

    # ── Localiser la section arborescence ────────────────────────────────────
    lines = text.splitlines()
    start = end = -1

    for i, line in enumerate(lines):
        if "ARBORESCENCE" in line and start == -1:
            start = i
        if "CONTENU DES FICHIERS" in line and start != -1:
            end = i
            break

    if start == -1 or end == -1:
        return nodes  # Section absente → on ne plante pas

    arbo_lines = lines[start:end]

    # ── Trouver la ligne racine ───────────────────────────────────────────────
    # Format : "Structure du dossier : montest"
    root_name = None
    tree_start_idx = 0

    for i, line in enumerate(arbo_lines):
        if line.startswith("Structure du dossier :"):
            root_name = line.split(":", 1)[1].strip()
            tree_start_idx = i + 1
            break

    if root_name is None:
        return nodes

    # ── Parser les lignes d'arbre ─────────────────────────────────────────────
    # Pile : [ (depth, path_fragment) ]
    # depth = 0 → enfant direct de la racine
    path_stack: list[tuple[int, str]] = []

    for line in arbo_lines[tree_start_idx:]:
        # Ignorer les lignes vides ou sans caractère arbre
        if not line.strip():
            continue
        if not any(c in line for c in "│├└─"):
            continue

        # ── Calcul de la profondeur ───────────────────────────────────────────
        # Chaque niveau = 4 caractères ("│   " ou "    ")
        # On compte les caractères AVANT le connecteur (├── ou └──)
        raw_prefix = _TREE_CHARS.match(line)
        if not raw_prefix:
            continue

        prefix_str = raw_prefix.group(0)
        # Profondeur = nb de "    " ou "│   " dans le préfixe
        depth = len(prefix_str) // 4

        # ── Extraire le nom du nœud ───────────────────────────────────────────
        name = _TREE_CHARS.sub("", line).strip()
        if not name:
            continue

        # ── Déterminer si fichier ou dossier ──────────────────────────────────
        suffix = Path(name).suffix.lower()
        # Cas dotfiles sans extension (.gitignore, .env...)
        is_dotfile = name.startswith(".") and not suffix
        if is_dotfile:
            is_file = name.lower() in _FILE_EXTENSIONS
        else:
            is_file = bool(suffix) and suffix in _FILE_EXTENSIONS

        # Nœud sans extension connue et sans point = dossier
        is_dir = not is_file

        # ── Reconstruire le chemin relatif ────────────────────────────────────
        # Dépiler jusqu'à la profondeur actuelle
        while path_stack and path_stack[-1][0] >= depth:
            path_stack.pop()

        # Construire le chemin
        if path_stack:
            parent_path = path_stack[-1][1]
            rel_path = f"{parent_path}/{name}"
        else:
            rel_path = name

        # Empiler si dossier (peut avoir des enfants)
        if is_dir:
            path_stack.append((depth, rel_path))

        nodes.append(StructureNode(rel_path=rel_path, is_dir=is_dir))

    return nodes

# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Parser les blocs fichiers texte (inchangé)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_recap(text: str) -> list[tuple[str, str]]:
    """
    Retourne une liste de (chemin_relatif_normalisé, contenu).
    Les chemins sont normalisés avec "/" comme séparateur.
    """
    files: list[tuple[str, str]] = []
    lines = text.splitlines()
    i, n = 0, len(lines)

    while i < n:
        if lines[i].strip() != _BLOC:
            i += 1
            continue

        i += 1
        if i >= n:
            break

        m = _RE_FICHIER.match(lines[i].strip())
        if not m:
            continue

        # Normalise séparateur Windows → Unix
        rel_path = m.group(1).strip().replace("\\", "/")
        i += 1

        if i < n and _RE_PROV.match(lines[i].strip()):
            i += 1

        if i < n and lines[i].strip() == _BLOC:
            i += 1

        content_lines: list[str] = []
        while i < n and lines[i].strip() != _BLOC:
            content_lines.append(lines[i])
            i += 1

        content = "\n".join(content_lines).strip("\n")
        # Nettoie le marqueur de fichier vide
        if content.strip() == "[Ce fichier est vide]":
            content = ""

        files.append((rel_path, content))

    return files

# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Reconstruction fusionnée
# ─────────────────────────────────────────────────────────────────────────────

def extract(
    recap_path: Path,
    dest_dir:   Path,
    overwrite:      bool = True,
    create_empty:   bool = True,   # ← NOUVEAU : crée les fichiers binaires vides
) -> ExtractResult:
    """
    Reconstruction hybride depuis un recap TreeForge.

    Args:
        recap_path    : fichier recap .txt généré par recaper.py
        dest_dir      : dossier de destination
        overwrite     : si False, ignore les fichiers déjà présents
        create_empty  : si True, crée les fichiers de l'arbre sans contenu texte
                        (ex: assets/audio/theme.mp3 → fichier vide placeholder)
    """
    result  = ExtractResult()
    dest_dir = Path(dest_dir).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    # ── Lecture ──────────────────────────────────────────────────────────────
    try:
        text = recap_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        result.errors.append(f"Impossible de lire le recap : {e}")
        return result

    # ── Phase 1 : structure depuis l'arborescence ─────────────────────────────
    structure_nodes = _parse_arborescence(text)

    # Index rapide : chemins normalisés présents dans l'arbre
    arbo_dirs  = {n.rel_path for n in structure_nodes if n.is_dir}
    arbo_files = {n.rel_path for n in structure_nodes if not n.is_dir}

    # Créer tous les dossiers de l'arbre
    for rel in sorted(arbo_dirs):  # sorted → parents avant enfants
        target = _safe_resolve(dest_dir, rel)
        if target is None:
            result.errors.append(f"Chemin suspect (dossier) : {rel}")
            continue
        try:
            target.mkdir(parents=True, exist_ok=True)
            result.dirs_created.append(str(target))
        except Exception as e:
            result.errors.append(f"Impossible de créer {rel} : {e}")

    # ── Phase 2 : fichiers texte depuis les blocs ─────────────────────────────
    entries = _parse_recap(text)

    # Index pour la phase 3 : quels fichiers ont déjà un contenu écrit
    written: set[str] = set()

    for rel_path_str, content in entries:
        target = _safe_resolve(dest_dir, rel_path_str)
        if target is None:
            result.errors.append(f"Chemin suspect ignoré : {rel_path_str}")
            continue

        if target.exists() and not overwrite:
            result.files_skipped.append(str(target))
            continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            result.files_created.append(str(target))
            written.add(rel_path_str)
        except Exception as e:
            result.errors.append(f"Erreur écriture {rel_path_str} : {e}")

    # ── Phase 3 : fichiers de l'arbre sans contenu texte ─────────────────────
    if create_empty:
        for rel in arbo_files:
            if rel in written:
                continue  # Déjà écrit en phase 2

            target = _safe_resolve(dest_dir, rel)
            if target is None:
                continue

            if target.exists() and not overwrite:
                result.files_skipped.append(str(target))
                continue

            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch()  # Fichier vide — placeholder binaire
                result.files_created.append(str(target))
            except Exception as e:
                result.errors.append(f"Erreur création placeholder {rel} : {e}")

    return result

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_resolve(dest_dir: Path, rel_path: str) -> Path | None:
    """
    Résout un chemin relatif dans dest_dir.
    Retourne None si le chemin tente un path traversal.
    """
    rel_path = rel_path.replace("\\", "/")
    try:
        target = (dest_dir / rel_path).resolve()
        target.relative_to(dest_dir)  # ValueError si hors dest
        return target
    except ValueError:
        return None
    except Exception:
        return None
