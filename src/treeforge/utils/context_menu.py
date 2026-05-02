"""
context_menu.py — Menu contextuel clic droit pour CTkTextbox.

Fournit : Coller / Copier / Couper / Tout sélectionner / Effacer
100% natif tkinter — aucune dépendance externe.

Usage :
    from treeforge.utils.context_menu import attach_context_menu
    attach_context_menu(self.input_area)
"""
from __future__ import annotations
import tkinter as tk


def attach_context_menu(textbox) -> None:
    """
    Attache un menu clic droit à un CTkTextbox (ou tout widget Text tkinter).

    Le menu s'adapte au contexte :
    - Coller est grisé si le presse-papiers est vide
    - Copier / Couper sont grisés si aucune sélection
    """
    # Récupère le widget Text interne de CTkTextbox
    # CTkTextbox encapsule un tk.Text dans ._textbox
    try:
        _widget = textbox._textbox
    except AttributeError:
        _widget = textbox  # fallback si c'est déjà un tk.Text

    menu = tk.Menu(_widget, tearoff=0)

    def _update_states():
        """Active/grise les entrées selon l'état courant."""
        try:
            has_clipboard = bool(_widget.clipboard_get())
        except tk.TclError:
            has_clipboard = False

        try:
            has_selection = bool(_widget.tag_ranges("sel"))
        except Exception:
            has_selection = False

        menu.entryconfigure("Coller",          state="normal" if has_clipboard else "disabled")
        menu.entryconfigure("Copier",          state="normal" if has_selection else "disabled")
        menu.entryconfigure("Couper",          state="normal" if has_selection else "disabled")

    def _paste():
        try:
            content = _widget.clipboard_get()
            try:
                _widget.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            _widget.insert("insert", content)
        except tk.TclError:
            pass

    def _copy():
        try:
            content = _widget.get("sel.first", "sel.last")
            _widget.clipboard_clear()
            _widget.clipboard_append(content)
        except tk.TclError:
            pass

    def _cut():
        _copy()
        try:
            _widget.delete("sel.first", "sel.last")
        except tk.TclError:
            pass

    def _select_all():
        _widget.tag_add("sel", "1.0", "end")
        _widget.mark_set("insert", "end")

    def _clear():
        _widget.delete("1.0", "end")

    # Construction du menu
    menu.add_command(label="Coller",             command=_paste)
    menu.add_command(label="Copier",             command=_copy)
    menu.add_command(label="Couper",             command=_cut)
    menu.add_separator()
    menu.add_command(label="Tout sélectionner",  command=_select_all)
    menu.add_separator()
    menu.add_command(label="Effacer la zone",    command=_clear)

    def _show(event):
        _update_states()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # Bind clic droit Windows + Linux + Mac
    _widget.bind("<Button-3>",  _show)   # Windows / Linux
    _widget.bind("<Button-2>",  _show)   # Mac (clic droit = Button-2 sur certains)