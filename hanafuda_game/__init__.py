"""
Hanafuda Koi-Koi — Anki Add-on
"""

from aqt import mw, gui_hooks
from aqt.qt import QAction


_window = None


def open_hanafuda():
    global _window
    try:
        if _window is None or not _window.isVisible():
            from .game_window import HanafudaWindow
            _window = HanafudaWindow(mw)
        _window.show()
        _window.raise_()
        _window.activateWindow()
    except Exception as e:
        from aqt.utils import showWarning
        showWarning(f"Hanafuda failed to open:\n\n{e}")


def setup_menu():
    action = QAction("🌸 Hanafuda Koi-Koi", mw)
    action.triggered.connect(open_hanafuda)
    mw.form.menuTools.addAction(action)


gui_hooks.main_window_did_init.append(setup_menu)
