from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from treeforge.utils.helpers import load_boilerplates, save_boilerplates
import treeforge.config as config


class BoilerplateEditorDialog(ctk.CTkToplevel):
    """
    Boîte de dialogue permettant à l'utilisateur de modifier, ajouter ou
    supprimer des modèles de démarrage (boilerplates) par extension de fichier.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.withdraw()  # Masquer temporairement
        self.title("TreeForge — Éditeur de Boilerplates")
        self.geometry("600x500")
        self.minsize(500, 400)
        self.resizable(True, True)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # Charger les boilerplates en mémoire
        self._boilerplates = load_boilerplates()
        self._extensions = sorted(self._boilerplates.keys())
        self._current_ext = self._extensions[0] if self._extensions else ""

        self._build()
        self._load_current_boilerplate()
        
        self.after(100, self._show_and_center)

    def _show_and_center(self):
        self._center()
        self.deiconify()
        self.grab_set()
        self.lift()
        self.focus_force()

    def _center(self):
        self.update_idletasks()
        m = self.master
        x = m.winfo_x() + (m.winfo_width()  - self.winfo_width())  // 2
        y = m.winfo_y() + (m.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── 1. En-tête (Sélection de l'extension) ────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=12)
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="Extension :",
            font=ctk.CTkFont(weight="bold", size=13),
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")

        # OptionMenu pour choisir l'extension
        self._ext_var = ctk.StringVar(value=self._current_ext or "(aucune)")
        self._ext_menu = ctk.CTkOptionMenu(
            header,
            variable=self._ext_var,
            values=self._extensions or ["(aucune)"],
            command=self._on_extension_changed,
            width=140,
        )
        self._ext_menu.grid(row=0, column=1, sticky="w")

        # Boutons d'action rapides sur les extensions
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=2, sticky="e")

        ctk.CTkButton(
            btn_frame, text="+ Ajouter", width=80, height=28,
            command=self._add_extension,
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(0, 4))

        self._btn_delete = ctk.CTkButton(
            btn_frame, text="🗑 Supprimer", width=90, height=28,
            fg_color="#c62828", hover_color="#b71c1c",
            command=self._delete_extension,
            font=ctk.CTkFont(size=11),
        )
        self._btn_delete.pack(side="left")

        # ── 2. Zone d'édition de texte ───────────────────────────────────────────
        editor_frame = ctk.CTkFrame(self)
        editor_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            editor_frame,
            text="Modèle de code initial (Boilerplate) :",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 2))

        self._textbox = ctk.CTkTextbox(
            editor_frame,
            font=("Consolas", 12),
            wrap="none",
        )
        self._textbox.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        # ── 3. Bas de page ───────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent", height=48)
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_propagate(False)

        ctk.CTkButton(
            footer, text="Fermer / Annuler", width=120, height=36,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray70"),
            hover_color=("gray85", "gray25"),
            command=self.destroy,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer, text="✔ Enregistrer", width=120, height=36,
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=ctk.CTkFont(weight="bold"),
            command=self._save_changes,
        ).grid(row=0, column=1, sticky="e")

    def _load_current_boilerplate(self):
        self._textbox.delete("1.0", "end")
        if self._current_ext:
            content = self._boilerplates.get(self._current_ext, "")
            self._textbox.insert("1.0", content)
            self._btn_delete.configure(state="normal")
        else:
            self._btn_delete.configure(state="disabled")

    def _on_extension_changed(self, ext: str):
        # Sauvegarder d'abord la valeur courante dans l'objet interne
        if self._current_ext:
            self._boilerplates[self._current_ext] = self._textbox.get("1.0", "end-1c")
        
        self._current_ext = ext
        self._load_current_boilerplate()

    def _save_changes(self):
        # Mettre à jour le boilerplate courant depuis la zone de texte
        if self._current_ext:
            self._boilerplates[self._current_ext] = self._textbox.get("1.0", "end-1c")

        # Enregistrer sur disque
        success = save_boilerplates(self._boilerplates)
        if success:
            # Mettre à jour en mémoire dans config.py
            config.BOILERPLATE.clear()
            config.BOILERPLATE.update(self._boilerplates)
            messagebox.showinfo("Succès", "Les boilerplates ont été enregistrés et appliqués en direct.", parent=self)
            self.destroy()
        else:
            messagebox.showerror("Erreur", "Impossible d'écrire le fichier de configuration.", parent=self)

    def _add_extension(self):
        # Demander le nom de l'extension
        dialog = ctk.CTkInputDialog(
            title="Ajouter une extension",
            text="Saisissez l'extension (ex: .rs, .go) :"
        )
        dialog.transient(self)
        dialog.grab_set()
        
        ext = dialog.get_input()
        if ext:
            ext = ext.strip().lower()
            if not ext.startswith("."):
                ext = "." + ext
            
            if ext in self._boilerplates:
                messagebox.showwarning("Extension existante", f"L'extension {ext} existe déjà.", parent=self)
                return

            self._boilerplates[ext] = ""
            self._extensions = sorted(self._boilerplates.keys())
            self._ext_menu.configure(values=self._extensions)
            self._ext_var.set(ext)
            
            # Activer la nouvelle
            self._on_extension_changed(ext)

    def _delete_extension(self):
        if not self._current_ext:
            return
        
        confirmed = messagebox.askyesno(
            "Confirmer la suppression",
            f"Voulez-vous vraiment supprimer le boilerplate pour l'extension {self._current_ext} ?",
            parent=self
        )
        if confirmed:
            del self._boilerplates[self._current_ext]
            self._extensions = sorted(self._boilerplates.keys())
            self._current_ext = self._extensions[0] if self._extensions else ""
            
            self._ext_menu.configure(values=self._extensions or ["(aucune)"])
            self._ext_var.set(self._current_ext or "(aucune)")
            self._load_current_boilerplate()
