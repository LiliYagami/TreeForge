"""
Onglet Prompt IA — sélection, édition, copie et raccourcis web pour les prompts.
"""
from __future__ import annotations
import webbrowser
import customtkinter as ctk

from treeforge.utils.logger import logger
from treeforge.utils.helpers import load_prompts, load_prefs, save_prefs

_PROMPTS = load_prompts()
_PROMPT_FALLBACK = (
    "Génère une arborescence de projet pour [DÉCRIRE VOTRE PROJET].\n\n"
    "Format attendu : arborescence texte indenté ou unicode (├──).\n"
    "Réponds UNIQUEMENT avec l'arborescence, sans explications."
)

def _get_prompt(key: str = "general") -> str:
    """Retourne le texte du prompt pour la clé donnée, ou le fallback."""
    return _PROMPTS.get(key, {}).get("text", _PROMPT_FALLBACK)


class PromptTab(ctk.CTkFrame):
    def __init__(self, master, update_status, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._update_status = update_status
        self._prefs = load_prefs()
        self._prompt_key = self._prefs.get("last_prompt_key", "general")

        # Mappages pour le sélecteur de prompt IA
        self._prompt_labels = [info.get("label", key) for key, info in _PROMPTS.items()]
        self._label_to_prompt_key = {info.get("label", key): key for key, info in _PROMPTS.items()}
        self._prompt_key_to_label = {key: info.get("label", key) for key, info in _PROMPTS.items()}

        self._build()

    def _build(self):
        # Configurer grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Sélecteur
        self.grid_rowconfigure(1, weight=1) # Textbox (prend toute la place)
        self.grid_rowconfigure(2, weight=0) # Boutons d'action (Copier / Réinitialiser)
        self.grid_rowconfigure(3, weight=0) # Raccourcis web

        # ── Sélecteur de type de prompt ────────────────────────────────────────
        selector_frame = ctk.CTkFrame(self, fg_color="transparent")
        selector_frame.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
        selector_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            selector_frame, text="Type de projet :",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")

        initial_label = self._prompt_key_to_label.get(self._prompt_key, "Général")
        self._prompt_menu_var = ctk.StringVar(value=initial_label)
        self._prompt_menu = ctk.CTkOptionMenu(
            selector_frame,
            variable=self._prompt_menu_var,
            values=self._prompt_labels or ["Général"],
            command=self._on_prompt_type_changed,
            font=("Consolas", 12),
            width=220,
        )
        self._prompt_menu.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            selector_frame,
            text="Personnalisez le prompt ci-dessous puis copiez-le dans votre LLM.",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray55"),
        ).grid(row=0, column=2, padx=12, sticky="e")

        # ── Zone de texte du prompt ───────────────────────────────────────────
        self.prompt_box = ctk.CTkTextbox(
            self,
            font=("Consolas", 13),
            wrap="word",
            fg_color=("white", "gray16"),
            border_width=1,
            border_color=("gray80", "gray25"),
        )
        self.prompt_box.grid(row=1, column=0, padx=12, pady=6, sticky="nsew")
        self.prompt_box.insert("1.0", _get_prompt(self._prompt_key))

        # ── Boutons d'action (Copier / Réinitialiser) ─────────────────────────
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.grid(row=2, column=0, padx=12, pady=6, sticky="ew")
        
        self.btn_copy = ctk.CTkButton(
            actions_frame,
            text="📋 Copier le prompt",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._copy_prompt,
        )
        self.btn_copy.pack(side="left", padx=(0, 10))

        self.btn_reset = ctk.CTkButton(
            actions_frame,
            text="↩️ Réinitialiser",
            height=36,
            fg_color="transparent",
            border_width=1,
            text_color=("gray25", "gray70"),
            hover_color=("gray85", "gray25"),
            font=ctk.CTkFont(size=12),
            command=self._reset_prompt,
        )
        self.btn_reset.pack(side="left")

        # ── Raccourcis web (ouvrir LLMs) ──────────────────────────────────────
        shortcuts_frame = ctk.CTkFrame(
            self,
            fg_color=("gray90", "gray20"),
            corner_radius=6,
        )
        shortcuts_frame.grid(row=3, column=0, padx=12, pady=(6, 12), sticky="ew")
        
        ctk.CTkLabel(
            shortcuts_frame,
            text="Ouvrir un modèle IA dans le navigateur :",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="left", padx=12, pady=8)

        llms = [
            ("ChatGPT", "https://chatgpt.com", "#10a37f", "#0e8c6d"),
            ("Claude", "https://claude.ai", "#d97757", "#c26548"),
            ("Gemini", "https://gemini.google.com", "#1a73e8", "#155cb0"),
        ]

        for name, url, color, hover_color in llms:
            btn = ctk.CTkButton(
                shortcuts_frame,
                text=f"🌐 {name}",
                height=28,
                width=100,
                fg_color=color,
                hover_color=hover_color,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda u=url: webbrowser.open(u),
            )
            btn.pack(side="left", padx=6, pady=8)

    def _copy_prompt(self):
        text = self.prompt_box.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        self._update_status("Prompt copié dans le presse-papiers")
        logger.info("Prompt IA copié")

    def _reset_prompt(self):
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", _get_prompt(self._prompt_key))
        self._update_status("Prompt réinitialisé à sa valeur par défaut")
        logger.info(f"Prompt IA réinitialisé ({self._prompt_key})")

    def _on_prompt_type_changed(self, label: str):
        key = self._label_to_prompt_key.get(label, "general")
        self._prompt_key = key
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", _get_prompt(key))
        logger.info(f"Modèle de prompt IA changé pour : {label} ({key})")
        self._save_prefs()

    def _save_prefs(self):
        """Sauvegarde la clé du dernier prompt dans user_prefs.json."""
        prefs = load_prefs()
        prefs["last_prompt_key"] = self._prompt_key
        save_prefs(prefs)

    def refresh_tab_settings(self):
        self._prefs = load_prefs()
        new_prompt_key = self._prefs.get("last_prompt_key", "general")
        if new_prompt_key != self._prompt_key:
            self._prompt_key = new_prompt_key
            label = self._prompt_key_to_label.get(new_prompt_key, "Général")
            self._prompt_menu_var.set(label)
            self.prompt_box.delete("1.0", "end")
            self.prompt_box.insert("1.0", _get_prompt(new_prompt_key))
