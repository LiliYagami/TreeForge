"""
test_diff_engine.py — Tests unitaires pour core/diff_engine.py et son
intégration dans generator.generate() / revers_recaper.extract().
"""
from __future__ import annotations
import sys
import os
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from treeforge.core.models import TreeNode, ParseResult
from treeforge.core.generator import generate
from treeforge.core.revers_recaper import extract
from treeforge.core.recaper import recap
from treeforge.core.diff_engine import compute_plan_for_generate, compute_plan_for_restore


def _status_map(plan):
    return {item.rel_path: item.status for item in plan.items}


class TestComputePlanForGenerate(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _tree(self):
        # racine/
        #   src/            (dossier)
        #     main.py       (fichier)
        #   README.md       (fichier)
        readme = TreeNode(name="README.md", is_dir=False, content="# Hello")
        main_py = TreeNode(name="main.py", is_dir=False, content="print(1)")
        src = TreeNode(name="src", is_dir=True, children=[main_py])
        return ParseResult(nodes=[src, readme])

    def test_all_new_on_empty_destination(self):
        plan = compute_plan_for_generate(self._tree(), self.dest, content_mode="Minimal")
        statuses = _status_map(plan)
        self.assertEqual(statuses["src"], "new")
        self.assertEqual(statuses["src/main.py"], "new")
        self.assertEqual(statuses["README.md"], "new")

    def test_unchanged_vs_modified(self):
        (self.dest / "src").mkdir()
        (self.dest / "src" / "main.py").write_text("print(1)", encoding="utf-8")  # identique
        (self.dest / "README.md").write_text("# Old", encoding="utf-8")           # différent

        plan = compute_plan_for_generate(self._tree(), self.dest, content_mode="Minimal")
        statuses = _status_map(plan)
        self.assertEqual(statuses["src"], "unchanged")
        self.assertEqual(statuses["src/main.py"], "unchanged")
        self.assertEqual(statuses["README.md"], "modified")

    def test_excluded_node_not_in_plan(self):
        tree = self._tree()
        # Exclure le dossier src/ entier (comme Espace/clic droit dans PreviewTree)
        tree.nodes[0].excluded = True
        plan = compute_plan_for_generate(tree, self.dest, content_mode="Minimal")
        paths = {item.rel_path for item in plan.items}
        self.assertNotIn("src", paths)
        self.assertNotIn("src/main.py", paths)
        self.assertIn("README.md", paths)


class TestGenerateRespectsPlan(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_unselected_item_is_skipped(self):
        readme = TreeNode(name="README.md", is_dir=False, content="# New")
        result = ParseResult(nodes=[readme])

        (self.dest / "README.md").write_text("# Keep me", encoding="utf-8")

        plan = compute_plan_for_generate(result, self.dest, content_mode="Minimal")
        plan.get("README.md").included = False

        generate(result, self.dest, content_mode="Minimal", plan=plan)

        self.assertEqual((self.dest / "README.md").read_text(encoding="utf-8"), "# Keep me")

    def test_unchanged_file_is_not_rewritten(self):
        readme = TreeNode(name="README.md", is_dir=False, content="# Same")
        result = ParseResult(nodes=[readme])
        (self.dest / "README.md").write_text("# Same", encoding="utf-8")

        plan = compute_plan_for_generate(result, self.dest, content_mode="Minimal")
        nb_dirs, nb_files, errors = generate(result, self.dest, content_mode="Minimal", plan=plan)

        self.assertEqual(nb_files, 0)  # rien écrit, contenu déjà identique
        self.assertEqual(errors, [])

    def test_selected_modified_item_is_written(self):
        readme = TreeNode(name="README.md", is_dir=False, content="# New content")
        result = ParseResult(nodes=[readme])
        (self.dest / "README.md").write_text("# Old content", encoding="utf-8")

        plan = compute_plan_for_generate(result, self.dest, content_mode="Minimal")
        generate(result, self.dest, content_mode="Minimal", plan=plan)

        self.assertEqual(
            (self.dest / "README.md").read_text(encoding="utf-8"), "# New content"
        )


class TestComputePlanForRestore(unittest.TestCase):

    def setUp(self):
        self.tmp_src  = tempfile.TemporaryDirectory()
        self.tmp_dest = tempfile.TemporaryDirectory()
        self.tmp_out  = tempfile.TemporaryDirectory()
        self.src  = Path(self.tmp_src.name)
        self.dest = Path(self.tmp_dest.name)

        # Projet source réel, recapé via core.recaper.recap()
        (self.src / "src").mkdir()
        (self.src / "src" / "a.py").write_text("print(1)", encoding="utf-8")
        (self.src / "src" / "b.py").write_text("print(2)", encoding="utf-8")
        (self.src / "README.md").write_text("# Hello", encoding="utf-8")

        self.recap_path = recap(root=self.src, output_dir=self.tmp_out.name)
        self.text = self.recap_path.read_text(encoding="utf-8")

    def tearDown(self):
        self.tmp_src.cleanup()
        self.tmp_dest.cleanup()
        self.tmp_out.cleanup()

    def test_new_modified_unchanged_classification(self):
        # Pré-remplir la destination : a.py identique, b.py différent, README.md absent
        (self.dest / "src").mkdir()
        (self.dest / "src" / "a.py").write_text("print(1)", encoding="utf-8")
        (self.dest / "src" / "b.py").write_text("print(OLD)", encoding="utf-8")

        plan = compute_plan_for_restore(self.text, self.dest)
        statuses = _status_map(plan)

        self.assertEqual(statuses["src"], "unchanged")
        self.assertEqual(statuses["src/a.py"], "unchanged")
        self.assertEqual(statuses["src/b.py"], "modified")
        self.assertEqual(statuses["README.md"], "new")

    def test_extract_respects_plan_selection(self):
        (self.dest / "src").mkdir()
        (self.dest / "src" / "a.py").write_text("print(1)", encoding="utf-8")
        (self.dest / "src" / "b.py").write_text("print(OLD)", encoding="utf-8")

        plan = compute_plan_for_restore(self.text, self.dest)
        plan.get("README.md").included = False  # décoché par l'utilisateur

        result = extract(self.recap_path, self.dest, overwrite=True, plan=plan)

        self.assertFalse((self.dest / "README.md").exists())
        self.assertEqual(
            (self.dest / "src" / "b.py").read_text(encoding="utf-8"), "print(2)"
        )
        self.assertEqual(
            (self.dest / "src" / "a.py").read_text(encoding="utf-8"), "print(1)"
        )


if __name__ == "__main__":
    unittest.main()
