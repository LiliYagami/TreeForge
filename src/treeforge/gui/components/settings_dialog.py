"""
settings_dialog.py — Fenêtre modale Paramètres TreeForge
"""
from __future__ import annotations
import platform
import customtkinter as ctk
from treeforge.core.telemetry import is_enabled, set_consent as set_enabled

APP_VERSION = "1.0.0"


class SettingsDialog(ctk.CTkToplevel):

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.title("TreeForge — Paramètres")
        self.geometry("540x420")
        self.minsize(460, 360)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.lift()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._build()
        self.after(50, self._center)

    # ─────────────────────────────────────────────────────────────────────────

    def _center(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_x() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_y() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # ── Zone scrollable ───────────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 0))
        scroll.grid_columnconfigure(0, weight=1)

        # ── Titre principal ───────────────────────────────────────────────────
        # row 0
        ctk.CTkLabel(
            scroll,
            text="Paramètres",
            font=ctk.CTkFont(weight="bold", size=16),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        # ── Section Données & confidentialité ─────────────────────────────────
        # row 1  → label titre
        # row 2  → trait séparateur   (géré par _section)
        self._section(scroll, row=1, title="Données & confidentialité")

        # row 3
        ctk.CTkLabel(
            scroll,
            text=(
                "Autoriser TreeForge à envoyer des données anonymes\n"
                "d'utilisation et des rapports de crash."
            ),
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        ).grid(row=3, column=0, sticky="w", padx=8, pady=(4, 4))

        # row 4
        self._telem_var = ctk.BooleanVar(value=is_enabled())
        ctk.CTkSwitch(
            scroll,
            text="Télémétrie activée",
            variable=self._telem_var,
            command=self._on_telem_toggle,
            font=ctk.CTkFont(size=13),
        ).grid(row=4, column=0, sticky="w", padx=8, pady=(0, 16))

        # ── Section À propos ──────────────────────────────────────────────────
        # row 5  → label titre
        # row 6  → trait séparateur
        self._section(scroll, row=5, title="À propos")

        # rows 7, 8, 9, 10
        infos = [
            ("Version",    APP_VERSION),
            ("Plateforme", f"{platform.system()} {platform.release()}"),
            ("Auteur",     "TreeForge"),
            ("Licence",    "Usage éducatif libre"),
        ]
        for i, (key, val) in enumerate(infos):
            row_n = 7 + i
            frame = ctk.CTkFrame(scroll, fg_color="transparent")
            frame.grid(row=row_n, column=0, sticky="ew", padx=8, pady=1)
            frame.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                frame, text=key,
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray60"),
                width=90, anchor="w",
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                frame, text=val,
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=(8, 0))

        # ── Section Apparence ─────────────────────────────────────────────────
        # row 11 → label titre
        # row 12 → trait séparateur
        self._section(scroll, row=11, title="Apparence  —  disponible en v1.5")

        # row 13
        ctk.CTkLabel(
            scroll,
            text="Prochainement…",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).grid(row=13, column=0, sticky="w", padx=8, pady=(4, 16))

        # ── Bas : version + bouton Fermer ─────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent", height=48)
        bottom.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 12))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_propagate(False)

        ctk.CTkLabel(
            bottom,
            text=f"TreeForge v{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=("gray45", "gray55"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            bottom,
            text="Fermer",
            width=100,
            command=self.destroy,
        ).grid(row=0, column=1, sticky="e")

    # ─────────────────────────────────────────────────────────────────────────

    def _section(self, parent, row: int, title: str):
        """Titre de section (row) + trait séparateur (row+1)."""
        ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(weight="bold", size=13),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(12, 0))

        ctk.CTkFrame(
            parent,
            height=1,
            fg_color=("gray75", "gray30"),
        ).grid(row=row + 1, column=0, sticky="ew", pady=(2, 6))

    # ─────────────────────────────────────────────────────────────────────────

    def _on_telem_toggle(self):
        set_enabled(self._telem_var.get())
