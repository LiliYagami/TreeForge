"""
test_clipboard_flow.py — Tests du cycle Recaper/Restaurer 100% en mémoire
(mode presse-papiers), sans fichier .txt intermédiaire sur disque.
"""
from __future__ import annotations
import sys
import os
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from treeforge.core.recaper import recap, recap_text
from treeforge.core.revers_recaper import extract_text
from treeforge.core.diff_engine import compute_plan_for_restore


class TestRecapText(unittest.TestCase):

    def setUp(self):
        self.tmp_src = tempfile.TemporaryDirectory()
        self.src = Path(self.tmp_src.name)
        (self.src / "src").mkdir()
        (self.src / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
        (self.src / "README.md").write_text("# Demo", encoding="utf-8")

    def tearDown(self):
        self.tmp_src.cleanup()

    def test_recap_text_produces_no_file_on_disk(self):
        before = set(self.src.rglob("*"))
        text, root = recap_text(self.src)
        after = set(self.src.rglob("*"))
        self.assertEqual(before, after)  # aucun fichier créé
        self.assertIn("ARBORESCENCE", text)
        self.assertIn("<<TREEFORGE_FILE_BLOCK>>", text)
        self.assertEqual(root, self.src.resolve())

    def test_recap_text_matches_recap_file_content(self):
        """recap_text() et recap() doivent produire le même contenu (hors horodatage)."""
        text, _ = recap_text(self.src)

        with tempfile.TemporaryDirectory() as out_dir:
            out_path = recap(self.src, output_dir=out_dir)
            file_text = out_path.read_text(encoding="utf-8")

        # Les deux doivent contenir les mêmes fichiers/contenus (la ligne de date diffère).
        self.assertIn("main.py", text)
        self.assertIn("main.py", file_text)
        self.assertIn("print('hello')", text)
        self.assertIn("print('hello')", file_text)


class TestExtractText(unittest.TestCase):

    def setUp(self):
        self.tmp_src  = tempfile.TemporaryDirectory()
        self.tmp_dest = tempfile.TemporaryDirectory()
        self.src  = Path(self.tmp_src.name)
        self.dest = Path(self.tmp_dest.name)

        (self.src / "src").mkdir()
        (self.src / "src" / "main.py").write_text("print(1)", encoding="utf-8")
        (self.src / "README.md").write_text("# Hello", encoding="utf-8")

        self.text, _ = recap_text(self.src)

    def tearDown(self):
        self.tmp_src.cleanup()
        self.tmp_dest.cleanup()

    def test_extract_text_recreates_project(self):
        result = extract_text(self.text, self.dest)

        self.assertTrue(result.success)
        self.assertEqual(
            (self.dest / "src" / "main.py").read_text(encoding="utf-8"), "print(1)"
        )
        self.assertEqual(
            (self.dest / "README.md").read_text(encoding="utf-8"), "# Hello"
        )

    def test_extract_text_respects_plan(self):
        (self.dest / "README.md").write_text("# ancien", encoding="utf-8")

        plan = compute_plan_for_restore(self.text, self.dest)
        plan.get("src").included = False
        plan.get("src/main.py").included = False

        result = extract_text(self.text, self.dest, plan=plan)

        self.assertFalse((self.dest / "src" / "main.py").exists())
        self.assertEqual(
            (self.dest / "README.md").read_text(encoding="utf-8"), "# Hello"
        )


if __name__ == "__main__":
    unittest.main()
