"""
Parser d'arborescences textuelles pour TreeForge.

Supporte les formats :
  - unicode  : ├── └── │   (ChatGPT, Claude, arbres standard)
  - wintree  : ├─── └─── │   fichier.py   (Windows tree /f)
  - indent   : indentation pure espaces/tabulations
  - json     : { name, children[], content? }

3 modes : Strict / Souple / Confiant

Nouveauté : détection automatique d'un chemin absolu en première ligne
(sortie Gemini, `tree /f`, etc.) — signalé via ROOT_PATH_DETECTED dans
les warnings pour confirmation UI.
"""
from __future__ import annotations
import json
import re

from treeforge.core.models import TreeNode, ParseResult

# ── Regex ─────────────────────────────────────────────────────────────────────

# Caractères box-drawing à consommer en préfixe
_BOX_RE = re.compile(r"^[│├└─\s]+")

# Détection chemin absolu Windows / UNC / Unix
_WIN_ABS_RE  = re.compile(r'^[A-Za-z]:[/\\]')
_UNC_RE      = re.compile(r'^\\\\')
_UNIX_ABS_RE = re.compile(r'^/[a-zA-Z]')

# Annotations à supprimer en fin de nom
# Couvre : ✅ ⚠️ ❓ 🔜 📁 📄 + texte qui suit 2 espaces ou plus
_ANNOTATION_RE = re.compile(
    r'\s{2,}.*$'                        # 2+ espaces puis n'importe quoi
    r'|'
    r'\s*[✅⚠️❓🔜📁📄✔️🚫🟡🟢🔴]\s*.*$'  # emoji connu + suite
)

# ── Nettoyage du nom ──────────────────────────────────────────────────────────

def _clean_name(raw: str) -> str:
    """
    Retire les annotations en fin de nom de nœud.
    
    Exemples :
      "parser.py    ✅ complet"   → "parser.py"
      "revers_recaper.py  ⚠️ vide" → "revers_recaper.py"
      "main_window.py  ❓ inconnu" → "main_window.py"
      "src/treeforge/"             → "src/treeforge/"  (inchangé)
    """
    cleaned = _ANNOTATION_RE.sub("", raw)
    return cleaned.strip()

# ── Détection de format ───────────────────────────────────────────────────────

def _detect_format(lines: list[str]) -> str:
    sample = [l for l in lines if l.strip()][:20]

    wintree_score = 0
    unicode_score = 0
    indent_score  = 0

    for line in sample:
        # Marqueur fort wintree : ├─── ou └─── (3 tirets ou plus)
        if re.search(r'[├└]─{3,}', line):
            wintree_score += 3

        # Marqueur wintree : │ + 3 espaces + NOM DIRECT (pas ├└─)
        elif re.match(r'^│\s{3,}[^├└─\s]', line):
            wintree_score += 2

        # Marqueur unicode : ├── ou └── (2 tirets)
        elif re.search(r'[├└]──[\s/]', line) or re.search(r'[├└]──$', line):
            unicode_score += 2

        # Marqueur unicode : │ suivi de ├ ou └ (sous-niveau imbriqué)
        elif re.match(r'^│\s+[├└]', line):
            unicode_score += 2

        # Indentation pure
        elif re.match(r'^[ \t]+\S', line) and not re.search(r'[│├└─]', line):
            indent_score += 1

    scores = {
        "wintree" : wintree_score,
        "unicode" : unicode_score,
        "indent"  : indent_score,
    }

    detected = max(scores, key=lambda k: scores[k])

    if scores[detected] == 0:
        detected = "unicode"

    return detected

# ── Calcul de profondeur selon le format ──────────────────────────────────────

def _strip_prefix(line: str, fmt: str) -> tuple[int, str]:
    """
    Retourne (profondeur, nom_nettoyé) selon le format.

    Format unicode :
        "│   ├── fichier.py"  → profondeur = nombre de │ + ├/└
        Chaque │ ou ├/└ = +1 niveau

    Format wintree :
        "│       fichier.py"  → profondeur par blocs de 4 espaces après │
        "├───dossier"         → profondeur par position du ├/└

    Format indent :
        "    fichier.py"      → profondeur par nb d'espaces ÷ 2 (ou tabs)
    """

    if fmt == "unicode":
        # Compter les caractères de structure avant le nom
        match = _BOX_RE.match(line)
        if match:
            prefix = match.group(0)
            # Profondeur = nb de │ + nb de ├ ou └
            # depth = prefix.count("│") + prefix.count("├") + prefix.count("└")
            
            # patch ci dessous
            # Trouve la position du premier connecteur ├ ou └
            connector_pos = next((i for i, ch in enumerate(prefix) if ch in "├└"), len(prefix))
            indent_prefix = prefix[:connector_pos]   # la partie avant le connecteur
            depth = (len(indent_prefix) // 4) + 1    # nombre de blocs de 4 + 1
            name  = line[match.end():].strip()
        else:
            # Pas de box-drawing → indentation simple
            depth = (len(line) - len(line.lstrip())) // 2
            name  = line.strip()

    elif fmt == "wintree":
        match = _BOX_RE.match(line)
        if match:
            prefix = match.group(0)
            if re.search(r'[├└]', prefix):
                # Ligne avec connecteur ├─── ou └───
                # Profondeur = nb de │ avant le connecteur
                depth = prefix.count("│")
            else:
                # Ligne │   fichier.py — profondeur par blocs d'espaces
                # Chaque niveau = 4 espaces dans tree /f
                spaces_after_pipe = len(prefix.rstrip()) 
                depth = max(1, spaces_after_pipe // 4)
            name = line[match.end():].strip().lstrip("─").strip()
        else:
            depth = 0
            name  = line.strip()

    else:  # indent
        raw_indent = len(line) - len(line.lstrip())
        # Support tabs (1 tab = 1 niveau) ou espaces (2 ou 4 espaces = 1 niveau)
        if "\t" in line[:raw_indent]:
            depth = line[:raw_indent].count("\t")
        else:
            # Détecte automatiquement si indentation = 2 ou 4 espaces
            depth = raw_indent // 2
        name = line.strip()

    # Nettoyage final du nom
    name = _clean_name(name)
    # Retirer commentaires Python éventuels
    name = name.split("#")[0].strip()

    return depth, name

# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_dir(name: str) -> bool:
    """Un nœud est un dossier s'il n'a pas d'extension ou se termine par /."""
    if name.endswith("/") or name.endswith("\\"):
        return True
    return "." not in name.split("/")[-1]

# ── Détection chemin absolu en première ligne ─────────────────────────────────

def _is_absolute_path_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _WIN_ABS_RE.match(stripped):
        return True
    if _UNC_RE.match(stripped):
        return True
    if _UNIX_ABS_RE.match(stripped):
        return True
    return False

def _strip_root_path_line(lines: list[str]) -> tuple[list[str], str | None]:
    """
    Si la première ligne non vide est un chemin absolu, la retire.
    Retourne (lignes_restantes, chemin_détecté | None).
    """
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if _is_absolute_path_line(line):
            return lines[i + 1:], line.strip()
        break
    return lines, None

# ── Parser texte ──────────────────────────────────────────────────────────────

def _parse_text(lines: list[str], mode: str, fmt: str) -> ParseResult:
    result = ParseResult()
    stack:  list[tuple[int, TreeNode]] = []
    roots:  list[TreeNode] = []

    for lineno, raw in enumerate(lines, 1):
        if not raw.strip():
            continue

        depth, name = _strip_prefix(raw, fmt)
        print(f"L{lineno:02} depth={depth} name={repr(name)}")
        if not name:
            continue

        is_dir = _is_dir(name)
        name   = name.rstrip("/\\")
        if not name:
            continue

        node = TreeNode(name=name, is_dir=is_dir, depth=depth)

        # Trouver le bon parent
        while stack and stack[-1][0] >= depth:
            stack.pop()

        if not stack:
            roots.append(node)
        else:
            parent = stack[-1][1]
            if not parent.is_dir:
                if mode == "🔒 Strict":
                    result.errors.append(
                        f"Ligne {lineno} : « {name} » est enfant de "
                        f"« {parent.name} » qui est un fichier."
                    )
                    return result
                else:
                    result.warnings.append(
                        f"Ligne {lineno} : « {parent.name} » converti en "
                        f"dossier (enfants détectés)."
                    )
                    parent.is_dir = True
            parent.children.append(node)

        stack.append((depth, node))

    result.nodes = roots
    return result

# ── Parser JSON ───────────────────────────────────────────────────────────────

def _node_from_json(obj: dict, depth: int = 0) -> TreeNode:
    name         = obj.get("name", "unnamed")
    children_raw = obj.get("children", [])
    content      = obj.get("content", "")
    is_dir       = bool(children_raw) or obj.get("is_dir", _is_dir(name))
    node = TreeNode(name=name, is_dir=is_dir, content=content, depth=depth)
    for child in children_raw:
        node.children.append(_node_from_json(child, depth + 1))
    return node

def _parse_json(text: str, mode: str) -> ParseResult:
    result = ParseResult()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        result.errors.append(f"JSON invalide : {e}")
        return result

    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        result.errors.append("Le JSON doit être un objet ou un tableau d'objets.")
        return result

    for obj in data:
        result.nodes.append(_node_from_json(obj))
    return result

# ── Point d'entrée public ─────────────────────────────────────────────────────

def parse(text: str, mode: str = "🔧 Souple", fmt: str = "auto") -> ParseResult:
    """
    Parse le texte en entrée et retourne un ParseResult.

    :param text: arborescence texte ou JSON
    :param mode: "🔒 Strict" | "🔧 Souple" | "⚡ Confiant"
    :param fmt:  "auto" | "unicode" | "wintree" | "indent"

    Notes :
      - Si fmt="auto" : _detect_format() choisit pour toi et ajoute
        un warning FORMAT_DETECTED:<fmt> pour feedback UI.
      - Les annotations (✅ ⚠️ ❓) sont toujours supprimées.
      - ROOT_PATH_DETECTED:<chemin> reste signalé si chemin absolu détecté.
    """
    text = text.strip()
    if not text:
        r = ParseResult()
        r.errors.append("Aucun texte à analyser.")
        return r

    # Détection auto JSON
    if text.startswith("{") or text.startswith("["):
        return _parse_json(text, mode)

    lines = text.splitlines()

    # ── Détection chemin absolu en première ligne ──────────────────────────
    lines, detected_path = _strip_root_path_line(lines)

    # ── Détection / validation du format ──────────────────────────────────
    auto_detected = False
    if fmt == "auto":
        fmt = _detect_format(lines)
        auto_detected = True

    result = _parse_text(lines, mode, fmt)

    # ── Warnings de feedback UI ────────────────────────────────────────────
    if detected_path:
        result.warnings.insert(0, f"ROOT_PATH_DETECTED:{detected_path}")

    if auto_detected:
        # Intercepté par generator_tab pour afficher "Format détecté : Unicode ├──"
        result.warnings.insert(0, f"FORMAT_DETECTED:{fmt}")

    return result
