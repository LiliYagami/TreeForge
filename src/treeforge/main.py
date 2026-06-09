"""Point d'entrée de l'application TreeForge."""
from __future__ import annotations
import os


def main() -> None:
    os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

    import customtkinter as ctk
    from treeforge.utils.helpers import load_prefs

    # Charger le thème utilisateur au démarrage
    prefs = load_prefs()
    theme = prefs.get("theme", "dark")
    ctk.set_appearance_mode(theme)

    from treeforge.gui.main_window import MainWindow
    from treeforge.core.telemetry import has_answered_consent, set_consent
    from treeforge.gui.components.consent_dialog import ConsentDialog

    app = MainWindow()

    # ── Premier lancement → dialogue télémétrie ───────────────────────────
    if not has_answered_consent():
        dlg = ConsentDialog(app)
        app.wait_window(dlg)
        if dlg.result is not None:
            set_consent(dlg.result)

    app.mainloop()


if __name__ == "__main__":
    main()
