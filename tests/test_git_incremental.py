"""
test_git_incremental.py — Tests pour le recap incrémental git-aware
(chantier #4) : git_changed_files(), apply_git_selection(), mode_label.
"""
from __future__ import annotations
import sys
import os
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import git

from treeforge.core.recaper import (
    recap_text, scan_tree, git_changed_files, apply_git_selection,
)


class TestGitChangedFilesNotARepo(unittest.TestCase):

    def test_returns_none_for_non_git_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("a", encoding="utf-8")
            self.assertIsNone(git_changed_files(tmp))


class TestGitChangedFilesRealRepo(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

        self.repo = git.Repo.init(self.root)
        with self.repo.config_writer() as cw:
            cw.set_value("user", "name", "Test")
            cw.set_value("user", "email", "test@example.com")

        (self.root / "src").mkdir()
        (self.root / "src" / "stable.py").write_text("stable", encoding="utf-8")
        (self.root / "src" / "will_change.py").write_text("old content", encoding="utf-8")
        self.repo.index.add(["src/stable.py", "src/will_change.py"])
        self.repo.index.commit("initial commit")

        # Modifie un fichier tracké, ajoute un fichier non tracké
        (self.root / "src" / "will_change.py").write_text("new content", encoding="utf-8")
        (self.root / "src" / "new_file.py").write_text("brand new", encoding="utf-8")

    def tearDown(self):
        self.repo.close()  # libère les handles git (cat-file) — sinon rmtree échoue sur Windows
        self.tmp.cleanup()

    def test_detects_modified_and_untracked(self):
        changed = git_changed_files(self.root)
        self.assertEqual(changed, {"src/will_change.py", "src/new_file.py"})
        self.assertNotIn("src/stable.py", changed)

    def test_apply_git_selection_marks_files_correctly(self):
        nodes = scan_tree(self.root)
        changed = git_changed_files(self.root)
        apply_git_selection(nodes, changed)

        src = next(n for n in nodes if n.name == "src")
        self.assertFalse(src.excluded)  # les dossiers restent toujours inclus

        by_name = {c.name: c for c in src.children}
        self.assertTrue(by_name["stable.py"].excluded)
        self.assertFalse(by_name["will_change.py"].excluded)
        self.assertFalse(by_name["new_file.py"].excluded)

    def test_recap_text_with_mode_label_and_incremental_selection(self):
        nodes = scan_tree(self.root)
        changed = git_changed_files(self.root)
        apply_git_selection(nodes, changed)

        from treeforge.core.recaper import included_paths_from_tree
        include_paths = included_paths_from_tree(nodes)

        text, _ = recap_text(self.root, include_paths=include_paths, mode_label="Incrémental depuis HEAD")

        self.assertIn("Mode             : Incrémental depuis HEAD", text)
        self.assertIn("new content", text)
        self.assertIn("brand new", text)
        self.assertNotIn("stable", text)  # ni le nom du fichier ni son contenu


if __name__ == "__main__":
    unittest.main()
