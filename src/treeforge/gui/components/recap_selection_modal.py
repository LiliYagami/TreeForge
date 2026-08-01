"""
RecapSelectionModal — fenêtre Toplevel de sélection avant recap : affiche
l'arborescence réelle du dossier source (core.recaper.scan_tree), permet
d'exclure des fichiers/dossiers (Espace/clic droit/case à cocher, même
composant PreviewTree que côté Générer), et estime la taille du recap
résultant en direct.

Usage :
    from treeforge.gui.components.recap_selection_modal import RecapSelectionModal
    from treeforge.core.recaper import scan_tree

    nodes = scan_tree(root, exclude_dirs=excl)
    RecapSelectionModal(self, nodes, on_confirm=self._proceed_with_selection)
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from treeforge.core.models import TreeNode
from treeforge.core.recaper import _is_text_file
from treeforge.gui.components.preview_tree import PreviewTree
from treeforge.gui.components.modal_base import ModalToplevel


def _estimate_tokens(nodes: list[TreeNode]) -> tuple[int, int]:
    """
    Parcourt les nœuds non exclus et retourne (nb_fichiers_texte_inclus,
    tokens_estimés). N'utilise que TreeNode.size (octets, rempli par
    scan_tree pour les fichiers texte) — approximation //4, pas un vrai
    tokenizer, juste de quoi se faire une idée avant de coller dans un chat IA.
    """
    nb_files = 0
    total_size = 0

    def _walk(node: TreeNode) -> None:
        nonlocal nb_files, total_size
        if node.excluded:
            return
        if node.is_dir:
            for child in node.children:
                _walk(child)
        elif _is_text_file(Path(node.name)):
            nb_files += 1
            total_size += node.size

    for n in nodes:
        _walk(n)

    return nb_files, total_size // 4


class RecapSelectionModal(ModalToplevel):
    """
    Paramètres
    ----------
    master     : widget parent
    nodes      : list[TreeNode] retournée par core.recaper.scan_tree()
    on_confirm : callback(nodes) appelé si l'utilisateur clique Continuer
                 (les TreeNode.excluded reflètent déjà les cases décochées)
    on_cancel  : callback optionnel si annulation
    """

    def __init__(
        self,
        master,
        nodes: list[TreeNode],
        on_confirm: Callable[[list[TreeNode]], None],
        on_cancel: Callable[[], None] | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._nodes      = nodes
        self._on_confirm = on_confirm
        self._on_cancel  = on_cancel

        self.title("TreeForge — Sélection avant Recap")
        self.geometry("620x600")
        self.minsize(480, 420)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._build()
        self._load()
        self._update_estimate()

        self._start_show_sequence()

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
            text="Choisissez ce qui doit entrer dans le recap (Espace/Clic droit pour exclure)",
            font=("Consolas", 13, "bold"),
            anchor="w",
            wraplength=380,
            justify="left",
        ).grid(row=0, column=0, padx=16, pady=10, sticky="w")

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

        # ── Arbre de sélection ───────────────────────────────────────────
        self._ptree = PreviewTree(
            self,
            stats_suffix="sélectionné(s)",
            on_toggle=self._update_estimate,
        )
        self._ptree.grid(row=1, column=0, sticky="nsew")

        # ── Estimation de taille ─────────────────────────────────────────
        self._estimate_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            self,
            textvariable=self._estimate_var,
            font=("Consolas", 11),
            text_color=("#1a5c8c", "#4da6ff"),
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
            footer, text="✔  Continuer", height=36,
            fg_color="#1565c0", hover_color="#0d47a1",
            font=("Consolas", 13, "bold"),
            command=self._confirm,
        ).grid(row=0, column=1, sticky="e")

    def _load(self):
        self._ptree.load(self._nodes)

    def _update_estimate(self):
        nb_files, tokens = _estimate_tokens(self._nodes)
        self._estimate_var.set(
            f"≈ {tokens:,} tokens estimés (grossier)  ·  {nb_files} fichier(s) texte inclus"
            .replace(",", " ")
        )

    # ── Actions ───────────────────────────────────────────────────────────

    def _confirm(self):
        self._close()
        self.destroy()
        self._on_confirm(self._nodes)

    def _cancel(self):
        self._close()
        self.destroy()
        if self._on_cancel:
            self._on_cancel()
