"""
game_window.py — PyQt6/5 QDialog hosting the Hanafuda game via QWebEngineView.
"""

import json
import os

from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
    QWidget, pyqtSlot
)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineScript
    from PyQt6.QtWebChannel import QWebChannel
    from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QFile, QIODevice
    PYQT6 = True
except ImportError:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineScript
    from PyQt5.QtWebChannel import QWebChannel
    from PyQt5.QtCore import QObject, pyqtSignal, QUrl, QFile, QIODevice
    PYQT6 = False

from .vocab_bridge import (
    get_decks, get_challenge, get_field_names, build_session,
    auto_detect_fields, record_answer, VocabSession
)

ADDON_DIR = os.path.dirname(__file__)
WEB_DIR = os.path.join(ADDON_DIR, "web")


class AnkiBridge(QObject):
    challengeReady = pyqtSignal(str)
    decksReady     = pyqtSignal(str)
    answerRecorded = pyqtSignal(bool)
    fieldsReady    = pyqtSignal(str)

    def __init__(self, col, parent=None):
        super().__init__(parent)
        self._col = col
        self._deck_id = None
        self._q_field = -1
        self._a_field = -1
        self._session = None  # Optional[VocabSession]

    def _reset_session(self):
        """Build a fresh session for the current deck."""
        self._session = build_session(self._col, self._deck_id)

    @pyqtSlot()
    def requestDecks(self):
        try:
            decks = get_decks(self._col)
            self.decksReady.emit(json.dumps(decks))
        except Exception as e:
            print(f"[Hanafuda] requestDecks error: {e}")
            self.decksReady.emit(json.dumps([]))

    @pyqtSlot(int)
    def setDeck(self, deck_id: int):
        self._deck_id = deck_id if deck_id != -1 else None
        self._q_field = -1
        self._a_field = -1
        self._reset_session()
        self._emit_fields()

    @pyqtSlot()
    def newGameStarted(self):
        """Called from JS when a new game begins — resets session."""
        self._reset_session()
        print("[Hanafuda] Session reset for new game")

    def _emit_fields(self):
        try:
            names = get_field_names(self._col, self._deck_id)
            self.fieldsReady.emit(json.dumps({'fields': names}))
            if names:
                q, a = auto_detect_fields(names)
                self._q_field = q
                self._a_field = a
                print(f"[Hanafuda] Auto-detected Q=[{q}] A=[{a}] from {names}")
        except Exception as e:
            print(f"[Hanafuda] _emit_fields error: {e}")
            self.fieldsReady.emit(json.dumps({'fields': []}))

    @pyqtSlot(int, int)
    def setFieldConfig(self, q_field: int, a_field: int):
        self._q_field = q_field
        self._a_field = a_field
        print(f"[Hanafuda] Field config: Q=[{q_field}] A=[{a_field}]")

    @pyqtSlot()
    def requestChallenge(self):
        try:
            challenge = get_challenge(
                self._col,
                session=self._session,
                q_field=self._q_field,
                a_field=self._a_field,
                deck_id=self._deck_id,
            )
            if challenge is None:
                self.challengeReady.emit(json.dumps({'error': 'not_enough_cards'}))
            else:
                self.challengeReady.emit(json.dumps(challenge))
        except Exception as e:
            print(f"[Hanafuda] requestChallenge error: {e}")
            self.challengeReady.emit(json.dumps({'error': str(e)}))

    @pyqtSlot(int)
    def setSessionFocus(self, focus):
        if self._session:
            self._session.focus = focus
            print("[Hanafuda] Session focus set to %d" % focus)

    @pyqtSlot(int)
    def setPoolSize(self, size):
        if self._session:
            self._session.pool_size = max(5, min(size, len(self._session.all_ids)))
            print("[Hanafuda] Pool size set to %d" % self._session.pool_size)

    @pyqtSlot(int, int)
    def recordAnswer(self, card_id: int, ease: int):
        try:
            # Update session tracker
            if self._session:
                if ease == 1 or ease == 2:
                    # Wrong answer or Hard button — reinforce, show again soon
                    self._session.record_wrong(card_id)
                elif ease == 4:
                    # Easy button — knew it cold, skip for rest of session
                    self._session.record_correct(card_id)
                    self._session.seen.add(card_id)
                else:
                    # ease 3 (Good) — normal correct
                    self._session.record_correct(card_id)
            ok = record_answer(self._col, card_id, ease)
            self.answerRecorded.emit(ok)
        except Exception as e:
            print(f"[Hanafuda] recordAnswer error: {e}")
            self.answerRecorded.emit(False)


class HanafudaWindow(QDialog):
    def __init__(self, mw):
        super().__init__(mw)
        self.mw = mw
        self.setWindowTitle("🌸 Hanafuda Koi-Koi")
        # Size to 90% of available screen height so taskbar doesn't cover it
        from aqt.qt import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()  # excludes taskbar
            w = min(980, geo.width())
            h2 = min(860, int(geo.height() * 0.95))
            self.resize(w, h2)
            self.setMinimumSize(800, 500)
        else:
            self.resize(980, 800)
            self.setMinimumSize(800, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QWidget()
        bar.setFixedHeight(44)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 6, 12, 6)
        bar_layout.addWidget(QLabel("Deck for vocab challenges:"))
        self.deck_combo = QComboBox()
        self.deck_combo.setMinimumWidth(260)
        self.deck_combo.currentIndexChanged.connect(self._on_deck_changed)
        bar_layout.addWidget(self.deck_combo)
        bar_layout.addStretch()
        layout.addWidget(bar)

        self.web = QWebEngineView()
        settings = self.web.settings()
        if PYQT6:
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        else:
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

        self._inject_qwebchannel()

        self.channel = QWebChannel()
        self.bridge = AnkiBridge(self.mw.col)
        self.channel.registerObject("ankiBridge", self.bridge)
        self.web.page().setWebChannel(self.channel)

        index_path = os.path.join(WEB_DIR, "index.html")
        self.web.load(QUrl.fromLocalFile(index_path))
        layout.addWidget(self.web)

        from aqt.qt import QTimer
        QTimer.singleShot(1200, self._populate_decks)

    def _inject_qwebchannel(self):
        try:
            f = QFile(":/qtwebchannel/qwebchannel.js")
            open_mode = (QIODevice.OpenModeFlag.ReadOnly if PYQT6 else QIODevice.ReadOnly)
            if f.open(open_mode):
                js_code = bytes(f.readAll()).decode('utf-8')
                f.close()
            else:
                bundled = os.path.join(WEB_DIR, "qwebchannel.js")
                with open(bundled, 'r', encoding='utf-8') as bf:
                    js_code = bf.read()
            script = QWebEngineScript()
            script.setName("qwebchannel")
            script.setSourceCode(js_code)
            if PYQT6:
                script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
                script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            else:
                script.setInjectionPoint(QWebEngineScript.DocumentCreation)
                script.setWorldId(QWebEngineScript.MainWorld)
            script.setRunsOnSubFrames(False)
            self.web.page().scripts().insert(script)
            print("[Hanafuda] qwebchannel.js injected")
        except Exception as e:
            print(f"[Hanafuda] qwebchannel injection error: {e}")

    def _populate_decks(self):
        try:
            decks = get_decks(self.mw.col)
            self.deck_combo.addItem("All decks", -1)
            for d in decks:
                self.deck_combo.addItem(d["name"], d["id"])
        except Exception as e:
            print(f"[Hanafuda] _populate_decks error: {e}")

    def _on_deck_changed(self, index):
        deck_id = self.deck_combo.itemData(index)
        if deck_id is not None:
            self.bridge.setDeck(int(deck_id))
