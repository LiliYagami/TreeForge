"""
test_audit_fixes.py — Tests unitaires automatisés pour valider les améliorations 1 et 3.
"""
from __future__ import annotations
import sys
import os
import unittest
import tempfile
import json
from pathlib import Path

# Ajouter src/ au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from treeforge.core.models import TreeNode, ParseResult
from treeforge.core.generator import generate
from treeforge.utils.helpers import load_boilerplates, save_boilerplates, DEFAULT_BOILERPLATE


class TestAuditFixes(unittest.TestCase):

    def setUp(self):
        # Utiliser un dossier temporaire pour les tests de génération
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.dest_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_improvement_1_boilerplates_io(self):
        """Vérifie le chargement et la sauvegarde des boilerplates par fichier externe."""
        # 1. Sauvegarder des boilerplates modifiés de test
        test_boilerplates = {
            ".py": "# Python custom header\n",
            ".html": "<!-- Custom HTML -->\n"
        }
        success = save_boilerplates(test_boilerplates)
        self.assertTrue(success)

        # 2. Charger et valider
        loaded = load_boilerplates()
        self.assertEqual(loaded.get(".py"), "# Python custom header\n")
        self.assertEqual(loaded.get(".html"), "<!-- Custom HTML -->\n")

        # 3. Restaurer les boilerplates par défaut
        save_boilerplates(DEFAULT_BOILERPLATE)

    def test_improvement_3_tree_node_excluded_attribute(self):
        """Vérifie que la classe TreeNode possède bien l'attribut excluded."""
        node = TreeNode(name="test_file.txt", is_dir=False)
        self.assertTrue(hasattr(node, "excluded"))
        self.assertFalse(node.excluded)

        node.excluded = True
        self.assertTrue(node.excluded)

    def test_improvement_3_generator_skips_excluded_nodes(self):
        """Vérifie que le générateur ignore les fichiers/dossiers exclus."""
        # Créer une arborescence de test
        # root/
        #   ├── included_dir/
        #   │     └── file1.txt
        #   └── excluded_dir/ [EXCLU]
        #         └── file2.txt
        
        file1 = TreeNode(name="file1.txt", is_dir=False)
        included_dir = TreeNode(name="included_dir", is_dir=True, children=[file1])
        
        file2 = TreeNode(name="file2.txt", is_dir=False)
        excluded_dir = TreeNode(name="excluded_dir", is_dir=True, children=[file2], excluded=True)
        
        root = TreeNode(name="root_dir", is_dir=True, children=[included_dir, excluded_dir])
        
        pr = ParseResult(nodes=[root])
        
        # Lancer la génération
        nb_dirs, nb_files, errors = generate(pr, self.dest_path, content_mode="Vide")
        
        # Vérifications
        self.assertEqual(len(errors), 0)
        self.assertEqual(nb_dirs, 2)  # root_dir + included_dir (excluded_dir est ignoré)
        self.assertEqual(nb_files, 1) # file1.txt (file2.txt sous dossier exclu est ignoré)
        
        # Vérification sur disque
        self.assertTrue((self.dest_path / "root_dir").exists())
        self.assertTrue((self.dest_path / "root_dir" / "included_dir").exists())
        self.assertTrue((self.dest_path / "root_dir" / "included_dir" / "file1.txt").exists())
        
        self.assertFalse((self.dest_path / "root_dir" / "excluded_dir").exists())
        self.assertFalse((self.dest_path / "root_dir" / "excluded_dir" / "file2.txt").exists())


if __name__ == "__main__":
    unittest.main()
