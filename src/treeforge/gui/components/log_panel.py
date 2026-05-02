"""Panneau de logs réutilisable."""
from __future__ import annotations
import customtkinter as ctk


class LogPanel(ctk.CTkFrame):

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            height=160,
            fg_color=("gray92", "gray20"),
            **kwargs,
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Barre titre ───────────────────────────────────────────────────────
        bar = ctk.CTkFrame(self, fg_color="transparent", height=28)
        bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 0))
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_propagate(False)

        ctk.CTkLabel(
            bar,
            text="Logs",
            font=ctk.CTkFont(weight="bold", size=12),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            bar,
            text="Effacer",
            width=72,
            height=24,
            fg_color="transparent",
            border_width=1,
            border_color=("gray70", "gray40"),
            hover_color=("gray85", "gray30"),
            font=ctk.CTkFont(size=11),
            command=self.clear,
        ).grid(row=0, column=1, sticky="e")

        # ── Zone texte ────────────────────────────────────────────────────────
        self.textbox = ctk.CTkTextbox(
            self,
            font=("Consolas", 12),
            state="disabled",
            fg_color="transparent",
            text_color=("gray20", "gray80"),
        )
        self.textbox.grid(
            row=1, column=0,
            padx=10, pady=(2, 8),
            sticky="nsew",
        )

    # ─────────────────────────────────────────────────────────────────────────

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")

    def append(self, text: str):
        """Ajoute une ligne — appelé par le logger handler."""
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")
