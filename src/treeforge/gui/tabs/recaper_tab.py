"""
Onglet Recaper — sélectionne un projet, choisit les exclusions, génère le .txt.
"""
from __future__ import annotations
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from treeforge.core.recaper import recap, recap_text, scan_tree, included_paths_from_tree, DEFAULT_EXCLUDE_DIRS
from treeforge.utils.logger import logger
from treeforge.gui.components.recap_selection_modal import RecapSelectionModal


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
        self.root_entry = ctk.CTkEntry(top, textvariable=self.root_var, placeholder_text="(non défini)",
                     state="normal")
        self.root_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.root_entry.bind("<Key>", lambda e: "break")
        ctk.CTkButton(top, text="Parcourir…", width=100,
                      command=self._browse_root).grid(row=0, column=2)

        # ── Dossier de sortie (optionnel) ────────────────────────────────────
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="ew")
        mid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(mid, text="Dossier de sortie :").grid(row=0, column=0, padx=(0, 8))
        self.out_var = ctk.StringVar(value="")
        self.out_entry = ctk.CTkEntry(mid, textvariable=self.out_var,
                     placeholder_text="(par défaut : <racine>/recaps/)",
                     state="normal")
        self.out_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.out_entry.bind("<Key>", lambda e: "break")
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

        self.excl_box = ctk.CTkTextbox(
            excl_frame, font=("Consolas", 12), height=120,
            fg_color=("white", "gray16"),
        )
        self.excl_box.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self._reset_exclusions()

        # ── Boutons Recaper ───────────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=3, column=0, padx=12, pady=(6, 12), sticky="ew")
        btn_bar.grid_columnconfigure(0, weight=1)
        btn_bar.grid_columnconfigure(1, weight=1)

        self._btn_recap = ctk.CTkButton(
            btn_bar, text="📄  Générer le fichier .txt", height=36,
            fg_color="#1565c0", hover_color="#0d47a1",
            command=self._run_recap
        )
        self._btn_recap.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self._btn_copy = ctk.CTkButton(
            btn_bar, text="📋  Copier dans le presse-papiers", height=36,
            fg_color="transparent", border_width=1,
            text_color=("gray15", "gray90"),
            hover_color=("gray85", "gray25"),
            command=self._run_recap_clipboard
        )
        self._btn_copy.grid(row=0, column=1, padx=(6, 0), sticky="ew")


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

    def _get_root_or_warn(self) -> str | None:
        root = self.root_var.get().strip()
        if not root:
            messagebox.showwarning("TreeForge", "Sélectionnez un dossier racine.")
            return None
        return root

    def _set_buttons_state(self, state: str):
        self._btn_recap.configure(state=state)
        self._btn_copy.configure(state=state)

    def _run_recap(self):
        root = self._get_root_or_warn()
        if not root:
            return
        self._prepare_selection(root, mode="file")

    def _run_recap_clipboard(self):
        root = self._get_root_or_warn()
        if not root:
            return
        self._prepare_selection(root, mode="clipboard")

    # ── Sélection avant recap ────────────────────────────────────────────────

    def _prepare_selection(self, root: str, mode: str):
        """Scanne le dossier en arrière-plan puis ouvre la modale de sélection."""
        excl = self._get_exclusions()
        self._update_status("Analyse du dossier…")
        self._set_buttons_state("disabled")

        def _scan():
            try:
                nodes = scan_tree(root, exclude_dirs=excl)
            except Exception as e:
                self.after(0, self._on_error, str(e))
                return
            self.after(0, self._on_scan_done, nodes, root, mode)

        threading.Thread(target=_scan, daemon=True).start()

    def _on_scan_done(self, nodes: list, root: str, mode: str):
        self._set_buttons_state("normal")
        if not nodes:
            messagebox.showinfo(
                "TreeForge",
                "Aucun fichier ou dossier trouvé (ou tout est déjà exclu)."
            )
            return
        RecapSelectionModal(
            self, nodes,
            on_confirm=lambda selected: self._on_selection_confirmed(selected, root, mode),
            on_cancel=lambda: self._update_status("Recap annulé — sélection non validée"),
        )

    def _on_selection_confirmed(self, nodes: list, root: str, mode: str):
        include_paths = included_paths_from_tree(nodes)
        if mode == "file":
            self._launch_recap_file(root, include_paths)
        else:
            self._launch_recap_clipboard(root, include_paths)

    # ── Lancement effectif ───────────────────────────────────────────────────

    def _launch_recap_file(self, root: str, include_paths: set[str]):
        out_dir = self.out_var.get().strip() or None
        excl    = self._get_exclusions()

        self._update_status("Génération du recap en cours…")
        logger.info(f"Recaper → {root}")
        self._set_buttons_state("disabled")

        def _run():
            try:
                out_path = recap(
                    root, output_dir=out_dir,
                    exclude_dirs=excl,
                    include_paths=include_paths,
                    on_progress=lambda m: logger.info(f"  {m}"),
                )
                self.after(0, self._on_done, str(out_path))
            except Exception as e:
                self.after(0, self._on_error, str(e))

        threading.Thread(target=_run, daemon=True).start()

    def _launch_recap_clipboard(self, root: str, include_paths: set[str]):
        excl = self._get_exclusions()

        self._update_status("Génération du recap en cours (presse-papiers)…")
        logger.info(f"Recaper (presse-papiers) → {root}")
        self._set_buttons_state("disabled")

        def _run():
            try:
                text, resolved_root = recap_text(
                    root, exclude_dirs=excl,
                    include_paths=include_paths,
                    on_progress=lambda m: logger.info(f"  {m}"),
                )
                self.after(0, self._on_copy_done, text, str(resolved_root))
            except Exception as e:
                self.after(0, self._on_error, str(e))

        threading.Thread(target=_run, daemon=True).start()

    def _on_done(self, out_path: str):
        self._set_buttons_state("normal")
        self._update_status(f"✅ Recap généré → {out_path}")
        logger.info(f"✅ Recap généré : {out_path}")
        messagebox.showinfo(
            "Recap généré ✅",
            f"Le fichier a été créé :\n{out_path}\n\nCopiez-le dans votre IA !"
        )

    def _on_copy_done(self, text: str, root: str):
        self._set_buttons_state("normal")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()  # garantit que le presse-papiers garde le contenu
        nb_lines = text.count("\n") + 1
        self._update_status(f"✅ Recap copié dans le presse-papiers ({nb_lines} lignes)")
        logger.info(f"✅ Recap copié dans le presse-papiers : {root}")
        messagebox.showinfo(
            "Recap copié ✅",
            f"Le recap de « {root} » a été copié dans le presse-papiers.\n\n"
            f"Collez-le directement dans votre IA !"
        )

    def _on_error(self, msg: str):
        self._set_buttons_state("normal")
        self._update_status(f"❌ Erreur : {msg}")
        logger.error(f"Erreur Recaper : {msg}")
        messagebox.showerror("Erreur", msg)