"""
gui/components/consent_dialog.py
==================================
Dialogue de consentement télémétrie — affiché au premier lancement.

Comportement :
  - S'affiche UNE SEULE FOIS (vérifié via telemetry.has_answered_consent())
  - "Accepter"  → telemetry.set_consent(True)  + telemetry.init()
  - "Non merci" → telemetry.set_consent(False)
  - Peut être rouvert via ⚙️ Paramètres
"""
from __future__ import annotations

import customtkinter as ctk


class ConsentDialog(ctk.CTkToplevel):
    """
    Popup modale de consentement télémétrie.
    
    Usage :
        dlg = ConsentDialog(parent)
        parent.wait_window(dlg)
        # dlg.result → True (accepté) / False (refusé) / None (fermé)
    """

    def __init__(self, parent: ctk.CTk):
        super().__init__(parent)

        self.title("TreeForge — Amélioration du logiciel")
        self.resizable(False, False)
        self.result: bool | None = None

        # Centrer sur le parent
        self.update_idletasks()
        px = parent.winfo_x() + parent.winfo_width()  // 2
        py = parent.winfo_y() + parent.winfo_height() // 2
        w, h = 480, 520
        self.geometry(f"{w}x{h}+{px - w//2}+{py - h//2}")

        self._build()

        # Rendre modale
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────────────────────────────────
    # Construction de l'interface
    # ─────────────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # ── Titre ─────────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Aidez-nous à améliorer TreeForge",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=25, pady=(25, 10))

        # ── Corps ─────────────────────────────────────────────────────────────
        body = (
            "TreeForge peut envoyer des données anonymes pour nous aider\n"
            "à comprendre comment l'outil est utilisé et corriger les bugs.\n"
        )
        ctk.CTkLabel(
            self,
            text=body,
            justify="left",
            anchor="w",
            wraplength=430,
        ).pack(fill="x", padx=25, pady=(0, 8))

        # ── Section collecté ──────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Ce qui est collecté :",
            font=ctk.CTkFont(weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=25, pady=(8, 2))

        collecte = (
            "  • Événements d'utilisation (onglets, générations, templates)\n"
            "  • Rapports de crash automatiques (stack trace uniquement)\n"
            "  • Version du logiciel et OS"
        )
        ctk.CTkLabel(
            self,
            text=collecte,
            justify="left",
            anchor="w",
            wraplength=430,
        ).pack(fill="x", padx=25, pady=(0, 8))

        # ── Section NON collecté ──────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Ce qui n'est PAS collecté :",
            font=ctk.CTkFont(weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=25, pady=(8, 2))

        non_collecte = (
            "  • Nom, email ou toute donnée personnelle\n"
            "  • Contenu de vos arborescences ou fichiers\n"
            "  • Chemins de fichiers locaux"
        )
        ctk.CTkLabel(
            self,
            text=non_collecte,
            justify="left",
            anchor="w",
            wraplength=430,
        ).pack(fill="x", padx=25, pady=(0, 15))

        # ── Note de bas ───────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Vous pouvez changer ce choix à tout moment via ⚙️ ou ≡ en bas de la fenêtre.",
            justify="left",
            anchor="w",
            wraplength=430,
            text_color="gray60",
            font=ctk.CTkFont(size=11),
        ).pack(fill="x", padx=25, pady=(0, 20))

        # ── Séparateur ────────────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color="gray30").pack(
            fill="x", padx=25, pady=(0, 20)
        )

        # ── Boutons ───────────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=25, pady=(0, 25))

        ctk.CTkButton(
            btn_row,
            text="Non merci",
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray50"),
            text_color=("gray20", "gray80"),
            hover_color=("gray90", "gray25"),
            height=40,
            command=self._decline,
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="Accepter",
            fg_color="#4CAF50",
            hover_color="#388E3C",
            text_color="white",
            height=40,
            command=self._accept,
        ).pack(side="left", expand=True, fill="x")

    # ─────────────────────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────────────────────

    def _accept(self) -> None:
        self.result = True
        self.grab_release()
        self.destroy()

    def _decline(self) -> None:
        self.result = False
        self.grab_release()
        self.destroy()

    def _on_close(self) -> None:
        """Fermeture via X → considéré comme refus."""
        self.result = False
        self.grab_release()
        self.destroy()
