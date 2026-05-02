"""Point d'entrée principal de TreeForge."""
import sys
import os

# Garantit que src/ est dans le path même sans pip install -e
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from treeforge.main import main

if __name__ == "__main__":
    main()