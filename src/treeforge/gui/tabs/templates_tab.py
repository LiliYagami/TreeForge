"""
Onglet Templates — sélection d'un template JSON, aperçu, génération.
"""
from __future__ import annotations
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from treeforge.config import MODES_CONTENU
from treeforge.core.template_manager import list_templates, load_template
from treeforge.core.generator import generate
from treeforge.core.models import ParseResult
from treeforge.utils.logger import logger
from treeforge.utils.helpers import format_tree


class TemplatesTab(ctk.CTkFrame):
    def __init__(self, master, update_status, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._update_status = update_status
        self._templates: list[str] = []
        self._build()
        self._refresh_templates()

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # ── Sélection du template ───────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="Template :").grid(row=0, column=0, padx=(0, 8))
        self.template_var = ctk.StringVar(value="")
        self.template_menu = ctk.CTkOptionMenu(
            top, variable=self.template_var,
            values=["(aucun template)"],
            command=self._on_template_change
        )
        self.template_menu.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ctk.CTkButton(top, text="↻", width=32, command=self._refresh_templates).grid(row=0, column=2)

        # ── Aperçu ─────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Aperçu de l'arborescence :").grid(
            row=1, column=0, padx=12, pady=(6, 2), sticky="w"
        )
        self.preview_box = ctk.CTkTextbox(
            self, font=("Consolas", 12), state="disabled",
            fg_color=("white", "gray16")
        )
        self.preview_box.grid(row=1, column=0, padx=12, pady=(24, 6), sticky="nsew")

        # ── Options + bouton ────────────────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")
        bottom.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bottom, text="Contenu :").grid(row=0, column=0, padx=(0, 8))
        self.content_var = ctk.StringVar(value=MODES_CONTENU[0])
        ctk.CTkOptionMenu(bottom, variable=self.content_var, values=MODES_CONTENU, width=140).grid(
            row=0, column=1, sticky="w", padx=(0, 12)
        )

        self._btn_generate = ctk.CTkButton(
            bottom, text="Générer ce template", height=36,
            fg_color="#2e7d32", hover_color="#1b5e20",
            command=self._generate
        )
        self._btn_generate.grid(row=0, column=2)


    def _refresh_templates(self):
        self._templates = list_templates()
        values = self._templates if self._templates else ["(aucun template)"]
        self.template_menu.configure(values=values)
        if self._templates:
            self.template_var.set(self._templates[0])
            self._on_template_change(self._templates[0])
        else:
            self.template_var.set("(aucun template)")
            self._set_preview("Aucun template disponible.\n\nAjoutez des fichiers .json dans :\nsrc/treeforge/resources/templates/")

    def _on_template_change(self, name: str):
        if name == "(aucun template)":
            return
        try:
            nodes = load_template(name)
            self._set_preview(format_tree(nodes))
        except Exception as e:
            self._set_preview(f"Erreur de chargement : {e}")

    def _set_preview(self, text: str):
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", text)
        self.preview_box.configure(state="disabled")

    def _generate(self):
        name = self.template_var.get()
        if name == "(aucun template)":
            messagebox.showwarning("TreeForge", "Sélectionnez un template.")
            return
        try:
            nodes = load_template(name)
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return

        dest = filedialog.askdirectory(title="Choisir le dossier de destination")
        if not dest:
            return

        content = self.content_var.get()
        pr = ParseResult(nodes=nodes)

        self._update_status(f"Génération du template {name}…")
        logger.info(f"Template {name} → {dest}")
        self._btn_generate.configure(state="disabled")

        def _run():
            nb_dirs, nb_files, errors = generate(pr, dest, content,
                                                  on_progress=lambda m: logger.info(m))
            self.after(0, self._on_done, nb_dirs, nb_files, errors, dest, name)

        threading.Thread(target=_run, daemon=True).start()


    def _on_done(self, nb_dirs, nb_files, errors, dest, name):
        self._btn_generate.configure(state="normal")
        if errors:
            self._update_status(f"⚠️ {name} terminé avec {len(errors)} erreur(s)")
            messagebox.showwarning("Terminé avec erreurs", "\n".join(errors[:5]))
        else:
            self._update_status(f"✅ Template {name} — {nb_dirs} dossiers, {nb_files} fichiers → {dest}")
            logger.info(f"✅ Template {name} généré avec succès")
            messagebox.showinfo("Succès ✅", f"Template « {name} » créé dans :\n{dest}")