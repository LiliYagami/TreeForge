"""
main_window.py — Fenêtre principale TreeForge
"""
from __future__ import annotations
import platform
import customtkinter as ctk

from treeforge.gui.tabs.prompt_tab         import PromptTab
from treeforge.gui.tabs.generator_tab      import GeneratorTab
from treeforge.gui.tabs.recaper_tab        import RecaperTab
from treeforge.gui.tabs.revers_recaper_tab import ReversRecaperTab
from treeforge.gui.tabs.templates_tab      import TemplatesTab
from treeforge.utils.logger                import logger, attach_gui_handler
from treeforge.gui.components.log_panel    import LogPanel

# ── Tentative d'initialisation D&D au niveau fenêtre ─────────────────────────
try:
    from tkinterdnd2 import TkinterDnD
    class _Base(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self):
            super().__init__()
            self.TkdndVersion = TkinterDnD._require(self)
    DND_WINDOW = True
except Exception as e:
    class _Base(ctk.CTk):
        def __init__(self):
            super().__init__()
    DND_WINDOW = False
    logger.warning("D&D fenêtre non disponible : %s", e)

# ─────────────────────────────────────────────────────────────────────────────
APP_TITLE   = "TreeForge"
APP_VERSION = "3.0.0"
TAGLINE     = "Think smart, work fast"
WIN_SIZE    = "900x720"
MIN_SIZE    = (750, 560)
# ─────────────────────────────────────────────────────────────────────────────


class MainWindow(_Base):

    def __init__(self):
        super().__init__()
        self._log_visible = False
        self._build_window()
        self._build_header()
        self._build_tabs()
        self._build_log_panel()
        self._build_statusbar()
        attach_gui_handler(self._log_panel.textbox)

        if DND_WINDOW:
            logger.info("TreeForge %s démarré  —  D&D actif", APP_VERSION)
        else:
            logger.info("TreeForge %s démarré  —  D&D inactif", APP_VERSION)

    # ─────────────────────────────────────────────────────────────────────────
    # Fenêtre
    # ─────────────────────────────────────────────────────────────────────────

    def _build_window(self):
        self.title(f"{APP_TITLE}  v{APP_VERSION}")
        self.geometry(WIN_SIZE)
        self.minsize(*MIN_SIZE)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)   # header
        self.grid_rowconfigure(1, weight=1)   # onglets
        self.grid_rowconfigure(2, weight=0)   # log panel (caché par défaut)
        self.grid_rowconfigure(3, weight=0)   # status bar

    # ─────────────────────────────────────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self, corner_radius=0, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        # ── Gauche : icône + titre + tagline ─────────────────────────────────
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=18, pady=8)

        ctk.CTkLabel(
            left,
            text="🌲  TreeForge",
            font=ctk.CTkFont(weight="bold", size=20),
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            left,
            text=f"  —  {TAGLINE}",
            font=ctk.CTkFont(size=12),
            text_color=("gray25", "gray70"),
            anchor="w",
        ).pack(side="left", padx=(4, 0))

        # ── Droite : boutons ≡ et ⚙️ ─────────────────────────────────────────
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e", padx=14)

        ctk.CTkButton(
            btn_frame,
            text="≡",
            width=36, height=36,
            fg_color="transparent",
            text_color=("gray15", "gray90"),
            hover_color=("gray85", "gray25"),
            font=ctk.CTkFont(size=18),
            command=self._toggle_log,
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_frame,
            text="⚙️",
            width=36, height=36,
            fg_color="transparent",
            text_color=("gray15", "gray90"),
            hover_color=("gray85", "gray25"),
            command=self._open_settings,
        ).pack(side="left")

    # ─────────────────────────────────────────────────────────────────────────
    # Onglets
    # ─────────────────────────────────────────────────────────────────────────

    def _build_tabs(self):
        self._tabview = ctk.CTkTabview(self)
        self._tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(6, 0))

        for name in ("Prompt IA", "Générer", "Recaper", "Restaurer", "Templates"):
            self._tabview.add(name)

        self.prompt_tab = PromptTab(
            self._tabview.tab("Prompt IA"),
            update_status=self._set_status,
        )
        self.prompt_tab.pack(fill="both", expand=True)

        self.generator_tab = GeneratorTab(
            self._tabview.tab("Générer"),
            update_status=self._set_status,
        )
        self.generator_tab.pack(fill="both", expand=True)


        RecaperTab(
            self._tabview.tab("Recaper"),
            update_status=self._set_status,
        ).pack(fill="both", expand=True)

        ReversRecaperTab(
            self._tabview.tab("Restaurer"),
            update_status=self._set_status,
        ).pack(fill="both", expand=True)

        TemplatesTab(
            self._tabview.tab("Templates"),
            update_status=self._set_status,
        ).pack(fill="both", expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Log panel
    # ─────────────────────────────────────────────────────────────────────────

    def _build_log_panel(self):
        self._log_panel = LogPanel(self)
        # caché par défaut — ≡ le toggle

    def _toggle_log(self):
        if self._log_visible:
            self._log_panel.grid_forget()
            self.grid_rowconfigure(2, weight=0)
            self._log_visible = False
        else:
            self._log_panel.grid(
                row=2, column=0,
                sticky="nsew",
                padx=10, pady=(4, 0),
            )
            self.grid_rowconfigure(2, weight=1)
            self._log_visible = True

    # ─────────────────────────────────────────────────────────────────────────
    # Status bar
    # ─────────────────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, corner_radius=0, height=26)
        bar.grid(row=3, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_propagate(False)

        self._status_label = ctk.CTkLabel(
            bar, text="Prêt", anchor="w",
            font=ctk.CTkFont(size=11),
        )
        self._status_label.grid(row=0, column=0, sticky="w", padx=12)

        ctk.CTkLabel(
            bar,
            text=f"V{APP_VERSION}  •  {TAGLINE}",
            anchor="e",
            font=ctk.CTkFont(size=11),
            text_color=("gray25", "gray75"),
        ).grid(row=0, column=1, sticky="e", padx=12)

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _set_status(self, msg: str):
        self.after(0, self._status_label.configure, {"text": msg})

    def _open_settings(self):
        from treeforge.gui.components.settings_dialog import SettingsDialog
        SettingsDialog(self)

    def refresh_settings(self) -> None:
        if hasattr(self, "generator_tab"):
            self.generator_tab.refresh_tab_settings()
        if hasattr(self, "prompt_tab"):
            self.prompt_tab.refresh_tab_settings()

