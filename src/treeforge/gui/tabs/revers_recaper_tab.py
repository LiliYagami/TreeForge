"""
revers_recaper_tab.py — Onglet Restauration de projet depuis un recap .txt
"""
from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from treeforge.core.revers_recaper import extract
from treeforge.core.diff_engine import compute_plan_for_restore
from treeforge.utils.logger import logger
from treeforge.gui.components.diff_preview_modal import DiffPreviewModal


class ReversRecaperTab(ctk.CTkFrame):
    def __init__(self, parent, update_status):
        super().__init__(parent, fg_color="transparent")
        self._update_status = update_status
        self._build_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # Construction UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # ── 1. Bandeau info ───────────────────────────────────────────────────
        info = ctk.CTkFrame(self, corner_radius=8)
        info.pack(fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            info,
            text="🔄  Restauration de projet depuis un recap .txt",
            font=ctk.CTkFont(weight="bold", size=13),
            anchor="w",
        ).pack(anchor="w", padx=15, pady=(10, 2))

        ctk.CTkLabel(
            info,
            text=(
                "Prends un fichier recap généré par l'onglet Recaper "
                "(ou modifié par une IA)\n"
                "et recrée tous les fichiers du projet à l'emplacement choisi."
            ),
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=15, pady=(0, 10))

        # ── 2. Fichier recap ──────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Fichier recap (.txt) :",
            anchor="w",
        ).pack(anchor="w", padx=15, pady=(8, 0))

        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=(4, 8))
        row1.grid_columnconfigure(0, weight=1)

        self.recap_var = ctk.StringVar()
        ctk.CTkEntry(
            row1,
            textvariable=self.recap_var,
            placeholder_text="Chemin vers le fichier recap...",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            row1,
            text="Parcourir…",
            width=110,
            command=self._browse_recap,
        ).grid(row=0, column=1)

        # ── 3. Dossier destination ────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Dossier de destination :",
            anchor="w",
        ).pack(anchor="w", padx=15, pady=(0, 0))

        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=(4, 8))
        row2.grid_columnconfigure(0, weight=1)

        self.dest_var = ctk.StringVar()
        ctk.CTkEntry(
            row2,
            textvariable=self.dest_var,
            placeholder_text="Dossier où recréer les fichiers...",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            row2,
            text="Parcourir…",
            width=110,
            command=self._browse_dest,
        ).grid(row=0, column=1)

        # ── 4. Option overwrite ───────────────────────────────────────────────
        self.overwrite_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self,
            text="Écraser les fichiers existants",
            variable=self.overwrite_var,
        ).pack(anchor="w", padx=15, pady=(0, 12))

        # ── 5. Bouton Restaurer ───────────────────────────────────────────────
        self._btn_restore = ctk.CTkButton(
            self,
            text="🔄  Restaurer le projet",
            height=45,
            fg_color="#2196F3",
            hover_color="#1976D2",
            command=self._restore,
        )
        self._btn_restore.pack(fill="x", padx=15, pady=(0, 12))

        # ── 6. Barre de progression ───────────────────────────────────────────
        self._progress = ctk.CTkProgressBar(self)
        self._progress.pack(fill="x", padx=15, pady=(0, 8))
        self._progress.set(0)
        self._progress.pack_forget()   # cachée au départ

        # ── 7. Zone résultat ──────────────────────────────────────────────────
        self._result_box = ctk.CTkTextbox(
            self,
            height=160,
            state="disabled",
            wrap="word",
        )
        self._result_box.pack(fill="x", padx=15, pady=(0, 15))

    # ─────────────────────────────────────────────────────────────────────────
    # Callbacks boutons
    # ─────────────────────────────────────────────────────────────────────────

    def _browse_recap(self):
        path = filedialog.askopenfilename(
            title="Choisir un fichier recap",
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")],
        )
        if path:
            self.recap_var.set(path)

    def _browse_dest(self):
        path = filedialog.askdirectory(title="Choisir le dossier de destination")
        if path:
            self.dest_var.set(path)

    # ─────────────────────────────────────────────────────────────────────────
    # Restauration
    # ─────────────────────────────────────────────────────────────────────────

    def _restore(self):
        recap = self.recap_var.get().strip()
        dest  = self.dest_var.get().strip()

        # ── Validations ───────────────────────────────────────────────────────
        if not recap:
            messagebox.showwarning("TreeForge", "Aucun fichier recap sélectionné.")
            return
        if not dest:
            messagebox.showwarning("TreeForge", "Aucun dossier de destination sélectionné.")
            return
        recap_path = Path(recap)
        if not recap_path.exists():
            messagebox.showerror("TreeForge", f"Fichier introuvable :\n{recap}")
            return

        dest_path = Path(dest)
        if dest_path.exists():
            existing = [p for p in dest_path.iterdir() if not p.name.startswith(".")]
            if existing:
                # Dossier non vide → calcul du plan et validation via la modale de diff
                # plutôt que le seul interrupteur global "Écraser les fichiers existants".
                try:
                    text = recap_path.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    messagebox.showerror("TreeForge", f"Impossible de lire le recap :\n{e}")
                    return
                plan = compute_plan_for_restore(text, dest_path)
                DiffPreviewModal(
                    self, plan,
                    on_confirm=lambda p: self._launch_restore(recap_path, dest_path, p),
                    on_cancel=self._restore_cancelled,
                )
                return

        self._launch_restore(recap_path, dest_path, plan=None)

    def _restore_cancelled(self):
        self._update_status("Restauration annulee — dossier non ecrase")
        logger.info("ReversRecaper — restauration annulee par l'utilisateur (plan refuse)")

    def _launch_restore(self, recap_path: Path, dest_path: Path, plan):
        overwrite = self.overwrite_var.get()

        # ── UI : état "en cours" ──────────────────────────────────────────────
        self._set_result("")
        self._btn_restore.configure(state="disabled", text="⏳  Restauration…")
        self._progress.pack(fill="x", padx=15, pady=(0, 8))
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        self._update_status("Restauration en cours…")
        logger.info("ReversRecaper — démarrage : %s → %s", recap_path, dest_path)

        # ── Thread ────────────────────────────────────────────────────────────
        threading.Thread(
            target=self._run,
            args=(recap_path, dest_path, overwrite, plan),
            daemon=True,
        ).start()

    def _run(self, recap_path: Path, dest_dir: Path, overwrite: bool, plan):
        """Exécuté dans un thread secondaire."""
        try:
            result = extract(recap_path, dest_dir, overwrite=overwrite, plan=plan)
        except Exception as e:
            logger.exception("ReversRecaper — erreur inattendue")
            self.after(0, self._on_error, str(e))
            return

        self.after(0, self._on_done, result)

    # ─────────────────────────────────────────────────────────────────────────
    # Callbacks retour thread → UI  (appelés via self.after)
    # ─────────────────────────────────────────────────────────────────────────

    def _on_done(self, result):
        """Appelé dans le thread principal après extraction."""
        # Arrêt progress bar
        self._progress.stop()
        self._progress.pack_forget()
        self._btn_restore.configure(state="normal", text="🔄  Restaurer le projet")

        summary = result.summary()
        logger.info("ReversRecaper — terminé\n%s", summary)

        if result.success:
            self._update_status(
                f"✅ {len(result.files_created)} fichier(s) restauré(s)"
            )
        else:
            self._update_status(
                f"⚠️ {len(result.files_created)} créé(s), "
                f"{len(result.errors)} erreur(s)"
            )

        self._set_result(summary)

    def _on_error(self, msg: str):
        """Appelé en cas d'exception non gérée dans le thread."""
        self._progress.stop()
        self._progress.pack_forget()
        self._btn_restore.configure(state="normal", text="🔄  Restaurer le projet")
        self._update_status("❌ Erreur inattendue")
        self._set_result(f"❌ Erreur inattendue :\n{msg}")
        logger.error("ReversRecaper — %s", msg)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers UI
    # ─────────────────────────────────────────────────────────────────────────

    def _set_result(self, text: str):
        """Écrit dans la zone résultat (thread-safe via after)."""
        self._result_box.configure(state="normal")
        self._result_box.delete("1.0", "end")
        if text:
            self._result_box.insert("1.0", text)
        self._result_box.configure(state="disabled")
