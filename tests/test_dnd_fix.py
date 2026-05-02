"""
test_dnd_fix.py — Valide le fix cohabitation CTk + TkinterDnD.

Lance depuis le venv AVANT d'intégrer main_window.py :
    $env:PYTHONPATH = "src"
    py tests\test_dnd_fix.py

Ce que tu dois voir si le fix fonctionne :
  ✅ Fenêtre CTk avec D&D actif
  ✅ Glisser un .txt → contenu s'insère dans la zone
  ✅ Pas d'erreur tkdnd::drop_target
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

print("=" * 60)
print("TEST — Fix CTk + TkinterDnD")

# ── Import conditionnel ───────────────────────────────────────────────────────
try:
    from tkinterdnd2 import TkinterDnD
    _DND_OK = True
    print("  ✅ tkinterdnd2 disponible")
except Exception as e:
    _DND_OK = False
    print(f"  ⚠️  tkinterdnd2 absent : {e}")

import customtkinter as ctk
from treeforge.utils.drag_drop import setup_drop_target, DND_AVAILABLE
from treeforge.utils.context_menu import attach_context_menu

# ── Fenêtre avec le fix ───────────────────────────────────────────────────────
if _DND_OK:
    class TestWindow(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self):
            super().__init__()
            self.TkdndVersion = TkinterDnD._require(self)
            self._build()
else:
    class TestWindow(ctk.CTk):
        def __init__(self):
            super().__init__()
            self._build()


class TestWindow(TestWindow):
    def _build(self):
        self.title("Test fix D&D + CTk")
        self.geometry("560x340")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.box = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.box.grid(row=0, column=0, padx=20, pady=(20, 8), sticky="nsew")
        self.box.insert("1.0", "Glissez un fichier .txt ici\nou faites clic droit…")

        self.lbl = ctk.CTkLabel(self, text="", font=("Consolas", 11),
                                text_color=("gray40", "gray60"))
        self.lbl.grid(row=1, column=0, pady=(0, 16))

        # Clic droit
        attach_context_menu(self.box)

        # D&D
        ok = setup_drop_target(self.box, on_drop=self._on_drop)
        if ok:
            self.lbl.configure(
                text="✅ D&D actif + clic droit — glissez un .txt pour tester"
            )
            print("  ✅ D&D activé sur le widget — fix OK !")
        else:
            self.lbl.configure(
                text="⚠️  D&D non disponible — clic droit uniquement"
            )
            print("  ⚠️  D&D toujours inactif — voir message d'erreur ci-dessus")

    def _on_drop(self, content):
        self.box.delete("1.0", "end")
        self.box.insert("1.0", content)
        self.lbl.configure(text="✅ Fichier déposé avec succès !")
        print(f"  ✅ D&D reçu — {len(content)} caractères")


if __name__ == "__main__":
    app = TestWindow()
    app.mainloop()
    print("\nFenêtre fermée proprement.")