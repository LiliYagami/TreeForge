"""
Onglet Recaper — sélectionne un projet, choisit les exclusions, génère le .txt.
"""
from __future__ import annotations
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from treeforge.core.recaper import recap, DEFAULT_EXCLUDE_DIRS
from treeforge.utils.logger import logger


class RecaperTab(ctk.CTkFrame):
    def __init__(self, master, update_status, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._update_status = update_status
        self._build()

    def _build(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Sélection du dossier racine ──────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="Dossier racine :").grid(row=0, column=0, padx=(0, 8))
        self.root_var = ctk.StringVar(value="")
        ctk.CTkEntry(top, textvariable=self.root_var, placeholder_text="(non défini)",
                     state="readonly").grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ctk.CTkButton(top, text="Parcourir…", width=100,
                      command=self._browse_root).grid(row=0, column=2)

        # ── Dossier de sortie (optionnel) ────────────────────────────────────
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="ew")
        mid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(mid, text="Dossier de sortie :").grid(row=0, column=0, padx=(0, 8))
        self.out_var = ctk.StringVar(value="")
        ctk.CTkEntry(mid, textvariable=self.out_var,
                     placeholder_text="(par défaut : <racine>/recaps/)",
                     state="readonly").grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ctk.CTkButton(mid, text="Changer…", width=100,
                      command=self._browse_output).grid(row=0, column=2)

        # ── Exclusions ───────────────────────────────────────────────────────
        excl_frame = ctk.CTkFrame(self, fg_color="transparent")
        excl_frame.grid(row=2, column=0, padx=12, pady=(0, 6), sticky="nsew")
        excl_frame.grid_columnconfigure(0, weight=1)
        excl_frame.grid_rowconfigure(1, weight=1)

        excl_header = ctk.CTkFrame(excl_frame, fg_color="transparent")
        excl_header.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(excl_header, text="Dossiers exclus (un par ligne) :").pack(side="left")
        ctk.CTkButton(excl_header, text="Réinitialiser", width=100,
                      command=self._reset_exclusions).pack(side="right")

        self.excl_box = ctk.CTkTextbox(excl_frame, font=("Consolas", 12), height=120)
        self.excl_box.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self._reset_exclusions()

        # ── Bouton Recaper ───────────────────────────────────────────────────
        ctk.CTkButton(
            self, text="Générer le recap .txt", height=36,
            fg_color="#1565c0", hover_color="#0d47a1",
            command=self._run_recap
        ).grid(row=3, column=0, padx=12, pady=(6, 12), sticky="ew")

    def _browse_root(self):
        path = filedialog.askdirectory(title="Sélectionner le dossier racine du projet")
        if path:
            self.root_var.set(path)
            self._update_status(f"Recaper — racine : {path}")

    def _browse_output(self):
        path = filedialog.askdirectory(title="Sélectionner le dossier de sortie")
        if path:
            self.out_var.set(path)

    def _reset_exclusions(self):
        self.excl_box.delete("1.0", "end")
        self.excl_box.insert("1.0", "\n".join(sorted(DEFAULT_EXCLUDE_DIRS)))

    def _get_exclusions(self) -> set[str]:
        raw = self.excl_box.get("1.0", "end-1c")
        return {line.strip() for line in raw.splitlines() if line.strip()}

    def _run_recap(self):
        root = self.root_var.get().strip()
        if not root:
            messagebox.showwarning("TreeForge", "Sélectionnez un dossier racine.")
            return

        out_dir  = self.out_var.get().strip() or None
        excl     = self._get_exclusions()

        self._update_status("Génération du recap en cours…")
        logger.info(f"Recaper → {root}")

        def _run():
            try:
                out_path = recap(
                    root, output_dir=out_dir,
                    exclude_dirs=excl,
                    on_progress=lambda m: logger.info(f"  {m}"),
                )
                self.after(0, self._on_done, str(out_path))
            except Exception as e:
                self.after(0, self._on_error, str(e))

        threading.Thread(target=_run, daemon=True).start()

    def _on_done(self, out_path: str):
        self._update_status(f"✅ Recap généré → {out_path}")
        logger.info(f"✅ Recap généré : {out_path}")
        messagebox.showinfo(
            "Recap généré ✅",
            f"Le fichier a été créé :\n{out_path}\n\nCopiez-le dans votre IA !"
        )

    def _on_error(self, msg: str):
        self._update_status(f"❌ Erreur : {msg}")
        logger.error(f"Erreur Recaper : {msg}")
        messagebox.showerror("Erreur", msg)