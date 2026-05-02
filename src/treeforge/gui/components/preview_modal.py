"""
PreviewModal — fenêtre Toplevel qui affiche le PreviewTree + bouton Générer.

Usage depuis generator_tab.py :
    from treeforge.gui.components.preview_modal import PreviewModal

    def _analyze(self):
        ...
        result = parse(text, mode)
        if result.ok:
            PreviewModal(self, result, dest_callback=self._generate_from_modal)
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Sequence

import customtkinter as ctk

from treeforge.core.models import TreeNode, ParseResult
from treeforge.gui.components.preview_tree import PreviewTree, _colors


class PreviewModal(ctk.CTkToplevel):
    """
    Fenêtre modale de prévisualisation.

    Paramètres
    ----------
    master          : widget parent (GeneratorTab)
    parse_result    : ParseResult à afficher
    on_confirm      : callback(parse_result) appelé si l'utilisateur clique Générer
    on_cancel       : callback optionnel si annulation
    """

    def __init__(
        self,
        master,
        parse_result: ParseResult,
        on_confirm: Callable[[ParseResult], None],
        on_cancel:  Callable[[], None] | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._result    = parse_result
        self._on_confirm = on_confirm
        self._on_cancel  = on_cancel
        self._c = _colors()

        # ── Fenêtre ───────────────────────────────────────────────────────
        self.title("TreeForge — Aperçu de l'arborescence")
        self.geometry("620x580")
        self.minsize(480, 400)
        self.resizable(True, True)

        # Surplombe la fenêtre principale
        self.transient(master)
        self.grab_set()           # bloque les clics sur la fenêtre parente
        self.lift()
        self.focus_force()

        # Fermeture via croix = annulation
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._build()
        self._load()

        # Centrage par rapport au parent
        self.after(50, self._center)

    # ── Construction ─────────────────────────────────────────────────────

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── En-tête ───────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=("gray88", "gray22"), corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Vérifiez l'arborescence avant de générer",
            font=("Consolas", 13, "bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=16, pady=10, sticky="w")

        # Boutons expand / collapse
        btn_bar = ctk.CTkFrame(header, fg_color="transparent")
        btn_bar.grid(row=0, column=1, padx=12)

        ctk.CTkButton(
            btn_bar, text="⊞ Tout ouvrir", width=110, height=28,
            fg_color="transparent", border_width=1,
            text_color=("gray30", "gray80"),
            hover_color=("gray80", "gray30"),
            command=lambda: self._ptree.expand_all(),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_bar, text="⊟ Tout fermer", width=110, height=28,
            fg_color="transparent", border_width=1,
            text_color=("gray30", "gray80"),
            hover_color=("gray80", "gray30"),
            command=lambda: self._ptree.collapse_all(),
        ).pack(side="left")

        # ── Arbre ─────────────────────────────────────────────────────────
        self._ptree = PreviewTree(self)
        self._ptree.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # ── Avertissements éventuels ──────────────────────────────────────
        if self._result.warnings:
            warn_text = "⚠️  " + "   |   ".join(self._result.warnings[:3])
            ctk.CTkLabel(
                self,
                text=warn_text,
                font=("Consolas", 11),
                text_color=("#b45309", "#fbbf24"),
                wraplength=580,
                justify="left",
                anchor="w",
            ).grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 0))

        # ── Boutons bas ───────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=12)
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            footer, text="✕  Annuler", width=120, height=36,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray70"),
            hover_color=("gray85", "gray25"),
            command=self._cancel,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer, text="✔  Générer la structure", height=36,
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=("Consolas", 13, "bold"),
            command=self._confirm,
        ).grid(row=0, column=1, sticky="e")

    # ── Chargement ────────────────────────────────────────────────────────

    def _load(self):
        self._ptree.load(self._result.nodes)

    # ── Actions ───────────────────────────────────────────────────────────

    def _confirm(self):
        self.grab_release()
        self.destroy()
        self._on_confirm(self._result)

    def _cancel(self):
        self.grab_release()
        self.destroy()
        if self._on_cancel:
            self._on_cancel()

    # ── Centrage ──────────────────────────────────────────────────────────

    def _center(self):
        self.update_idletasks()
        pw = self.master.winfo_width()
        ph = self.master.winfo_height()
        px = self.master.winfo_rootx()
        py = self.master.winfo_rooty()
        w  = self.winfo_width()
        h  = self.winfo_height()
        x  = px + (pw - w) // 2
        y  = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")