"""
modal_base.py — Base commune pour les fenêtres Toplevel modales de TreeForge.

Centralise :
  - l'affichage différé + centrage sur la fenêtre parente
  - le contournement d'un bug de compositing Windows (DWM) où une
    CTkToplevel modale garde le focus/grab (donc bloque bien les
    événements — l'appli semble figée) mais cesse d'être repeinte à
    l'écran après quelques secondes, jusqu'à ce qu'une action système
    (Win+flèche, Alt-Tab) force Windows à la recomposer. Découvert sur
    DiffPreviewModal (chantier #1) ; partagé ici pour que toute fenêtre
    modale en bénéficie, plutôt que de dupliquer le correctif.
"""
from __future__ import annotations

import customtkinter as ctk


class ModalToplevel(ctk.CTkToplevel):
    """
    À sous-classer. Dans __init__ : construire l'UI puis appeler
    self._start_show_sequence() en dernier (remplace tout appel manuel à
    withdraw()/transient()/deiconify()/grab_set()).
    """

    def _start_show_sequence(self) -> None:
        self.withdraw()
        self.transient(self.master)
        self._watchdog_job = None
        self.after(100, self._show_and_center)

    def _show_and_center(self) -> None:
        self._center()
        self.deiconify()
        # wait_visibility() plutôt qu'un délai deviné : évite un grab_set()
        # posé sur une fenêtre pas encore réellement mappée côté Windows.
        self.wait_visibility()
        self.grab_set()
        self.lift()
        self.focus_force()
        self._force_repaint()
        self._schedule_visibility_watchdog()

    def _force_repaint(self) -> None:
        """Léger cycle d'opacité pour forcer Windows (DWM) à recomposer la fenêtre."""
        try:
            self.attributes("-alpha", 0.999)
            self.after(30, lambda: self.winfo_exists() and self.attributes("-alpha", 1.0))
        except Exception:
            pass

    def _schedule_visibility_watchdog(self) -> None:
        """
        Revérifie et force périodiquement le repaint tant que la modale garde
        le grab. winfo_viewable() seul ne suffit pas (Tk peut croire la
        fenêtre visible alors que Windows ne la repeint plus) — on force
        donc le nudge d'opacité à chaque tick, pas seulement en secours.
        """
        if not self.winfo_exists():
            return
        if not self.winfo_viewable():
            try:
                self.deiconify()
                self.lift()
                self.attributes("-topmost", True)
                self.after(50, lambda: self.winfo_exists() and self.attributes("-topmost", False))
                self.focus_force()
            except Exception:
                pass
        self._force_repaint()
        self._watchdog_job = self.after(1000, self._schedule_visibility_watchdog)

    def _cancel_watchdog(self) -> None:
        if getattr(self, "_watchdog_job", None) is not None:
            try:
                self.after_cancel(self._watchdog_job)
            except Exception:
                pass
            self._watchdog_job = None

    def _center(self) -> None:
        self.update_idletasks()
        pw = self.master.winfo_width()
        ph = self.master.winfo_height()
        px = self.master.winfo_rootx()
        py = self.master.winfo_rooty()
        w  = self.winfo_width()
        h  = self.winfo_height()
        x  = px + (pw - w) // 2
        y  = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")

    def _close(self) -> None:
        """À appeler avant destroy() dans les callbacks confirm/cancel des sous-classes."""
        self._cancel_watchdog()
        self.grab_release()
