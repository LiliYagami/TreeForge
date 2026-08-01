"""
test_recap_selection.py — Tests pour la sélection interactive avant recap
(chantier #3) : scan_tree(), included_paths_from_tree(), et include_paths
dans recap()/recap_text().
"""
from __future__ import annotations
import sys
import os
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from treeforge.core.recaper import recap, recap_text, scan_tree, included_paths_from_tree


def _names(nodes) -> set[str]:
    return {n.name for n in nodes}


class TestScanTree(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "main.py").write_text("print(1)", encoding="utf-8")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "junk.js").write_text("//junk", encoding="utf-8")
        (self.root / "README.md").write_text("# Hello world", encoding="utf-8")
        (self.root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_exclude_dirs_are_pruned(self):
        nodes = scan_tree(self.root)
        self.assertNotIn("node_modules", _names(nodes))

    def test_structure_and_ordering(self):
        nodes = scan_tree(self.root)
        # Dossiers avant fichiers (comme _tree_lines)
        self.assertEqual(nodes[0].name, "src")
        self.assertTrue(nodes[0].is_dir)
        src_children = _names(nodes[0].children)
        self.assertIn("main.py", src_children)

    def test_size_populated_for_text_files_only(self):
        nodes = scan_tree(self.root)
        readme = next(n for n in nodes if n.name == "README.md")
        logo   = next(n for n in nodes if n.name == "logo.png")
        self.assertGreater(readme.size, 0)
        self.assertEqual(logo.size, 0)  # non-texte → pas d'estimation


class TestIncludedPathsFromTree(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("a", encoding="utf-8")
        (self.root / "src" / "b.py").write_text("b", encoding="utf-8")
        (self.root / "README.md").write_text("readme", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_included_by_default(self):
        nodes = scan_tree(self.root)
        included = included_paths_from_tree(nodes)
        self.assertEqual(included, {"src", "src/a.py", "src/b.py", "README.md"})

    def test_excluding_dir_removes_descendants(self):
        nodes = scan_tree(self.root)
        src_node = next(n for n in nodes if n.name == "src")
        src_node.excluded = True

        included = included_paths_from_tree(nodes)
        self.assertEqual(included, {"README.md"})

    def test_excluding_single_file(self):
        nodes = scan_tree(self.root)
        src_node = next(n for n in nodes if n.name == "src")
        b_node = next(n for n in src_node.children if n.name == "b.py")
        b_node.excluded = True

        included = included_paths_from_tree(nodes)
        self.assertEqual(included, {"src", "src/a.py", "README.md"})


class TestIncludePathsInRecap(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "keep.py").write_text("KEEP_MARKER", encoding="utf-8")
        (self.root / "src" / "skip.py").write_text("SKIP_MARKER", encoding="utf-8")
        (self.root / "README.md").write_text("readme", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _selection_excluding_skip(self) -> set[str]:
        nodes = scan_tree(self.root)
        src_node = next(n for n in nodes if n.name == "src")
        skip_node = next(n for n in src_node.children if n.name == "skip.py")
        skip_node.excluded = True
        return included_paths_from_tree(nodes)

    def test_recap_text_respects_include_paths(self):
        include_paths = self._selection_excluding_skip()
        text, _ = recap_text(self.root, include_paths=include_paths)

        self.assertIn("KEEP_MARKER", text)
        self.assertNotIn("SKIP_MARKER", text)
        self.assertIn("keep.py", text)
        self.assertNotIn("skip.py", text)  # ni dans l'arborescence, ni dans le contenu

    def test_recap_file_respects_include_paths(self):
        include_paths = self._selection_excluding_skip()
        with tempfile.TemporaryDirectory() as out_dir:
            out_path = recap(self.root, output_dir=out_dir, include_paths=include_paths)
            text = out_path.read_text(encoding="utf-8")

        self.assertIn("KEEP_MARKER", text)
        self.assertNotIn("SKIP_MARKER", text)


if __name__ == "__main__":
    unittest.main()
