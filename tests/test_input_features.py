"""
test_input_features.py — Test D&D + clic droit.

Lance depuis le venv :
    $env:PYTHONPATH = "src"
    py tests\test_input_features.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

print("=" * 60)
print("TEST 1 — Import tkinterdnd2")
try:
    from tkinterdnd2 import TkinterDnD
    _DND_OK = True
    print("  ✅ tkinterdnd2 importé avec succès")
except Exception as e:
    _DND_OK = False
    print(f"  ⚠️  tkinterdnd2 absent : {e}")

print("\nTEST 2 — Imports TreeForge")
try:
    from treeforge.utils.drag_drop import setup_drop_target, DND_AVAILABLE
    from treeforge.utils.context_menu import attach_context_menu
    print(f"  ✅ drag_drop.py — DND_AVAILABLE={DND_AVAILABLE}")
    print("  ✅ context_menu.py")
except Exception as e:
    print(f"  ❌ Erreur import : {e}")
    sys.exit(1)

print("\nTEST 3 — Fenêtre avec fix CTk+DnD")
print("  → Clic droit pour tester le menu")
if _DND_OK:
    print("  → Glissez un .txt ou .json pour tester le D&D")
print("  → Fermez la fenêtre pour terminer")
print("=" * 60)

import customtkinter as ctk

# ── Fenêtre avec le MÊME fix que main_window.py ──────────────────────────────
_base_ok = False
if _DND_OK:
    try:
        class _TestBase(ctk.CTk, TkinterDnD.DnDWrapper):
            def __init__(self):
                super().__init__()
                self.TkdndVersion = TkinterDnD._require(self)
        _base_ok = True
        print("  ✅ Classe hybride CTk+DnD créée")
    except Exception as e:
        print(f"  ❌ Hybride échoué : {e}")

if not _base_ok:
    class _TestBase(ctk.CTk):
        def __init__(self):
            super().__init__()
    print("  ℹ️  Fenêtre CTk standard (sans D&D)")


class TestWindow(_TestBase):
    def __init__(self):
        super().__init__()
        self.title("Test D&D + Clic droit — TreeForge")
        self.geometry("580x360")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.box = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.box.grid(row=0, column=0, padx=20, pady=(20, 8), sticky="nsew")

        self.lbl = ctk.CTkLabel(self, text="", font=("Consolas", 11),
                                text_color=("gray40", "gray60"))
        self.lbl.grid(row=1, column=0, pady=(0, 16))

        attach_context_menu(self.box)
        ok = setup_drop_target(self.box, on_drop=self._on_drop)

        if ok:
            self.box.insert("1.0",
                "✅ D&D actif !\n\nGlissez un .txt ou .json ici.\n"
                "Faites aussi un clic droit pour tester le menu.")
            self.lbl.configure(text="✅ Drag & Drop actif   ✅ Clic droit actif")
            print("  ✅ D&D activé sur le widget — FIX OK !")
        else:
            self.box.insert("1.0",
                "⚠️  D&D non disponible.\n\nFaites un clic droit pour tester le menu.")
            self.lbl.configure(text="⚠️  D&D inactif   ✅ Clic droit actif")
            print("  ⚠️  D&D inactif malgré le fix")

    def _on_drop(self, content: str):
        self.box.delete("1.0", "end")
        self.box.insert("1.0", content)
        self.lbl.configure(text="✅ Fichier déposé avec succès !")
        print(f"  ✅ D&D reçu — {len(content)} caractères")


if __name__ == "__main__":
    app = TestWindow()
    app.mainloop()
    print("\n✅ Fenêtre fermée proprement")
    print(f"\n  tkinterdnd2 dispo  : {_DND_OK}")
    print(f"  DND_AVAILABLE      : {DND_AVAILABLE}")
    print(f"  Fix hybride actif  : {_base_ok}")