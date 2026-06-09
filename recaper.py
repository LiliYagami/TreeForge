import os
from datetime import datetime

# Extensions que tu veux "copier" dans le recap (fichiers texte / code)
TEXT_EXTENSIONS = {
    # Langages principaux
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".scss", ".sass",
    ".php", ".rb", ".go", ".rs", ".c", ".cpp", ".h",
    # Config / Data
    ".json", ".xml", ".yml", ".yaml", ".toml",
    ".ini", ".cfg", ".env",
    # Docs
    ".txt", ".md", ".rst",
    # SQL
    ".sql",
    # Scripts
    ".sh", ".bat", ".ps1",
    # Git
    ".gitignore", ".gitattributes",
}

# Dossiers à ignorer (tu peux ajouter node_modules, .git, dist, etc.)

IGNORE_DIRS = {
    "recaps",
    ".git",
    "node_modules",
    "__pycache__",
    "build",
    "dist",
    "TForge_ENV",
    "TForge_ENV_py312",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
}

def build_tree(root_path: str) -> str:
    """
    Construit une arborescence style `tree /f` (version simple)
    """
    lines = []
    root_name = os.path.basename(os.path.abspath(root_path))
    lines.append(f"Structure du dossier : {root_name}")
    lines.append("")

    def walk(dir_path, prefix=""):
        try:
            entries = sorted(os.listdir(dir_path))
        except PermissionError:
            lines.append(prefix + "└── [Permission Denied]")
            return

        # filtrer dossiers ignorés
        filtered = []
        for e in entries:
            full = os.path.join(dir_path, e)
            if os.path.isdir(full) and e in IGNORE_DIRS:
                continue
            filtered.append(e)

        for i, name in enumerate(filtered):
            full_path = os.path.join(dir_path, name)
            is_last = i == len(filtered) - 1

            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + name)

            if os.path.isdir(full_path):
                extension_prefix = "    " if is_last else "│   "
                walk(full_path, prefix + extension_prefix)

    walk(root_path)
    return "\n".join(lines)


def is_text_file(file_path: str) -> bool:
    """
    Vérifie si on doit inclure le contenu du fichier dans le recap.
    """
    ext = os.path.splitext(file_path)[1].lower()
    return ext in TEXT_EXTENSIONS


def safe_read_file(file_path: str) -> str:
    encodings_to_try = [
        "utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be",  # Ajout des UTF-16
        "latin-1", "cp1252"
    ]

    for enc in encodings_to_try:
        try:
            with open(file_path, "r", encoding=enc, errors="strict") as f:
                return f.read()
        except Exception:
            pass

    # Dernier recours
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def generate_recap(root_path: str):
    root_path = os.path.abspath(root_path)
    folder_name = os.path.basename(root_path)

    # dossier recaps
    recaps_dir = os.path.join(root_path, "recaps")
    os.makedirs(recaps_dir, exist_ok=True)

    # nom du fichier recap
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    recap_filename = f"recap_{folder_name}_{now}.txt"
    recap_path = os.path.join(recaps_dir, recap_filename)

    with open(recap_path, "w", encoding="utf-8") as out:
        # 1) Arborescence au début
        out.write("=" * 80 + "\n")
        out.write("RECAP PROJECT\n")
        out.write("=" * 80 + "\n")
        out.write(f"Racine du projet : {root_path}\n")
        out.write(f"Date : {now}\n")
        out.write("\n")
        out.write(build_tree(root_path))
        out.write("\n\n")

        # 2) Contenu de chaque fichier
        out.write("=" * 80 + "\n")
        out.write("CONTENU DES FICHIERS\n")
        out.write("=" * 80 + "\n\n")

        for current_dir, dirs, files in os.walk(root_path):
            # ignorer dossiers
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file_name in sorted(files):
                file_path = os.path.join(current_dir, file_name)

                # ignorer le recap lui-même
                if os.path.abspath(file_path) == os.path.abspath(recap_path):
                    continue

                # ignorer fichiers binaires (images etc.)
                if not is_text_file(file_path):
                    continue

                rel_path = os.path.relpath(file_path, root_path)

                out.write("-" * 80 + "\n")
                out.write(f"FICHIER : {rel_path}\n")
                out.write(f"PROVENANCE : {file_path}\n")
                out.write("-" * 80 + "\n\n")

                try:
                    content = safe_read_file(file_path)
                    out.write(content)
                except Exception as e:
                    out.write(f"[ERREUR LECTURE] {e}\n")

                out.write("\n\n")

    print(f"[OK] Recap généré : {recap_path}")


def is_binary_allowed(file_path):
    return os.path.splitext(file_path)[1].lower() in {".ico", ".png", ".jpg"}


if __name__ == "__main__":
    # Par défaut : le dossier où tu lances le script
    generate_recap(".")
