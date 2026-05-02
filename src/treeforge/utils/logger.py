"""Logger centralisé avec handler GUI optionnel."""
from __future__ import annotations
import logging
import threading


logger = logging.getLogger("treeforge")
logger.setLevel(logging.DEBUG)

# Console handler (toujours actif)
_ch = logging.StreamHandler()
_ch.setFormatter(logging.Formatter("%(levelname)s — %(message)s"))
logger.addHandler(_ch)

_gui_handler: logging.Handler | None = None


class _TextboxHandler(logging.Handler):
    """Handler qui écrit dans un CTkTextbox (thread-safe)."""

    def __init__(self, textbox) -> None:
        super().__init__()
        self._box = textbox
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record) + "\n"
        try:
            self._box.after(0, self._write, msg)
        except Exception:
            pass

    def _write(self, msg: str) -> None:
        with self._lock:
            try:
                self._box.configure(state="normal")
                self._box.insert("end", msg)
                self._box.see("end")
                self._box.configure(state="disabled")
            except Exception:
                pass


def attach_gui_handler(textbox) -> None:
    """Connecte le logger à un CTkTextbox."""
    global _gui_handler
    if _gui_handler:
        logger.removeHandler(_gui_handler)
    _gui_handler = _TextboxHandler(textbox)
    _gui_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%H:%M:%S"))
    logger.addHandler(_gui_handler)