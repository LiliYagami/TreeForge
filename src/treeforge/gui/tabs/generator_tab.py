"""
Onglet Générateur — version finale avec toutes les features.

Features :
  - Détection chemin absolu en première ligne (Gemini, tree /f, etc.)
  - Drag & Drop de fichiers .txt/.json (si tkinterdnd2 dispo)
  - Menu clic droit : Coller / Copier / Couper / Tout sélectionner / Effacer
  - Panneau droit CTkScrollableFrame
  - Sélecteur de format : Auto / Unicode / Windows tree /f / Indentation
  - Analyser → PreviewModal (Treeview 📁/📄)
  - Générer → génération directe sans aperçu
  - Confirmation avant overwrite si dossier non vide
  - Zone Prompt IA collapsible
  - Barre d'astuces rotative
  - user_prefs chargés au démarrage + sauvegardés automatiquement
"""
from __future__ import annotations
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from treeforge.config import MODES_PARSING, MODES_CONTENU
from treeforge.core.parser import parse
from treeforge.core.generator import generate
from treeforge.utils.logger import logger
from treeforge.utils.helpers import load_tips, load_prefs, save_prefs
from treeforge.utils.drag_drop import setup_drop_target, DND_AVAILABLE
from treeforge.utils.context_menu import attach_context_menu
from treeforge.gui.components.preview_modal import PreviewModal

# ── Constantes format ─────────────────────────────────────────────────────────

MODES_FORMAT = {
    "Auto"        : "auto",
    "Unicode ├──" : "unicode",
    "Windows tree": "wintree",
    "Indentation" : "indent",
}

FORMAT_LABELS = {
    "auto"   : "Auto",
    "unicode": "Unicode ├──",
    "wintree": "Windows tree",
    "indent" : "Indentation",
}

FORMAT_DETECTED_LABELS = {
    "unicode": "Unicode ├──  (ChatGPT, Claude…)",
    "wintree": "Windows tree /f",
    "indent" : "Indentation pure (espaces/tabs)",
}

# ── Ressources chargées depuis les JSON ───────────────────────────────────────

TIPS     = load_tips()
_PREFS   = load_prefs()     # prefs initiales au niveau module (snapshot)

# ── Helpers warnings ──────────────────────────────────────────────────────────

def _split_warnings(warnings: list[str]) -> tuple:
    root_path    = None
    fmt_detected = None
    others       = []
    for w in warnings:
        if w.startswith("ROOT_PATH_DETECTED:"):
            root_path = w[len("ROOT_PATH_DETECTED:"):]
        elif w.startswith("FORMAT_DETECTED:"):
            fmt_detected = w[len("FORMAT_DETECTED:"):]
        else:
            others.append(w)
    return root_path, fmt_detected, others

def _confirm_root_path(parent, path: str) -> bool:
    return messagebox.askyesno(
        "Chemin racine détecté",
        f"La première ligne ressemble à un chemin absolu :\n\n"
        f"  {path}\n\n"
        f"TreeForge va l'ignorer et générer uniquement le contenu\n"
        f"en dessous dans le dossier de destination.\n\n"
        f"C'est le comportement attendu ?",
        icon="question",
        parent=parent,
    )

# ── Onglet ────────────────────────────────────────────────────────────────────

class GeneratorTab(ctk.CTkFrame):
    def __init__(self, master, update_status, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._update_status = update_status
        self._tip_index     = 0
        self._tip_job       = None

        # ── Chargement prefs ──────────────────────────────────────────────────
        self._prefs       = load_prefs()

        self._build()
        self._setup_input_features()
        self.refresh_tab_settings()

    def _build(self):
        self.grid_rowconfigure(0, weight=1)  # input_area
        self.grid_rowconfigure(1, weight=0)  # tips
        self.grid_rowconfigure(2, weight=0)  # boutons
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        # ── Zone de saisie ────────────────────────────────────────────────────
        self.input_area = ctk.CTkTextbox(
            self, font=("Consolas", 13), wrap="word",
            fg_color=("white", "gray16"),
        )
        self.input_area.grid(row=0, column=0, padx=(12, 6), pady=(12, 4), sticky="nsew")

        self._placeholder = "Collez ici votre arborescence\n(texte indenté ou JSON)..."
        self._show_placeholder()
        self.input_area.bind("<FocusIn>",  self._clear_placeholder)
        self.input_area.bind("<FocusOut>", self._restore_placeholder)

        # ── Panneau droit ─────────────────────────────────────────────────────
        right = ctk.CTkScrollableFrame(
            self, width=210,
            fg_color=("gray93", "gray18"),
            corner_radius=8,
            scrollbar_button_color=("gray75", "gray35"),
            scrollbar_button_hover_color=("gray60", "gray50"),
        )
        right.grid(row=0, column=1, rowspan=2, padx=(0, 12), pady=12, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)

        # ── Section Format ────────────────────────────────────────────────────
        ctk.CTkLabel(
            right, text="Format d'arborescence", anchor="w",
            font=("Consolas", 12, "bold")
        ).pack(anchor="w", padx=12, pady=(12, 2))

        ctk.CTkLabel(
            right,
            text=(
                "Auto détecte le style.\n"
                "Choisissez manuellement\n"
                "si le résultat est incorrect."
            ),
            anchor="w", justify="left",
            font=("Consolas", 10),
            text_color=("gray50", "gray60"),
        ).pack(anchor="w", padx=12, pady=(0, 6))

        # PATCH — valeur initiale depuis prefs
        self.format_var = ctk.StringVar(
            value=self._prefs.get("format_mode", "Auto")
        )
        for label in MODES_FORMAT:
            ctk.CTkRadioButton(
                right, text=label, value=label,
                variable=self.format_var,
                font=("Consolas", 11),
            ).pack(anchor="w", padx=20, pady=3)

        self._fmt_feedback_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            right,
            textvariable=self._fmt_feedback_var,
            anchor="w", justify="left",
            font=("Consolas", 10),
            text_color=("#1a5c8c", "#4da6ff"),
            wraplength=170,
        ).pack(anchor="w", padx=12, pady=(4, 0))

        ctk.CTkFrame(right, height=1, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=12, pady=(12, 0))

        # ── Mode de parsing ───────────────────────────────────────────────────
        ctk.CTkLabel(
            right, text="Mode de parsing", anchor="w",
            font=("Consolas", 12, "bold")
        ).pack(anchor="w", padx=12, pady=(12, 4))

        # PATCH — valeur initiale depuis prefs
        self.parsing_mode_var = ctk.StringVar(
            value=self._prefs.get("parsing_mode", MODES_PARSING[0])
        )
        for mode in MODES_PARSING:
            ctk.CTkRadioButton(
                right, text=mode, value=mode,
                variable=self.parsing_mode_var,
                font=("Consolas", 11),
            ).pack(anchor="w", padx=20, pady=3)

        ctk.CTkFrame(right, height=1, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=12, pady=(12, 0))

        # ── Contenu des fichiers ──────────────────────────────────────────────
        ctk.CTkLabel(
            right, text="Contenu des fichiers", anchor="w",
            font=("Consolas", 12, "bold")
        ).pack(anchor="w", padx=12, pady=(12, 4))

        # PATCH — valeur initiale depuis prefs
        self.content_mode_var = ctk.StringVar(
            value=self._prefs.get("content_mode", MODES_CONTENU[0])
        )
        for mode in MODES_CONTENU:
            ctk.CTkRadioButton(
                right, text=mode, value=mode,
                variable=self.content_mode_var,
                font=("Consolas", 11),
            ).pack(anchor="w", padx=20, pady=3)

        ctk.CTkFrame(right, height=1, fg_color=("gray80", "gray30")).pack(
            fill="x", padx=12, pady=(12, 0))

        # ── Destination ───────────────────────────────────────────────────────
        ctk.CTkLabel(
            right, text="Destination", anchor="w",
            font=("Consolas", 12, "bold")
        ).pack(anchor="w", padx=12, pady=(12, 4))

        # PATCH — valeur initiale depuis prefs
        self.destination_var = ctk.StringVar(
            value=self._prefs.get("last_destination", "")
        )
        self.destination_entry = ctk.CTkEntry(
            right, textvariable=self.destination_var,
            placeholder_text="(non défini)", state="normal",
            font=("Consolas", 11),
        )
        self.destination_entry.pack(fill="x", padx=12, pady=(0, 6))
        self.destination_entry.bind("<Key>", lambda e: "break")

        ctk.CTkButton(
            right, text="Choisir un dossier...", height=32,
            fg_color=("#1f6aa5", "#1a5a8a"),
            hover_color=("#144870", "#114060"),
            font=("Consolas", 11),
            command=self._browse_destination,
        ).pack(fill="x", padx=12, pady=(0, 4))

        ctk.CTkButton(
            right, text="Effacer", height=28,
            fg_color="transparent", border_width=1,
            text_color=("gray25", "gray70"),
            hover_color=("gray85", "gray25"),
            font=("Consolas", 11),
            command=self._clear_destination,
        ).pack(fill="x", padx=12, pady=(0, 12))

        # ── Barre d'astuces ───────────────────────────────────────────────────
        self._tips_bar = ctk.CTkFrame(
            self, fg_color=("gray85", "gray22"), corner_radius=4, height=28
        )
        self._tips_bar.grid_propagate(False)
        self._tips_bar.grid_columnconfigure(0, weight=1)

        self._tip_var = ctk.StringVar(value=TIPS[0] if TIPS else "💡 TreeForge")
        ctk.CTkLabel(
            self._tips_bar,
            textvariable=self._tip_var,
            anchor="w",
            font=("Consolas", 10),
            text_color=("gray20", "gray80"),
        ).grid(row=0, column=0, padx=10, sticky="ew")

        # ── Barre de boutons ──────────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")
        btn_bar.grid_columnconfigure(0, weight=1)
        btn_bar.grid_columnconfigure(1, weight=1)

        self._btn_analyze = ctk.CTkButton(
            btn_bar, text="Analyser / Apercu", height=36,
            font=("Consolas", 12),
            command=self._analyze,
        )
        self._btn_analyze.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self._btn_generate = ctk.CTkButton(
            btn_bar, text="Generer structure", height=36,
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=("Consolas", 13, "bold"),
            command=self._generate,
        )
        self._btn_generate.grid(row=0, column=1, padx=(6, 0), sticky="ew")


    # ── Prefs ─────────────────────────────────────────────────────────────────

    def _save_prefs(self):
        """Sauvegarde l'état courant dans user_prefs.json."""
        prefs = load_prefs()
        prefs.update({
            "parsing_mode"     : self.parsing_mode_var.get(),
            "content_mode"     : self.content_mode_var.get(),
            "format_mode"      : self.format_var.get(),
            "last_destination" : self.destination_var.get(),
        })
        save_prefs(prefs)

    # ── Astuces rotatives ─────────────────────────────────────────────────────

    def _start_tips(self):
        if self._prefs.get("tips_enabled", True):
            if not self._tip_job:
                self._rotate_tip()

    def _apply_tips_visibility(self):
        enabled = self._prefs.get("tips_enabled", True)
        if enabled:
            self._tips_bar.grid(row=1, column=0, padx=(12, 6), pady=(0, 4), sticky="ew")
            if not self._tip_job:
                self._start_tips()
        else:
            self._tips_bar.grid_forget()
            if self._tip_job:
                self.after_cancel(self._tip_job)
                self._tip_job = None

    def refresh_tab_settings(self):
        self._prefs = load_prefs()
        self._apply_tips_visibility()
        self.destination_var.set(self._prefs.get("last_destination", ""))

    def _rotate_tip(self):
        if TIPS:
            self._tip_index = (self._tip_index + 1) % len(TIPS)
            self._tip_var.set(TIPS[self._tip_index])
        self._tip_job = self.after(8000, self._rotate_tip)

    def destroy(self):
        if self._tip_job:
            self.after_cancel(self._tip_job)
        super().destroy()

    # ── Input features ────────────────────────────────────────────────────────

    def _setup_input_features(self):
        attach_context_menu(self.input_area)

        self.input_area._textbox.config(undo=True, maxundo=-1)
        self.input_area._textbox.bind(
            "<Control-z>",
            lambda e: (self.input_area._textbox.edit_undo(), "break")[1]
        )
        self.input_area._textbox.bind(
            "<Control-y>",
            lambda e: (self.input_area._textbox.edit_redo(), "break")[1]
        )

        activated = setup_drop_target(self.input_area, on_drop=self._on_file_dropped)
        if activated:
            logger.info("Drag & Drop active sur la zone de saisie")
            self._placeholder = (
                "Collez ici votre arborescence\n"
                "(texte indente ou JSON)...\n\n"
                "Vous pouvez aussi glisser-deposer\n"
                "un fichier .txt ou .json ici"
            )
            self._show_placeholder()
        else:
            logger.info("Drag & Drop non disponible (tkinterdnd2 absent)")

    def _on_file_dropped(self, content: str):
        self._clear_placeholder()
        self.input_area.delete("1.0", "end")
        self.input_area.insert("1.0", content)
        self.input_area.configure(text_color=("gray10", "gray90"))
        self._update_status("Fichier depose — pret a analyser")
        logger.info("Fichier depose par drag & drop")

    def _show_placeholder(self):
        self.input_area.configure(state="normal")
        self.input_area.delete("1.0", "end")
        self.input_area.insert("1.0", self._placeholder)
        self.input_area.configure(text_color="gray50")

    def _clear_placeholder(self, _event=None):
        if self.input_area.get("1.0", "end-1c").strip() == self._placeholder.strip():
            self.input_area.delete("1.0", "end")
            self.input_area.configure(text_color=("gray10", "gray90"))

    def _restore_placeholder(self, _event=None):
        if not self.input_area.get("1.0", "end-1c").strip():
            self._show_placeholder()

    def _get_text(self) -> str:
        txt = self.input_area.get("1.0", "end-1c").strip()
        return "" if txt == self._placeholder.strip() else txt

    # ── Destination ───────────────────────────────────────────────────────────

    def _browse_destination(self):
        path = filedialog.askdirectory(title="Choisir le dossier de destination")
        if path:
            self.destination_var.set(path)
            self._update_status(f"Destination : {path}")
            logger.info(f"Destination selectionnee : {path}")
            self._save_prefs()  # PATCH

    def _clear_destination(self):
        self.destination_var.set("")
        self._update_status("Destination effacee")
        self._save_prefs()  # PATCH

    def _resolve_destination(self):
        dest = self.destination_var.get().strip()
        if not dest:
            dest = filedialog.askdirectory(title="Choisir le dossier de destination")
            if not dest:
                self._update_status("Annule — aucun dossier selectionne")
                return None
            self.destination_var.set(dest)
            self._save_prefs()  # PATCH
        return dest

    # ── Helpers format ────────────────────────────────────────────────────────

    def _get_fmt(self) -> str:
        return MODES_FORMAT.get(self.format_var.get(), "auto")

    def _handle_fmt_detected(self, fmt_detected: str | None):
        if fmt_detected and self._get_fmt() == "auto":
            label = FORMAT_DETECTED_LABELS.get(fmt_detected, fmt_detected)
            self._fmt_feedback_var.set(f"↳ Détecté : {label}")
            logger.info(f"Format détecté automatiquement : {label}")
            self._update_status(f"Format détecté : {label}")
        else:
            self._fmt_feedback_var.set("")

    # ── Analyser ──────────────────────────────────────────────────────────────

    def _analyze(self):
        text = self._get_text()
        if not text:
            messagebox.showwarning("TreeForge", "Aucun texte a analyser.")
            return

        mode   = self.parsing_mode_var.get()
        fmt    = self._get_fmt()
        result = parse(text, mode, fmt)

        if not result.ok:
            for err in result.errors:
                logger.error(err)
            self._update_status("Erreur(s) de parsing")
            messagebox.showerror("Erreur de parsing", "\n".join(result.errors))
            return

        root_path, fmt_detected, other_warnings = _split_warnings(result.warnings)
        self._handle_fmt_detected(fmt_detected)

        if root_path:
            if not _confirm_root_path(self, root_path):
                self._update_status("Parsing annule — modifiez l'arborescence si besoin")
                logger.info(f"Parsing annule — chemin racine conserve : {root_path}")
                return
            logger.info(f"Chemin racine ignore : {root_path}")

        for w in other_warnings:
            logger.warning(w)

        nb_f = sum(1 for n in _flatten(result.nodes) if not n.is_dir)
        nb_d = sum(1 for n in _flatten(result.nodes) if n.is_dir)
        logger.info(f"Parsing OK — {nb_d} dossiers, {nb_f} fichiers")
        self._update_status(f"{nb_d} dossier(s), {nb_f} fichier(s) — apercu ouvert")

        PreviewModal(self, result, on_confirm=self._generate_confirmed)

    # ── Générer ───────────────────────────────────────────────────────────────

    def _generate(self):
        text = self._get_text()
        if not text:
            messagebox.showwarning("TreeForge", "Aucun texte a analyser.")
            return

        dest = self._resolve_destination()
        if not dest:
            return

        mode    = self.parsing_mode_var.get()
        fmt     = self._get_fmt()
        content = self.content_mode_var.get()
        result  = parse(text, mode, fmt)

        if not result.ok:
            for err in result.errors:
                logger.error(err)
            messagebox.showerror("Erreur de parsing", "\n".join(result.errors))
            return

        root_path, fmt_detected, other_warnings = _split_warnings(result.warnings)
        self._handle_fmt_detected(fmt_detected)

        if root_path:
            if not _confirm_root_path(self, root_path):
                self._update_status("Generation annulee")
                logger.info(f"Generation annulee — chemin racine conserve : {root_path}")
                return
            logger.info(f"Chemin racine ignore : {root_path}")

        for w in other_warnings:
            logger.warning(w)

        self._launch_generation(result, dest, content)

    def _generate_confirmed(self, result):
        dest = self._resolve_destination()
        if not dest:
            return
        content = self.content_mode_var.get()
        self._launch_generation(result, dest, content)

    # ── Lancement génération ──────────────────────────────────────────────────

    def _launch_generation(self, result, dest: str, content: str):
        dest_path = Path(dest)
        if dest_path.exists():
            existing = [p for p in dest_path.iterdir() if not p.name.startswith(".")]
            if existing:
                confirmed = messagebox.askyesno(
                    "Dossier non vide — confirmer ?",
                    f"Le dossier de destination contient deja {len(existing)} element(s) :\n"
                    f"{dest}\n\n"
                    f"Les fichiers existants portant le meme nom seront ecrases.\n\n"
                    f"Continuer quand meme ?",
                    icon="warning",
                )
                if not confirmed:
                    self._update_status("Generation annulee — dossier non ecrase")
                    logger.info("Generation annulee par l'utilisateur (overwrite refuse)")
                    return

        self._update_status("Generation en cours...")
        logger.info(f"Generation -> {dest}  [contenu={content}]")

        self._btn_analyze.configure(state="disabled")
        self._btn_generate.configure(state="disabled")

        def _run():
            nb_dirs, nb_files, errors = generate(
                result, dest, content,
                on_progress=lambda msg: logger.info(msg)
            )
            self.after(0, self._on_done, nb_dirs, nb_files, errors, dest)

        threading.Thread(target=_run, daemon=True).start()


    def _on_done(self, nb_dirs: int, nb_files: int, errors: list, dest: str):
        if errors:
            for e in errors:
                logger.error(e)
            self._update_status(f"Termine avec {len(errors)} erreur(s)")
            messagebox.showwarning(
                "Termine avec erreurs",
                f"{nb_dirs} dossiers, {nb_files} fichiers crees.\n\n"
                f"{len(errors)} erreur(s) :\n" + "\n".join(errors[:5])
            )
        else:
            logger.info(f"{nb_dirs} dossiers, {nb_files} fichiers -> {dest}")
            self._update_status(
                f"{nb_dirs} dossiers + {nb_files} fichiers crees dans {dest}"
            )
            messagebox.showinfo(
                "Generation reussie",
                f"{nb_dirs} dossier(s) et {nb_files} fichier(s) crees.\n\n{dest}"
            )
        self._btn_analyze.configure(state="normal")
        self._btn_generate.configure(state="normal")
        self._save_prefs()  # PATCH


# ── Flatten ───────────────────────────────────────────────────────────────────

def _flatten(nodes):
    for n in nodes:
        yield n
        yield from _flatten(n.children)
