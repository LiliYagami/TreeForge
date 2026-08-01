"""
Composant PreviewTree — affiche une arborescence TreeNode dans un widget
Treeview tkinter enrichi avec icônes 📁 / 📄, couleurs et scrollbars.

Utilisable standalone ou embarqué dans un Frame parent.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Sequence

import customtkinter as ctk

from treeforge.core.models import TreeNode


# ── Palette selon le thème CTk ───────────────────────────────────────────────
def _colors() -> dict:
    dark = ctk.get_appearance_mode() == "Dark"
    return {
        "bg":          "#1e1e2e" if dark else "#f5f5f7",
        "bg_alt":      "#2a2a3e" if dark else "#ebebef",
        "fg":          "#cdd6f4" if dark else "#1c1c1e",
        "fg_dir":      "#89b4fa" if dark else "#1a6fc4",
        "fg_file":     "#a6e3a1" if dark else "#2d6a2d",
        "select_bg":   "#313244" if dark else "#c8d8f0",
        "border":      "#45475a" if dark else "#c0c0cc",
        "scrollbar":   "#585b70" if dark else "#b0b0be",
        "count":       "#6c7086" if dark else "#5c5c66",
        "excluded":    "#6c7086" if dark else "#6b6b72",
    }


class PreviewTree(ctk.CTkFrame):
    """
    Widget réutilisable : prend une liste de TreeNode et les affiche
    dans un Treeview tkinter avec icônes, couleurs et compteurs.
    """

    def __init__(
        self,
        master,
        stats_suffix: str = "à générer",
        on_toggle: Callable[[], None] | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._c = _colors()
        self._nb_dirs  = 0
        self._nb_files = 0
        self._stats_suffix = stats_suffix
        self._on_toggle = on_toggle

        self._build()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Barre de stats ────────────────────────────────────────────────
        self._stats_var = tk.StringVar(value="")
        stats = ctk.CTkLabel(
            self, textvariable=self._stats_var,
            font=("Consolas", 11),
            text_color=self._c["count"],
            anchor="w",
        )
        stats.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 0))

        # ── Treeview + scrollbars ─────────────────────────────────────────
        tree_frame = tk.Frame(self, bg=self._c["bg"])
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(4, 8))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style_name = "TFPreview.Treeview"
        style.theme_use("default")
        style.configure(
            style_name,
            background=self._c["bg"],
            foreground=self._c["fg"],
            fieldbackground=self._c["bg"],
            borderwidth=0,
            font=("Consolas", 12),
            rowheight=24,
        )
        style.configure(f"{style_name}.Heading",
                        background=self._c["bg_alt"],
                        foreground=self._c["fg"],
                        font=("Consolas", 11, "bold"))
        style.map(style_name,
                  background=[("selected", self._c["select_bg"])],
                  foreground=[("selected", self._c["fg"])])

        self._tree = ttk.Treeview(
            tree_frame,
            style=style_name,
            show="tree",          # pas de colonne header
            selectmode="browse",
        )
        self._tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar verticale
        vsb = ctk.CTkScrollbar(tree_frame, orientation="vertical",
                               command=self._tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=vsb.set)

        # Scrollbar horizontale
        hsb = ctk.CTkScrollbar(self, orientation="horizontal",
                               command=self._tree.xview)
        hsb.grid(row=2, column=0, sticky="ew", padx=(8, 0))
        self._tree.configure(xscrollcommand=hsb.set)

        # Tags de couleur
        self._tree.tag_configure("dir",  foreground=self._c["fg_dir"])
        self._tree.tag_configure("file", foreground=self._c["fg_file"])
        self._tree.tag_configure("excluded", foreground=self._c["excluded"])

        # Double-clic → expand/collapse les dossiers
        self._tree.bind("<Double-1>", self._on_double_click)
        # Espace → exclure / inclure l'élément
        self._tree.bind("<space>", self._on_space_toggle)
        # Clic droit → menu contextuel
        self._tree.bind("<Button-3>", self._on_right_click)


    # ── API publique ──────────────────────────────────────────────────────────

    def load(self, nodes: Sequence[TreeNode]) -> None:
        """Vide l'arbre et charge une nouvelle liste de nœuds racines."""
        self._tree.delete(*self._tree.get_children())
        self._nb_dirs  = 0
        self._nb_files = 0
        self._item_to_node = {}

        for node in nodes:
            self._insert_node("", node)

        # Développer le premier niveau automatiquement
        for child in self._tree.get_children():
            self._tree.item(child, open=True)

        self._update_stats()

    def clear(self) -> None:
        self._tree.delete(*self._tree.get_children())
        self._nb_dirs  = 0
        self._nb_files = 0
        self._item_to_node = {}
        self._stats_var.set("")


    def expand_all(self) -> None:
        self._set_open_all(True)

    def collapse_all(self) -> None:
        self._set_open_all(False)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _insert_node(self, parent_id: str, node: TreeNode) -> str:
        if node.is_dir:
            icon  = "📁"
            tag   = "dir"
            label = f"{icon}  {node.name}/"
            self._nb_dirs += 1
        else:
            icon  = "📄"
            tag   = "file"
            label = f"{icon}  {node.name}"
            self._nb_files += 1

        item_id = self._tree.insert(
            parent_id, "end",
            text=label,
            open=False,
            tags=(tag,),
        )
        self._item_to_node[item_id] = node

        for child in node.children:
            self._insert_node(item_id, child)

        return item_id

    def _update_stats(self) -> None:
        # Re-calculer les dossiers et fichiers inclus
        nb_dirs = 0
        nb_files = 0
        for node in self._item_to_node.values():
            if not node.excluded:
                if node.is_dir:
                    nb_dirs += 1
                else:
                    nb_files += 1
        self._stats_var.set(
            f"  📁 {nb_dirs} dossier(s)   📄 {nb_files} fichier(s) {self._stats_suffix}"
        )

    def _on_double_click(self, event) -> None:
        item = self._tree.focus()
        if not item:
            return
        is_open = self._tree.item(item, "open")
        self._tree.item(item, open=not is_open)

    def _on_space_toggle(self, event) -> str:
        item = self._tree.focus()
        if not item:
            return "break"
        node = self._item_to_node.get(item)
        if not node:
            return "break"
        new_state = not node.excluded
        self._toggle_node_exclusion(item, node, new_state)
        self._update_stats()
        if self._on_toggle:
            self._on_toggle()
        return "break"

    def _on_right_click(self, event) -> None:
        iid = self._tree.identify_row(event.y)
        if not iid:
            return
        self._tree.focus(iid)
        self._tree.selection_set(iid)

        node = self._item_to_node.get(iid)
        if not node:
            return

        menu = tk.Menu(self, tearoff=0)
        label = "Inclure cet élément" if node.excluded else "Exclure cet élément"
        menu.add_command(label=label, command=lambda: self._toggle_item_from_menu(iid, node))
        menu.post(event.x_root, event.y_root)

    def _toggle_item_from_menu(self, iid: str, node: TreeNode) -> None:
        new_state = not node.excluded
        self._toggle_node_exclusion(iid, node, new_state)
        self._update_stats()
        if self._on_toggle:
            self._on_toggle()

    def _toggle_node_exclusion(self, item_id: str, node: TreeNode, excluded: bool) -> None:
        node.excluded = excluded
        
        tags = list(self._tree.item(item_id, "tags"))
        if excluded:
            if "excluded" not in tags:
                tags.append("excluded")
        else:
            if "excluded" in tags:
                tags.remove("excluded")
        self._tree.item(item_id, tags=tuple(tags))
        
        for child_id in self._tree.get_children(item_id):
            child_node = self._item_to_node.get(child_id)
            if child_node:
                self._toggle_node_exclusion(child_id, child_node, excluded)

    def _set_open_all(self, state: bool) -> None:
        def walk(item):
            self._tree.item(item, open=state)
            for child in self._tree.get_children(item):
                walk(child)
        for root in self._tree.get_children():
            walk(root)