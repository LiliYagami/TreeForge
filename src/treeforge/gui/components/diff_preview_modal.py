"""
DiffPreviewModal — fenêtre Toplevel qui affiche un GenerationPlan avant écriture
disque : Nouveaux / Modifiés / Inchangés, avec case à cocher par item et diff
unifié consultable pour les fichiers modifiés.

Usage :
    from treeforge.gui.components.diff_preview_modal import DiffPreviewModal

    plan = compute_plan_for_generate(result, dest, content_mode)
    DiffPreviewModal(self, plan, on_confirm=self._apply_plan)
"""
from __future__ import annotations

import difflib
from typing import Callable

import customtkinter as ctk

from treeforge.core.diff_engine import GenerationPlan, PlanItem
from treeforge.gui.components.modal_base import ModalToplevel

_GREEN  = ("#1b6b2e", "#66bb6a")
_ORANGE = ("#b45309", "#fbbf24")
_GRAY   = ("gray40", "gray60")


class DiffPreviewModal(ModalToplevel):
    """
    Paramètres
    ----------
    master     : widget parent
    plan       : GenerationPlan calculé par core.diff_engine
    on_confirm : callback(plan) appelé si l'utilisateur clique Appliquer
                 (les PlanItem.included reflètent déjà les cases décochées)
    on_cancel  : callback optionnel si annulation
    """

    def __init__(
        self,
        master,
        plan: GenerationPlan,
        on_confirm: Callable[[GenerationPlan], None],
        on_cancel: Callable[[], None] | None = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._plan       = plan
        self._on_confirm = on_confirm
        self._on_cancel  = on_cancel

        self.title("TreeForge — Vérifier les changements")
        self.geometry("640x600")
        self.minsize(500, 420)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._build()
        self._start_show_sequence()

    # ── Construction ─────────────────────────────────────────────────────

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        n_new, n_mod, n_unc = len(self._plan.new), len(self._plan.modified), len(self._plan.unchanged)

        # ── En-tête ───────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=("gray88", "gray22"), corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Vérifiez les changements avant application",
            font=("Consolas", 13, "bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=16, pady=(10, 2), sticky="w")

        ctk.CTkLabel(
            header,
            text=f"🆕 {n_new} nouveau(x)    ✏️ {n_mod} modifié(s)    ✅ {n_unc} inchangé(s)",
            font=("Consolas", 11),
            anchor="w",
            text_color=("gray30", "gray70"),
        ).grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")

        # ── Liste scrollable ──────────────────────────────────────────────
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 0))
        body.grid_columnconfigure(0, weight=1)

        row = 0
        if self._plan.new:
            row = self._section(body, row, "🆕 Nouveaux", _GREEN, self._plan.new, diffable=False)
        if self._plan.modified:
            row = self._section(body, row, "✏️ Modifiés", _ORANGE, self._plan.modified, diffable=True)
        if self._plan.unchanged:
            row = self._section(body, row, "✅ Inchangés (rien à faire)", _GRAY, self._plan.unchanged, diffable=False, checkable=False)

        if not self._plan.items:
            ctk.CTkLabel(
                body, text="Rien à générer.", font=("Consolas", 12),
                text_color=("gray40", "gray60"),
            ).grid(row=0, column=0, padx=12, pady=20)

        # ── Boutons bas ───────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=12)
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            footer, text="✕  Annuler", width=120, height=36,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray70"),
            hover_color=("gray85", "gray25"),
            command=self._cancel,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer, text="✔  Appliquer", height=36,
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=("Consolas", 13, "bold"),
            command=self._confirm,
        ).grid(row=0, column=1, sticky="e")

    def _section(
        self, parent, row: int, title: str, color: tuple,
        items: list[PlanItem], diffable: bool, checkable: bool = True,
    ) -> int:
        ctk.CTkLabel(
            parent, text=title, font=("Consolas", 12, "bold"),
            text_color=color, anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=8, pady=(10, 2))
        row += 1

        for item in items:
            line = ctk.CTkFrame(parent, fg_color="transparent")
            line.grid(row=row, column=0, sticky="ew", padx=8, pady=1)
            line.grid_columnconfigure(0, weight=1)

            icon = "📁" if item.is_dir else "📄"
            label = f"{icon}  {item.rel_path}"

            if checkable:
                var = ctk.BooleanVar(value=item.included)
                var.trace_add("write", lambda *_a, it=item, v=var: setattr(it, "included", v.get()))
                ctk.CTkCheckBox(
                    line, text=label, variable=var,
                    font=("Consolas", 11),
                ).grid(row=0, column=0, sticky="w")
            else:
                ctk.CTkLabel(
                    line, text=label, font=("Consolas", 11),
                    text_color=("gray40", "gray60"), anchor="w",
                ).grid(row=0, column=0, sticky="w", padx=(2, 0))

            if diffable and not item.is_dir:
                ctk.CTkButton(
                    line, text="Voir le diff", width=90, height=22,
                    font=("Consolas", 10),
                    fg_color="transparent", border_width=1,
                    text_color=("gray30", "gray80"),
                    hover_color=("gray80", "gray30"),
                    command=lambda it=item: self._show_diff(it),
                ).grid(row=0, column=1, sticky="e", padx=(6, 0))

            row += 1

        return row

    # ── Diff unifié ───────────────────────────────────────────────────────

    def _show_diff(self, item: PlanItem):
        popup = ctk.CTkToplevel(self)
        popup.title(f"Diff — {item.rel_path}")
        popup.geometry("700x500")
        popup.transient(self)

        box = ctk.CTkTextbox(popup, font=("Consolas", 11), wrap="none")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        old_lines = (item.old_content or "").splitlines(keepends=True)
        new_lines = (item.new_content or "").splitlines(keepends=True)
        diff_lines = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"disque/{item.rel_path}",
            tofile=f"nouveau/{item.rel_path}",
        )

        box.tag_config("add", foreground="#2e7d32")
        box.tag_config("del", foreground="#c62828")
        box.tag_config("hunk", foreground="#1565c0")

        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                box.insert("end", line, "add")
            elif line.startswith("-") and not line.startswith("---"):
                box.insert("end", line, "del")
            elif line.startswith("@@"):
                box.insert("end", line, "hunk")
            else:
                box.insert("end", line)
            if not line.endswith("\n"):
                box.insert("end", "\n")

        box.configure(state="disabled")
        popup.after(50, popup.lift)

    # ── Actions ───────────────────────────────────────────────────────────

    def _confirm(self):
        self._close()
        self.destroy()
        self._on_confirm(self._plan)

    def _cancel(self):
        self._close()
        self.destroy()
        if self._on_cancel:
            self._on_cancel()
