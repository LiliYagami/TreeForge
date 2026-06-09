"""
settings_dialog.py — Fenêtre modale Paramètres TreeForge
"""
from __future__ import annotations
import platform
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from treeforge.core.telemetry import is_enabled, set_consent as set_enabled
from treeforge.utils.helpers import load_prefs, save_prefs, DEFAULT_PREFS, DEFAULT_BOILERPLATE, save_boilerplates
from treeforge.config import MODES_PARSING, MODES_CONTENU
import treeforge.config as config

APP_VERSION = "1.0.0"


class SettingsDialog(ctk.CTkToplevel):

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.withdraw()  # Masquer temporairement
        self.title("TreeForge — Paramètres")
        self.geometry("540x480")
        self.minsize(460, 400)
        self.resizable(True, True)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._build()
        
        self.after(100, self._show_and_center)

    def _show_and_center(self):
        self._center()
        self.deiconify()
        self.grab_set()
        self.lift()
        self.focus_force()

    def destroy(self):
        try:
            self.master.refresh_settings()
        except Exception:
            pass
        super().destroy()

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

        self._prefs = load_prefs()
        r = 0

        # ── Titre principal ───────────────────────────────────────────────────
        ctk.CTkLabel(
            scroll,
            text="Paramètres",
            font=ctk.CTkFont(weight="bold", size=16),
            anchor="w",
        ).grid(row=r, column=0, sticky="w", pady=(0, 12))
        r += 1

        # ── Section Apparence ─────────────────────────────────────────────────
        self._section(scroll, r, title="Apparence")
        r += 2

        # Choix du thème
        ctk.CTkLabel(
            scroll,
            text="Thème de l'application :",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).grid(row=r, column=0, sticky="w", padx=8, pady=(4, 2))
        r += 1

        current_theme = self._prefs.get("theme", "dark")
        self._theme_map = {
            "Sombre": "dark",
            "Clair": "light",
            "Système": "system"
        }
        self._theme_reverse_map = {v: k for k, v in self._theme_map.items()}
        initial_value = self._theme_reverse_map.get(current_theme, "Sombre")

        self._theme_var = ctk.StringVar(value=initial_value)
        self._theme_menu = ctk.CTkOptionMenu(
            scroll,
            values=["Sombre", "Clair", "Système"],
            variable=self._theme_var,
            command=self._on_theme_change,
            font=ctk.CTkFont(size=12),
            width=150,
        )
        self._theme_menu.grid(row=r, column=0, sticky="w", padx=8, pady=(0, 8))
        r += 1

        # Astuces rotatives Switch
        self._tips_var = ctk.BooleanVar(value=self._prefs.get("tips_enabled", True))
        self._tips_switch = ctk.CTkSwitch(
            scroll,
            text="Activer la barre d'astuces rotatives",
            variable=self._tips_var,
            command=self._on_tips_toggle,
            font=ctk.CTkFont(size=13),
        )
        self._tips_switch.grid(row=r, column=0, sticky="w", padx=8, pady=(4, 16))
        r += 1

        # ── Section Génération & Parsing ──────────────────────────────────────
        self._section(scroll, r, title="Génération & Parsing")
        r += 2

        # Mode de parsing par défaut
        ctk.CTkLabel(
            scroll,
            text="Mode de parsing par défaut :",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).grid(row=r, column=0, sticky="w", padx=8, pady=(4, 2))
        r += 1

        current_parsing = self._prefs.get("parsing_mode", MODES_PARSING[0])
        self._parsing_var = ctk.StringVar(value=current_parsing)
        self._parsing_menu = ctk.CTkOptionMenu(
            scroll,
            values=MODES_PARSING,
            variable=self._parsing_var,
            command=self._on_default_parsing_change,
            font=ctk.CTkFont(size=12),
            width=150,
        )
        self._parsing_menu.grid(row=r, column=0, sticky="w", padx=8, pady=(0, 8))
        r += 1

        # Contenu par défaut
        ctk.CTkLabel(
            scroll,
            text="Contenu des fichiers par défaut :",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).grid(row=r, column=0, sticky="w", padx=8, pady=(4, 2))
        r += 1

        current_content = self._prefs.get("content_mode", MODES_CONTENU[0])
        self._content_var = ctk.StringVar(value=current_content)
        self._content_menu = ctk.CTkOptionMenu(
            scroll,
            values=MODES_CONTENU,
            variable=self._content_var,
            command=self._on_default_content_change,
            font=ctk.CTkFont(size=12),
            width=150,
        )
        self._content_menu.grid(row=r, column=0, sticky="w", padx=8, pady=(0, 12))
        r += 1

        # Bouton Gérer Boilerplates
        ctk.CTkButton(
            scroll,
            text="📝 Gérer les Boilerplates...",
            font=ctk.CTkFont(size=12),
            height=32,
            command=self._open_boilerplate_editor,
        ).grid(row=r, column=0, sticky="w", padx=8, pady=(4, 16))
        r += 1

        # ── Section Données & Maintenance ─────────────────────────────────────
        self._section(scroll, r, title="Données & Maintenance")
        r += 2

        # Nettoyage historique
        ctk.CTkButton(
            scroll,
            text="🧹 Vider l'historique des dossiers",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            border_width=1,
            text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray25"),
            height=32,
            command=self._clear_history,
        ).grid(row=r, column=0, sticky="w", padx=8, pady=(4, 6))
        r += 1

        # Rétablir paramètres d'usine
        ctk.CTkButton(
            scroll,
            text="⚠️ Réinitialiser l'application",
            font=ctk.CTkFont(size=12),
            fg_color="#c62828",
            hover_color="#b71c1c",
            height=32,
            command=self._reset_factory,
        ).grid(row=r, column=0, sticky="w", padx=8, pady=(4, 16))
        r += 1

        # ── Section Données & confidentialité ─────────────────────────────────
        self._section(scroll, r, title="Données & confidentialité")
        r += 2

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
        ).grid(row=r, column=0, sticky="w", padx=8, pady=(4, 4))
        r += 1

        self._telem_var = ctk.BooleanVar(value=is_enabled())
        self._telem_switch = ctk.CTkSwitch(
            scroll,
            text="Télémétrie activée",
            variable=self._telem_var,
            command=self._on_telem_toggle,
            font=ctk.CTkFont(size=13),
        )
        self._telem_switch.grid(row=r, column=0, sticky="w", padx=8, pady=(0, 16))
        r += 1

        # ── Section À propos ──────────────────────────────────────────────────
        self._section(scroll, r, title="À propos")
        r += 2

        infos = [
            ("Version",    APP_VERSION),
            ("Plateforme", f"{platform.system()} {platform.release()}"),
            ("Auteur",     "TreeForge"),
            ("Licence",    "Usage éducatif libre"),
        ]
        for key, val in infos:
            frame = ctk.CTkFrame(scroll, fg_color="transparent")
            frame.grid(row=r, column=0, sticky="ew", padx=8, pady=1)
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
            r += 1

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

    def _on_theme_change(self, val: str):
        theme = self._theme_map.get(val, "dark")
        ctk.set_appearance_mode(theme)
        self._prefs["theme"] = theme
        save_prefs(self._prefs)
        # Forcer le rafraîchissement visuel et ramener au premier plan pour éviter l'invisibilité sous Windows
        self.update_idletasks()
        self.lift()
        self.focus_force()

    def _on_tips_toggle(self):
        self._prefs["tips_enabled"] = self._tips_var.get()
        save_prefs(self._prefs)

    def _on_default_parsing_change(self, val: str):
        self._prefs["parsing_mode"] = val
        save_prefs(self._prefs)

    def _on_default_content_change(self, val: str):
        self._prefs["content_mode"] = val
        save_prefs(self._prefs)

    def _open_boilerplate_editor(self):
        from treeforge.gui.components.boilerplate_editor import BoilerplateEditorDialog
        BoilerplateEditorDialog(self)

    def _clear_history(self):
        confirmed = messagebox.askyesno(
            "Confirmer la suppression",
            "Voulez-vous vraiment effacer l'historique des dossiers de destination récents ?",
            parent=self
        )
        if confirmed:
            self._prefs["destination_history"] = []
            self._prefs["last_destination"] = ""
            save_prefs(self._prefs)
            messagebox.showinfo("Historique vidé", "L'historique des destinations a été effacé.", parent=self)

    def _reset_factory(self):
        confirmed = messagebox.askyesno(
            "Réinitialisation d'usine",
            "ATTENTION: Cette action va réinitialiser tous vos paramètres de préférences "
            "et restaurer les boilerplates par défaut.\n\n"
            "Voulez-vous vraiment continuer ?",
            parent=self
        )
        if confirmed:
            # Réinitialiser les préférences
            self._prefs.clear()
            self._prefs.update(DEFAULT_PREFS)
            save_prefs(self._prefs)

            # Réinitialiser les boilerplates
            save_boilerplates(DEFAULT_BOILERPLATE)
            config.BOILERPLATE.clear()
            config.BOILERPLATE.update(DEFAULT_BOILERPLATE)

            # Mettre à jour l'état de l'UI du dialogue
            ctk.set_appearance_mode(DEFAULT_PREFS["theme"])
            self._theme_var.set(self._theme_reverse_map.get(DEFAULT_PREFS["theme"], "Sombre"))
            self._tips_var.set(DEFAULT_PREFS["tips_enabled"])
            self._parsing_var.set(DEFAULT_PREFS["parsing_mode"])
            self._content_var.set(DEFAULT_PREFS["content_mode"])
            self._telem_var.set(DEFAULT_PREFS["telemetry_enabled"])
            set_enabled(DEFAULT_PREFS["telemetry_enabled"])

            # Mettre à jour les switches et menus visuellement
            self._tips_switch.deselect() if not DEFAULT_PREFS["tips_enabled"] else self._tips_switch.select()
            self._telem_switch.deselect() if not DEFAULT_PREFS["telemetry_enabled"] else self._telem_switch.select()

            messagebox.showinfo("Réinitialisation réussie", "L'application a été réinitialisée avec succès aux paramètres d'usine.", parent=self)
