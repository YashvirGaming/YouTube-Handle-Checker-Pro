import csv
import json
import logging
import os
import platform
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from logging.handlers import RotatingFileHandler

import httpx
import PySide6
from PySide6.QtCore import (
    QObject,
    QSettings,
    QStandardPaths,
    QStringListModel,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QCompleter,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "YouTube Handle Checker Pro"
APP_ID = "YouTubeHandleChecker"
ORG_ID = "YashvirGaming"
APP_BRAND = "Yashvir Gaming"
APP_VERSION = "1.0.0"
APP_STAGE = "Beta"
BUILD_DATE = "2026-10-24"
MAX_BULK = 500
DEFAULT_THEME = "Cyber Cyan"
HANDLE_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,30}$")
HANDLE_RULE = "Use 3–30 characters: letters, numbers, dots, underscores or hyphens."

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

STATUS_LABEL = {
    "available": "✅ Available",
    "taken": "❌ Taken",
    "error": "⚠️ Error",
    "invalid": "🚫 Invalid",
    "pending": "⏳ Pending",
    "skipped": "⏸ Skipped",
}

STATUS_COLOR_KEY = {
    "available": "ok",
    "taken": "bad",
    "error": "warn",
    "invalid": "warn",
    "pending": "muted",
    "skipped": "muted",
}

DEFAULTS = {
    "theme": DEFAULT_THEME,
    "timeout": 10,
    "retries": 1,
    "workers": 5,
    "delay_ms": 150,
    "always_on_top": False,
    "save_history": True,
    "auto_copy": False,
}

THEMES = {
    "Cyber Cyan": dict(bg="#0d0e15", panel="#141624", card="#1a1c29", border="#2a2d42", text="#ffffff", muted="#8b8ea8", accent="#4facfe", accent2="#00f2fe", ok="#00ff87", bad="#ff3366", warn="#ff9f43", btn_text="#0d0e15"),
    "Midnight Purple": dict(bg="#0f0a1f", panel="#171030", card="#1f1740", border="#352a63", text="#f3ecff", muted="#9a8fc4", accent="#8e2de2", accent2="#c471ed", ok="#4ff0a8", bad="#ff4d8d", warn="#ffb454", btn_text="#ffffff"),
    "Crimson Night": dict(bg="#130809", panel="#1d0e11", card="#261418", border="#43222a", text="#fff1f2", muted="#b08a90", accent="#ff416c", accent2="#ff4b2b", ok="#2ee59d", bad="#ff5e7e", warn="#ffb347", btn_text="#ffffff"),
    "Emerald Matrix": dict(bg="#06100c", panel="#0a1a13", card="#0f241a", border="#1c4733", text="#e8fff3", muted="#7fb59b", accent="#11998e", accent2="#38ef7d", ok="#38ef7d", bad="#ff5470", warn="#ffc857", btn_text="#04120b"),
    "Sunset Blaze": dict(bg="#160c10", panel="#21121a", card="#2b1822", border="#4d2a3a", text="#fff4ec", muted="#c19a96", accent="#ff7e5f", accent2="#feb47b", ok="#7bed9f", bad="#ff4d6d", warn="#ffd166", btn_text="#1a0c0c"),
    "Ocean Blue": dict(bg="#07121f", panel="#0c1b2e", card="#112640", border="#1f3d63", text="#eaf4ff", muted="#86a5c9", accent="#2193b0", accent2="#6dd5ed", ok="#3ddc97", bad="#ff5c7a", warn="#ffb74d", btn_text="#04121f"),
    "Neon Aurora": dict(bg="#0e0a17", panel="#160f24", card="#1e1530", border="#3a2a5a", text="#fdf2ff", muted="#a98fc4", accent="#f093fb", accent2="#f5576c", ok="#5cffb0", bad="#ff4d6d", warn="#ffc857", btn_text="#1a0b22"),
    "AMOLED Black": dict(bg="#000000", panel="#0a0a0a", card="#111111", border="#262626", text="#f5f5f5", muted="#8a8a8a", accent="#e0e0e0", accent2="#ffffff", ok="#00e676", bad="#ff1744", warn="#ffab00", btn_text="#000000"),
    "Snow Light": dict(bg="#f4f6fb", panel="#ffffff", card="#ffffff", border="#d6dbea", text="#1b1f33", muted="#6a7090", accent="#3a7bd5", accent2="#00d2ff", ok="#0e9f6e", bad="#e0245e", warn="#d9770a", btn_text="#ffffff"),
}

log = logging.getLogger(APP_ID)


def data_dir():
    path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    os.makedirs(path, exist_ok=True)
    return path


def setup_logging():
    handler = RotatingFileHandler(
        os.path.join(data_dir(), "app.log"), maxBytes=512_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    log.setLevel(logging.INFO)
    log.addHandler(handler)


def install_exception_hook():
    def hook(exc_type, exc, tb):
        log.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook


def normalize_handle(text):
    text = text.strip()
    match = re.search(r"youtube\.com/@([^/?#\s]+)", text, re.IGNORECASE)
    if match:
        text = match.group(1)
    return text.lstrip("@").strip()


def parse_handles(raw):
    seen = {}
    for token in re.split(r"[\s,;]+", raw):
        handle = normalize_handle(token)
        if handle and handle.lower() not in seen:
            seen[handle.lower()] = handle
    return list(seen.values())


def build_alternatives(handle):
    base = handle.rstrip("._-")
    suffixes = ["official", "hq", "tv", "yt", "live", "gaming", "real", "plays", "studio", "channel", "online", "world"]
    underscored = ["official", "tv", "hq", "yt"]
    prefixes = ["the", "its", "real", "official", "mr", "im"]
    candidates = [f"{base}{s}" for s in suffixes]
    candidates += [f"{base}_{s}" for s in underscored]
    candidates += [f"{p}{base}" for p in prefixes]
    candidates += [f"{base}1", f"{base}7", f"{base}x", f"{base}.official"]
    result = []
    for candidate in candidates:
        if HANDLE_PATTERN.match(candidate) and candidate.lower() != handle.lower() and candidate not in result:
            result.append(candidate)
    return result[:30]


def make_client():
    return httpx.Client(headers=REQUEST_HEADERS, follow_redirects=False, limits=httpx.Limits(max_connections=16))


def probe_handle(client, handle, timeout):
    url = f"https://www.youtube.com/@{handle}"
    try:
        response = client.get(url, timeout=float(timeout))
    except httpx.RequestError as exc:
        log.warning("Request failed for @%s: %s", handle, type(exc).__name__)
        return "error", "Connection Error: Handshake blocked."
    code = response.status_code
    if code == 404:
        return "available", f"HTTP {code}"
    if code in (200, 302):
        return "taken", f"HTTP {code}"
    return "error", f"Server response code: {code}"


def probe_with_retry(client, handle, timeout, retries, cancel=None):
    attempt = 0
    while True:
        status, detail = probe_handle(client, handle, timeout)
        if status != "error" or attempt >= retries:
            return status, detail
        if cancel is not None and cancel.is_set():
            return "cancelled", "Cancelled"
        attempt += 1
        time.sleep(min(1.5 * attempt, 4.0))


def default_name(prefix, ext):
    return f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.{ext}"


def write_csv(path, header, rows):
    try:
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            writer.writerows(rows)
    except OSError as exc:
        log.error("CSV export failed: %s", exc)
        return f"Export failed: {exc}"
    return f"Exported {len(rows)} rows to {path}"


def write_lines(path, lines):
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    except OSError as exc:
        log.error("Text export failed: %s", exc)
        return f"Export failed: {exc}"
    return f"Exported {len(lines)} handles to {path}"


def build_app_icon(theme):
    pix = QPixmap(128, 128)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(0, 0, 128, 128)
    gradient.setColorAt(0, QColor(theme["accent"]))
    gradient.setColorAt(1, QColor(theme["accent2"]))
    painter.setBrush(gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(8, 8, 112, 112, 28, 28)
    painter.setPen(QColor(theme["btn_text"]))
    painter.setFont(QFont("Segoe UI", 54, QFont.Weight.Bold))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "@")
    painter.end()
    return QIcon(pix)


def build_stylesheet(t):
    bg, panel, card, border = t["bg"], t["panel"], t["card"], t["border"]
    text, muted, accent, accent2 = t["text"], t["muted"], t["accent"], t["accent2"]
    ok, bad, btn = t["ok"], t["bad"], t["btn_text"]
    hover1 = QColor(accent).lighter(118).name()
    hover2 = QColor(accent2).lighter(118).name()
    return f"""
QWidget {{ color: {text}; font-family: 'Segoe UI', 'Inter', 'Arial', sans-serif; font-size: 13px; }}
QMainWindow, QWidget#Root, QWidget#Page {{ background-color: {bg}; }}
QDialog, QMessageBox {{ background-color: {panel}; }}
QLabel {{ background: transparent; }}
QLabel#AppTitle {{ font-size: 24px; font-weight: bold; letter-spacing: 1px; }}
QLabel#Muted {{ color: {muted}; font-size: 12px; }}
QLabel#Section {{ color: {muted}; font-size: 11px; font-weight: bold; letter-spacing: 2px; }}
QLabel#Badge {{ background-color: {accent}; color: {btn}; border-radius: 9px; padding: 3px 10px; font-size: 11px; font-weight: bold; }}
QLabel#AtSign {{ color: {accent2}; font-size: 22px; font-weight: bold; }}
QLabel#ResultBig {{ font-size: 20px; font-weight: bold; }}
QFrame#Card {{ background-color: {panel}; border: 1px solid {border}; border-radius: 12px; }}
QPushButton {{ background-color: {card}; border: 1px solid {border}; border-radius: 8px; padding: 8px 16px; color: {text}; font-weight: bold; }}
QPushButton:hover {{ border-color: {accent}; color: {accent}; }}
QPushButton:disabled {{ background-color: {panel}; color: {muted}; border-color: {border}; }}
QPushButton#Primary {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {accent2}); border: none; color: {btn}; font-size: 14px; padding: 10px 18px; }}
QPushButton#Primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {hover1}, stop:1 {hover2}); color: {btn}; }}
QPushButton#Primary:disabled {{ background: {border}; color: {muted}; }}
QPushButton#Danger:hover {{ border-color: {bad}; color: {bad}; }}
QPushButton#Success {{ border-color: {ok}; color: {ok}; }}
QPushButton#Success:hover {{ background-color: {ok}; color: {btn}; }}
QLineEdit, QPlainTextEdit, QTextBrowser, QComboBox, QSpinBox {{ background-color: {card}; border: 2px solid {border}; border-radius: 8px; color: {text}; padding: 7px 10px; font-size: 14px; selection-background-color: {accent}; selection-color: {btn}; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 2px solid {accent2}; }}
QTextBrowser#AboutView {{ background-color: {panel}; border: 1px solid {border}; border-radius: 12px; padding: 14px; font-size: 13px; }}
QComboBox QAbstractItemView {{ background-color: {card}; border: 1px solid {border}; color: {text}; selection-background-color: {accent}; selection-color: {btn}; }}
QListView {{ background-color: {card}; border: 1px solid {border}; color: {text}; selection-background-color: {accent}; selection-color: {btn}; }}
QCheckBox {{ spacing: 10px; background: transparent; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 2px solid {border}; background-color: {card}; }}
QCheckBox::indicator:hover {{ border-color: {accent}; }}
QCheckBox::indicator:checked {{ background-color: {accent}; border-color: {accent}; }}
QTabWidget::pane {{ border: 1px solid {border}; border-radius: 10px; background-color: {bg}; top: -1px; }}
QTabBar::tab {{ background-color: {panel}; color: {muted}; padding: 9px 18px; margin-right: 4px; border: 1px solid {border}; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; }}
QTabBar::tab:selected {{ background-color: {card}; color: {accent2}; border-color: {accent}; }}
QTabBar::tab:hover:!selected {{ color: {text}; }}
QTableWidget {{ background-color: {card}; alternate-background-color: {panel}; border: 1px solid {border}; border-radius: 8px; gridline-color: {border}; selection-background-color: {accent}; selection-color: {btn}; }}
QTableWidget::item {{ padding: 4px 8px; }}
QHeaderView::section {{ background-color: {panel}; color: {muted}; border: none; border-bottom: 1px solid {border}; padding: 8px; font-weight: bold; }}
QTableCornerButton::section {{ background-color: {panel}; border: none; }}
QProgressBar {{ background-color: {card}; border: none; border-radius: 4px; text-align: center; }}
QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent2}, stop:1 {accent}); border-radius: 4px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {accent}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {border}; border-radius: 5px; min-width: 28px; }}
QScrollBar::handle:horizontal:hover {{ background: {accent}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QMenuBar {{ background-color: {panel}; border-bottom: 1px solid {border}; }}
QMenuBar::item {{ padding: 6px 12px; background: transparent; }}
QMenuBar::item:selected {{ background-color: {card}; border-radius: 4px; }}
QMenu {{ background-color: {panel}; border: 1px solid {border}; padding: 4px; }}
QMenu::item {{ padding: 6px 26px; border-radius: 4px; }}
QMenu::item:selected {{ background-color: {accent}; color: {btn}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 8px; }}
QStatusBar {{ background-color: {panel}; color: {muted}; border-top: 1px solid {border}; }}
QStatusBar QLabel {{ color: {muted}; font-size: 12px; }}
QToolTip {{ background-color: {card}; color: {text}; border: 1px solid {accent}; padding: 5px; }}
"""


def build_about_html(t):
    return f"""
<div style="color:{t['text']};">
<h1 style="color:{t['accent2']}; margin-bottom:0;">{APP_NAME}</h1>
<p style="color:{t['muted']}; margin-top:2px;">Version {APP_VERSION} {APP_STAGE} &nbsp;·&nbsp; Build {BUILD_DATE}</p>
<h3 style="color:{t['accent']};">Developed by {APP_BRAND}</h3>
<p>A fast, key-free desktop scanner that tells you whether a YouTube @handle is free before you try to claim it. No API key, no account, no login — just a lightweight request to the public channel URL.</p>

<h3 style="color:{t['accent']};">Features</h3>
<ul>
<li>Instant single-handle availability check with copy &amp; open-channel actions</li>
<li>Bulk scanner (up to {MAX_BULK} handles) with multi-threading, stop control and CSV / TXT export</li>
<li>One-click alternative suggestions for taken handles</li>
<li>Persistent history with search, filters and re-check</li>
<li>9 hand-tuned themes, live switching, remembered between launches</li>
<li>Configurable timeout, retries, worker count and request delay</li>
<li>Always-on-top mode, auto-copy, window position memory, rotating log file</li>
</ul>

<h3 style="color:{t['accent']};">Keyboard Shortcuts</h3>
<ul>
<li><b>Ctrl+1 … Ctrl+5</b> — switch tabs</li>
<li><b>Ctrl+L</b> — focus the handle box</li>
<li><b>Ctrl+T</b> — cycle theme</li>
<li><b>F1</b> — open this page</li>
<li><b>Ctrl+Q</b> — quit</li>
</ul>

<h3 style="color:{t['accent']};">Changelog</h3>
<p><b>v{APP_VERSION} {APP_STAGE}</b> — First public build. Tabbed interface, bulk scanner, history, settings, theme engine, credits panel, input validation, retry handling and persistent preferences.</p>

<h3 style="color:{t['accent']};">Roadmap</h3>
<ul>
<li>Watch-list that alerts when a taken handle becomes free</li>
<li>Proxy support for very large scans</li>
<li>Custom user-defined themes</li>
</ul>

<h3 style="color:{t['accent']};">Credits</h3>
<ul>
<li><b>Design, development &amp; QA</b> — {APP_BRAND}</li>
<li><b>Built with</b> — Python, PySide6 (Qt for Python), httpx</li>
<li><b>Thanks</b> — everyone testing the beta and sending feedback</li>
</ul>

<h3 style="color:{t['accent']};">Disclaimer</h3>
<p style="color:{t['muted']};">This tool is not affiliated with, endorsed by, or sponsored by YouTube or Google. Results are based on public HTTP responses and are a best-effort indication only; YouTube may still reject reserved, blocked or policy-restricted handles when you try to claim them.</p>

<p style="color:{t['muted']};">© 2026 {APP_BRAND}. All rights reserved.</p>
</div>
"""


def build_info_text():
    return "\n".join(
        [
            f"{APP_NAME} v{APP_VERSION} {APP_STAGE}",
            f"By {APP_BRAND}",
            f"Build: {BUILD_DATE}",
            f"Python: {platform.python_version()}",
            f"PySide6: {PySide6.__version__}",
            f"httpx: {httpx.__version__}",
            f"OS: {platform.platform()}",
        ]
    )


def section_label(text):
    label = QLabel(text)
    label.setObjectName("Section")
    return label


def muted_label(text=""):
    label = QLabel(text)
    label.setObjectName("Muted")
    label.setWordWrap(True)
    return label


def make_button(text, role=None, height=None):
    button = QPushButton(text)
    if role:
        button.setObjectName(role)
    if height:
        button.setMinimumHeight(height)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def make_card():
    card = QFrame()
    card.setObjectName("Card")
    return card


def make_table(headers, stretch_col):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    for index in range(len(headers)):
        header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(stretch_col, QHeaderView.ResizeMode.Stretch)
    return table


def status_item(ctx, status):
    item = QTableWidgetItem(STATUS_LABEL.get(status, status))
    item.setData(Qt.ItemDataRole.UserRole, status)
    item.setForeground(QColor(ctx.theme[STATUS_COLOR_KEY.get(status, "muted")]))
    return item


def recolor_table(ctx, table, column):
    for row in range(table.rowCount()):
        item = table.item(row, column)
        if item is not None:
            key = STATUS_COLOR_KEY.get(item.data(Qt.ItemDataRole.UserRole), "muted")
            item.setForeground(QColor(ctx.theme[key]))


class Config:
    def __init__(self):
        self.settings = QSettings(ORG_ID, APP_ID)

    def get(self, key):
        default = DEFAULTS[key]
        value = self.settings.value(key, default)
        if isinstance(default, bool):
            return value in (True, "true", "True", 1, "1")
        if isinstance(default, int):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        return str(value)

    def set(self, key, value):
        self.settings.setValue(key, value)


class HistoryStore:
    LIMIT = 1000

    def __init__(self):
        self.path = os.path.join(data_dir(), "history.json")
        self.entries = []
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            self.entries = []
            return
        if isinstance(data, list):
            self.entries = [
                e for e in data if isinstance(e, dict) and "handle" in e and "status" in e
            ][-self.LIMIT:]

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.entries, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError as exc:
            log.error("History save failed: %s", exc)

    def add(self, handle, status, detail):
        self.entries.append(
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "handle": handle,
                "status": status,
                "detail": detail,
            }
        )
        del self.entries[: -self.LIMIT]

    def clear(self):
        self.entries = []
        self.save()


class Context(QObject):
    theme_changed = Signal()
    history_changed = Signal()
    stats_changed = Signal()
    window_flags_changed = Signal()
    notify = Signal(str)

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.history = HistoryStore()
        self.session_checked = 0
        self.session_available = 0
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(700)
        self.save_timer.timeout.connect(self.history.save)

    @property
    def theme(self):
        return THEMES.get(self.config.get("theme"), THEMES[DEFAULT_THEME])

    def set_theme(self, name):
        if name in THEMES:
            self.config.set("theme", name)
            self.theme_changed.emit()

    def cycle_theme(self):
        names = list(THEMES)
        current = self.config.get("theme")
        index = names.index(current) if current in names else 0
        self.set_theme(names[(index + 1) % len(names)])

    def record(self, handle, status, detail):
        if status not in ("available", "taken"):
            return
        self.session_checked += 1
        if status == "available":
            self.session_available += 1
        self.stats_changed.emit()
        if self.config.get("save_history"):
            self.history.add(handle, status, detail)
            self.save_timer.start()
            self.history_changed.emit()

    def clear_history(self):
        self.history.clear()
        self.history_changed.emit()

    def flush(self):
        self.history.save()


class SingleWorker(QThread):
    finished_check = Signal(str, str, str)

    def __init__(self, handle, timeout, retries, parent=None):
        super().__init__(parent)
        self.handle = handle
        self.timeout = timeout
        self.retries = retries

    def run(self):
        try:
            with make_client() as client:
                status, detail = probe_with_retry(client, self.handle, self.timeout, self.retries)
        except Exception:
            log.exception("Single check failed for @%s", self.handle)
            status, detail = "error", "Connection Error: Handshake blocked."
        self.finished_check.emit(self.handle, status, detail)


class BulkWorker(QThread):
    item_done = Signal(str, str, str)
    progress = Signal(int, int)
    completed = Signal(bool)

    def __init__(self, handles, timeout, retries, workers, delay_ms, parent=None):
        super().__init__(parent)
        self.handles = handles
        self.timeout = timeout
        self.retries = retries
        self.workers = max(1, workers)
        self.delay = max(0, delay_ms) / 1000.0
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def task(self, client, handle):
        if self.cancel_event.is_set():
            return "cancelled", "Cancelled"
        if self.delay:
            time.sleep(self.delay)
        if self.cancel_event.is_set():
            return "cancelled", "Cancelled"
        return probe_with_retry(client, handle, self.timeout, self.retries, self.cancel_event)

    def run(self):
        total = len(self.handles)
        done = 0
        try:
            with make_client() as client:
                with ThreadPoolExecutor(max_workers=self.workers) as pool:
                    futures = {pool.submit(self.task, client, h): h for h in self.handles}
                    for future in as_completed(futures):
                        handle = futures[future]
                        try:
                            status, detail = future.result()
                        except Exception as exc:
                            log.exception("Bulk task failed for @%s", handle)
                            status, detail = "error", str(exc)
                        done += 1
                        if status != "cancelled":
                            self.item_done.emit(handle, status, detail)
                        self.progress.emit(done, total)
        except Exception:
            log.exception("Bulk worker crashed")
        self.completed.emit(self.cancel_event.is_set())


class CheckerPage(QWidget):
    alternatives_requested = Signal(list)

    def __init__(self, ctx):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx
        self.worker = None
        self.current_handle = ""
        self.state = ("idle", "", "")

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        input_card = make_card()
        ic = QVBoxLayout(input_card)
        ic.setContentsMargins(20, 18, 20, 18)
        ic.setSpacing(12)
        ic.addWidget(section_label("CHANNEL HANDLE"))

        row = QHBoxLayout()
        row.setSpacing(8)
        at_sign = QLabel("@")
        at_sign.setObjectName("AtSign")
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Enter handle (e.g., JohnDoe) or paste a channel link")
        self.entry.setMinimumHeight(44)
        self.entry.setMaxLength(150)
        self.entry.setClearButtonEnabled(True)
        self.entry.returnPressed.connect(self.start_checking)
        row.addWidget(at_sign)
        row.addWidget(self.entry, 1)
        ic.addLayout(row)

        ic.addWidget(muted_label("3–30 characters · letters, numbers, dots, underscores and hyphens"))

        self.btn_check = make_button("Check Availability", "Primary", 46)
        self.btn_check.clicked.connect(self.start_checking)
        ic.addWidget(self.btn_check)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.hide()
        ic.addWidget(self.progress)
        root.addWidget(input_card)

        result_card = make_card()
        rc = QVBoxLayout(result_card)
        rc.setContentsMargins(20, 18, 20, 20)
        rc.setSpacing(10)
        rc.addWidget(section_label("RESULT"))
        self.result_label = QLabel("")
        self.result_label.setObjectName("ResultBig")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setWordWrap(True)
        self.result_label.setMinimumHeight(40)
        rc.addWidget(self.result_label)
        self.detail_label = muted_label()
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rc.addWidget(self.detail_label)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch(1)
        self.btn_copy = make_button("📋 Copy Handle", "Success", 36)
        self.btn_copy.clicked.connect(self.copy_handle)
        self.btn_open = make_button("🔗 Open Channel", None, 36)
        self.btn_open.clicked.connect(self.open_channel)
        self.btn_alt = make_button("💡 Find Alternatives", None, 36)
        self.btn_alt.clicked.connect(self.request_alternatives)
        for button in (self.btn_copy, self.btn_open, self.btn_alt):
            button.hide()
            actions.addWidget(button)
        actions.addStretch(1)
        rc.addLayout(actions)
        root.addWidget(result_card)
        root.addStretch(1)

        self.completer_model = QStringListModel(self)
        completer = QCompleter(self.completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.entry.setCompleter(completer)

        ctx.theme_changed.connect(self.render)
        ctx.history_changed.connect(self.refresh_completer)
        self.refresh_completer()
        self.render()

    def refresh_completer(self):
        handles = list(dict.fromkeys(e["handle"] for e in reversed(self.ctx.history.entries)))
        self.completer_model.setStringList(handles[:200])

    def set_state(self, status, text, detail):
        self.state = (status, text, detail)
        self.render()

    def render(self):
        status, text, detail = self.state
        color = self.ctx.theme[STATUS_COLOR_KEY.get(status, "muted")]
        self.result_label.setText(text or "Ready when you are.")
        self.result_label.setStyleSheet(f"color: {color};")
        self.detail_label.setText(detail)
        self.btn_copy.setVisible(status == "available")
        self.btn_open.setVisible(status == "taken")
        self.btn_alt.setVisible(status == "taken")

    def set_busy(self, busy):
        self.btn_check.setDisabled(busy)
        self.entry.setDisabled(busy)
        self.progress.setVisible(busy)
        if not busy:
            self.entry.setFocus()

    def check_handle(self, handle):
        self.entry.setText(handle)
        self.start_checking()

    def start_checking(self):
        if self.worker is not None:
            return
        handle = normalize_handle(self.entry.text())
        if not handle:
            self.set_state("invalid", "⚠️ Please enter a handle name!", "")
            return
        if not HANDLE_PATTERN.match(handle):
            self.set_state("invalid", f"🚫 @{handle} is not a valid handle", HANDLE_RULE)
            return
        self.entry.setText(handle)
        self.set_busy(True)
        self.set_state("idle", "Checking…", f"Contacting YouTube for @{handle}")
        config = self.ctx.config
        worker = SingleWorker(handle, config.get("timeout"), config.get("retries"), self)
        worker.finished_check.connect(self.on_finished)
        worker.finished.connect(worker.deleteLater)
        self.worker = worker
        worker.start()

    def on_finished(self, handle, status, detail):
        self.worker = None
        self.set_busy(False)
        self.current_handle = handle
        self.ctx.record(handle, status, detail)
        if status == "available":
            self.set_state(
                "available",
                f"✅ @{handle} is Available!",
                f"No channel was found at this handle ({detail}). YouTube may still reject reserved or policy-restricted handles.",
            )
            if self.ctx.config.get("auto_copy"):
                QApplication.clipboard().setText(f"@{handle}")
                self.ctx.notify.emit(f"Copied @{handle} to clipboard")
        elif status == "taken":
            self.set_state("taken", f"❌ @{handle} is Taken", f"A channel already uses this handle ({detail}).")
        else:
            self.set_state("error", f"⚠️ {detail}", "Check your internet connection or try again in a moment.")

    def copy_handle(self):
        if not self.current_handle:
            return
        QApplication.clipboard().setText(f"@{self.current_handle}")
        self.btn_copy.setText("✨ Copied!")
        QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 Copy Handle"))

    def open_channel(self):
        if self.current_handle:
            QDesktopServices.openUrl(QUrl(f"https://www.youtube.com/@{self.current_handle}"))

    def request_alternatives(self):
        if self.current_handle:
            self.alternatives_requested.emit(build_alternatives(self.current_handle))

    def shutdown(self):
        if self.worker is not None:
            self.worker.wait(3000)


class BulkPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx
        self.worker = None
        self.rows = {}
        self.counts = {}
        self.total = 0
        self.done = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(14)

        input_card = make_card()
        ic = QVBoxLayout(input_card)
        ic.setContentsMargins(20, 16, 20, 16)
        ic.setSpacing(10)
        ic.addWidget(section_label("BULK SCANNER"))
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(
            "Paste handles — one per line, or separated by commas / spaces.\nFull youtube.com/@handle links work too."
        )
        self.input.setMinimumHeight(80)
        self.input.setMaximumHeight(120)
        ic.addWidget(self.input)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_start = make_button("▶ Start Scan", "Primary", 38)
        self.btn_start.clicked.connect(self.start_bulk)
        self.btn_stop = make_button("⏹ Stop", "Danger", 38)
        self.btn_stop.setDisabled(True)
        self.btn_stop.clicked.connect(self.stop_bulk)
        self.btn_import = make_button("📂 Import…", None, 38)
        self.btn_import.clicked.connect(self.import_file)
        self.btn_clear = make_button("🧹 Clear", None, 38)
        self.btn_clear.clicked.connect(self.clear_all)
        buttons.addWidget(self.btn_start, 2)
        buttons.addWidget(self.btn_stop, 1)
        buttons.addWidget(self.btn_import, 1)
        buttons.addWidget(self.btn_clear, 1)
        ic.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.hide()
        ic.addWidget(self.progress)
        root.addWidget(input_card)

        head = QHBoxLayout()
        head.addWidget(section_label("RESULTS"))
        head.addStretch(1)
        self.chk_filter = QCheckBox("Show available only")
        self.chk_filter.toggled.connect(self.apply_filter)
        head.addWidget(self.chk_filter)
        root.addLayout(head)

        self.table = make_table(["Handle", "Status", "Detail"], 2)
        root.addWidget(self.table, 1)

        self.summary = muted_label("No scan yet.")
        root.addWidget(self.summary)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.btn_copy = make_button("📋 Copy Available", "Success", 36)
        self.btn_copy.clicked.connect(self.copy_available)
        self.btn_csv = make_button("📄 Export CSV", None, 36)
        self.btn_csv.clicked.connect(self.export_csv)
        self.btn_txt = make_button("📝 Export Available (TXT)", None, 36)
        self.btn_txt.clicked.connect(self.export_available)
        footer.addWidget(self.btn_copy)
        footer.addWidget(self.btn_csv)
        footer.addWidget(self.btn_txt)
        footer.addStretch(1)
        root.addLayout(footer)

        ctx.theme_changed.connect(self.on_theme)

    def on_theme(self):
        recolor_table(self.ctx, self.table, 1)

    def set_handles(self, handles):
        self.input.setPlainText("\n".join(handles))

    def set_busy(self, busy):
        self.btn_start.setDisabled(busy)
        self.btn_stop.setEnabled(busy)
        self.btn_import.setDisabled(busy)
        self.btn_clear.setDisabled(busy)
        self.input.setReadOnly(busy)
        self.progress.setVisible(busy)

    def update_summary(self):
        c = self.counts
        text = (
            f"✅ Available: {c.get('available', 0)}     ❌ Taken: {c.get('taken', 0)}     "
            f"⚠️ Errors: {c.get('error', 0)}     🚫 Invalid: {c.get('invalid', 0)}"
        )
        if self.worker is not None:
            text += f"     ·     Progress: {self.done} / {self.total}"
        self.summary.setText(text)

    def prepare_table(self, handles):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(handles))
        self.rows = {}
        self.counts = {}
        valid = []
        for index, handle in enumerate(handles):
            item = QTableWidgetItem(f"@{handle}")
            item.setData(Qt.ItemDataRole.UserRole, handle)
            self.table.setItem(index, 0, item)
            self.rows[handle.lower()] = index
            if HANDLE_PATTERN.match(handle):
                self.table.setItem(index, 1, status_item(self.ctx, "pending"))
                self.table.setItem(index, 2, QTableWidgetItem(""))
                valid.append(handle)
            else:
                self.table.setItem(index, 1, status_item(self.ctx, "invalid"))
                self.table.setItem(index, 2, QTableWidgetItem(HANDLE_RULE))
                self.counts["invalid"] = self.counts.get("invalid", 0) + 1
        return valid

    def start_bulk(self):
        if self.worker is not None:
            return
        handles = parse_handles(self.input.toPlainText())
        if not handles:
            self.ctx.notify.emit("Add at least one handle to scan.")
            return
        if len(handles) > MAX_BULK:
            handles = handles[:MAX_BULK]
            self.ctx.notify.emit(f"Limited to the first {MAX_BULK} handles.")
        valid = self.prepare_table(handles)
        self.apply_filter()
        self.total = len(valid)
        self.done = 0
        if not valid:
            self.table.setSortingEnabled(True)
            self.update_summary()
            self.ctx.notify.emit("No valid handles to scan.")
            return
        self.progress.setRange(0, self.total)
        self.progress.setValue(0)
        config = self.ctx.config
        worker = BulkWorker(
            valid,
            config.get("timeout"),
            config.get("retries"),
            config.get("workers"),
            config.get("delay_ms"),
            self,
        )
        worker.item_done.connect(self.on_item)
        worker.progress.connect(self.on_progress)
        worker.completed.connect(self.on_complete)
        worker.finished.connect(worker.deleteLater)
        self.worker = worker
        self.set_busy(True)
        self.update_summary()
        worker.start()

    def stop_bulk(self):
        if self.worker is not None:
            self.worker.cancel()
            self.btn_stop.setDisabled(True)
            self.ctx.notify.emit("Stopping scan…")

    def on_item(self, handle, status, detail):
        row = self.rows.get(handle.lower())
        if row is None:
            return
        self.table.setItem(row, 1, status_item(self.ctx, status))
        self.table.setItem(row, 2, QTableWidgetItem(detail))
        self.counts[status] = self.counts.get(status, 0) + 1
        self.ctx.record(handle, status, detail)
        self.update_summary()

    def on_progress(self, done, total):
        self.done = done
        self.progress.setValue(done)
        self.update_summary()

    def on_complete(self, cancelled):
        self.worker = None
        self.set_busy(False)
        if cancelled:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 1)
                if item is not None and item.data(Qt.ItemDataRole.UserRole) == "pending":
                    self.table.setItem(row, 1, status_item(self.ctx, "skipped"))
                    self.table.setItem(row, 2, QTableWidgetItem("Scan stopped"))
        self.table.setSortingEnabled(True)
        self.apply_filter()
        self.update_summary()
        found = self.counts.get("available", 0)
        self.ctx.notify.emit(
            f"Scan stopped — {found} available found" if cancelled else f"Scan complete — {found} available found"
        )

    def apply_filter(self):
        only_available = self.chk_filter.isChecked()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            status = item.data(Qt.ItemDataRole.UserRole) if item is not None else ""
            self.table.setRowHidden(row, only_available and status != "available")

    def available_handles(self):
        found = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == "available":
                found.append(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole))
        return found

    def copy_available(self):
        found = self.available_handles()
        if not found:
            self.ctx.notify.emit("No available handles to copy yet.")
            return
        QApplication.clipboard().setText("\n".join(f"@{h}" for h in found))
        self.ctx.notify.emit(f"Copied {len(found)} available handles")

    def export_csv(self):
        if self.table.rowCount() == 0:
            self.ctx.notify.emit("Nothing to export yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export results", default_name("bulk_results", "csv"), "CSV files (*.csv)"
        )
        if not path:
            return
        rows = []
        for row in range(self.table.rowCount()):
            handle = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            status = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
            detail = self.table.item(row, 2).text()
            rows.append((handle, status, detail))
        self.ctx.notify.emit(write_csv(path, ("Handle", "Status", "Detail"), rows))

    def export_available(self):
        found = self.available_handles()
        if not found:
            self.ctx.notify.emit("No available handles to export yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export available handles", default_name("available_handles", "txt"), "Text files (*.txt)"
        )
        if not path:
            return
        self.ctx.notify.emit(write_lines(path, [f"@{h}" for h in found]))

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import handles", "", "Text / CSV files (*.txt *.csv *.lst);;All files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except OSError as exc:
            self.ctx.notify.emit(f"Import failed: {exc}")
            return
        existing = self.input.toPlainText().strip()
        merged = parse_handles(f"{existing}\n{content}")
        self.input.setPlainText("\n".join(merged))
        self.ctx.notify.emit(f"Imported {len(merged)} unique handles")

    def clear_all(self):
        self.input.clear()
        self.table.setRowCount(0)
        self.rows = {}
        self.counts = {}
        self.summary.setText("No scan yet.")

    def shutdown(self):
        if self.worker is not None:
            self.worker.cancel()
            if not self.worker.wait(4000):
                self.worker.terminate()
                self.worker.wait(1000)


class HistoryPage(QWidget):
    recheck_requested = Signal(str)

    def __init__(self, ctx):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search handles…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        self.filter = QComboBox()
        self.filter.addItems(["All results", "Available only", "Taken only"])
        self.filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.search, 1)
        top.addWidget(self.filter)
        root.addLayout(top)

        self.table = make_table(["Time", "Handle", "Status"], 1)
        self.table.cellDoubleClicked.connect(self.on_double_click)
        root.addWidget(self.table, 1)

        self.count_label = muted_label()
        root.addWidget(self.count_label)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.btn_recheck = make_button("🔄 Re-check Selected", "Primary", 36)
        self.btn_recheck.clicked.connect(self.recheck_selected)
        self.btn_copy = make_button("📋 Copy Selected", None, 36)
        self.btn_copy.clicked.connect(self.copy_selected)
        self.btn_export = make_button("📄 Export CSV", None, 36)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_clear = make_button("🗑 Clear History", "Danger", 36)
        self.btn_clear.clicked.connect(self.clear_history)
        footer.addWidget(self.btn_recheck)
        footer.addWidget(self.btn_copy)
        footer.addWidget(self.btn_export)
        footer.addStretch(1)
        footer.addWidget(self.btn_clear)
        root.addLayout(footer)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(300)
        self.refresh_timer.timeout.connect(self.refresh)
        ctx.history_changed.connect(self.refresh_timer.start)
        ctx.theme_changed.connect(self.on_theme)
        self.refresh()

    def on_theme(self):
        recolor_table(self.ctx, self.table, 2)

    def refresh(self):
        needle = self.search.text().strip().lower().lstrip("@")
        mode = self.filter.currentIndex()
        wanted = {1: "available", 2: "taken"}.get(mode)
        entries = [
            e
            for e in reversed(self.ctx.history.entries)
            if (not needle or needle in e["handle"].lower()) and (wanted is None or e["status"] == wanted)
        ]
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(entries))
        for index, entry in enumerate(entries):
            self.table.setItem(index, 0, QTableWidgetItem(entry.get("time", "")))
            self.table.setItem(index, 1, QTableWidgetItem(f"@{entry['handle']}"))
            self.table.setItem(index, 2, status_item(self.ctx, entry["status"]))
        self.table.setUpdatesEnabled(True)
        self.count_label.setText(f"{len(entries)} of {len(self.ctx.history.entries)} entries")

    def selected_handle(self):
        row = self.table.currentRow()
        if row < 0:
            return ""
        item = self.table.item(row, 1)
        return item.text().lstrip("@") if item is not None else ""

    def on_double_click(self, row, column):
        item = self.table.item(row, 1)
        if item is not None:
            self.recheck_requested.emit(item.text().lstrip("@"))

    def recheck_selected(self):
        handle = self.selected_handle()
        if handle:
            self.recheck_requested.emit(handle)
        else:
            self.ctx.notify.emit("Select a history row first.")

    def copy_selected(self):
        handle = self.selected_handle()
        if handle:
            QApplication.clipboard().setText(f"@{handle}")
            self.ctx.notify.emit(f"Copied @{handle}")
        else:
            self.ctx.notify.emit("Select a history row first.")

    def export_csv(self):
        entries = self.ctx.history.entries
        if not entries:
            self.ctx.notify.emit("History is empty.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export history", default_name("handle_history", "csv"), "CSV files (*.csv)"
        )
        if not path:
            return
        rows = [(e.get("time", ""), e["handle"], e["status"], e.get("detail", "")) for e in entries]
        self.ctx.notify.emit(write_csv(path, ("Time", "Handle", "Status", "Detail"), rows))

    def clear_history(self):
        if not self.ctx.history.entries:
            return
        answer = QMessageBox.question(
            self,
            "Clear history",
            "Delete all saved check history? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.ctx.clear_history()
            self.ctx.notify.emit("History cleared")


def form_card(title):
    card = make_card()
    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 16, 20, 18)
    layout.setSpacing(12)
    layout.addWidget(section_label(title))
    form = QFormLayout()
    form.setHorizontalSpacing(18)
    form.setVerticalSpacing(12)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    layout.addLayout(form)
    return card, form


class SettingsPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        body.setObjectName("Page")
        scroll.setWidget(body)
        root = QVBoxLayout(body)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        appearance, form = form_card("APPEARANCE")
        self.theme_box = QComboBox()
        self.theme_box.addItems(list(THEMES))
        self.swatch = QFrame()
        self.swatch.setFixedHeight(10)
        form.addRow("Theme", self.theme_box)
        form.addRow("Preview", self.swatch)
        root.addWidget(appearance)

        network, form = form_card("NETWORK")
        self.timeout = QSpinBox()
        self.timeout.setRange(3, 30)
        self.timeout.setSuffix(" s")
        self.retries = QSpinBox()
        self.retries.setRange(0, 3)
        self.workers = QSpinBox()
        self.workers.setRange(1, 10)
        self.delay = QSpinBox()
        self.delay.setRange(0, 2000)
        self.delay.setSingleStep(50)
        self.delay.setSuffix(" ms")
        form.addRow("Request timeout", self.timeout)
        form.addRow("Retries on error", self.retries)
        form.addRow("Bulk worker threads", self.workers)
        form.addRow("Delay between requests", self.delay)
        form.addRow(muted_label("Lower threads and a longer delay reduce the chance of rate limiting on big scans."))
        root.addWidget(network)

        behaviour, form = form_card("BEHAVIOUR")
        self.chk_top = QCheckBox("Keep window always on top")
        self.chk_history = QCheckBox("Save check history")
        self.chk_copy = QCheckBox("Auto-copy handle when it is available")
        form.addRow(self.chk_top)
        form.addRow(self.chk_history)
        form.addRow(self.chk_copy)
        root.addWidget(behaviour)

        reset_row = QHBoxLayout()
        reset_row.addStretch(1)
        self.btn_reset = make_button("↺ Reset to Defaults", "Danger", 36)
        self.btn_reset.clicked.connect(self.reset_defaults)
        reset_row.addWidget(self.btn_reset)
        root.addLayout(reset_row)
        root.addStretch(1)

        config = ctx.config
        self.theme_box.currentTextChanged.connect(ctx.set_theme)
        self.timeout.valueChanged.connect(lambda v: config.set("timeout", v))
        self.retries.valueChanged.connect(lambda v: config.set("retries", v))
        self.workers.valueChanged.connect(lambda v: config.set("workers", v))
        self.delay.valueChanged.connect(lambda v: config.set("delay_ms", v))
        self.chk_top.toggled.connect(self.on_top_toggled)
        self.chk_history.toggled.connect(lambda v: config.set("save_history", v))
        self.chk_copy.toggled.connect(lambda v: config.set("auto_copy", v))

        ctx.theme_changed.connect(self.sync_theme)
        ctx.window_flags_changed.connect(self.load)
        self.load()

    def load(self):
        config = self.ctx.config
        widgets = (self.theme_box, self.timeout, self.retries, self.workers, self.delay, self.chk_top, self.chk_history, self.chk_copy)
        for widget in widgets:
            widget.blockSignals(True)
        self.theme_box.setCurrentText(config.get("theme"))
        self.timeout.setValue(config.get("timeout"))
        self.retries.setValue(config.get("retries"))
        self.workers.setValue(config.get("workers"))
        self.delay.setValue(config.get("delay_ms"))
        self.chk_top.setChecked(config.get("always_on_top"))
        self.chk_history.setChecked(config.get("save_history"))
        self.chk_copy.setChecked(config.get("auto_copy"))
        for widget in widgets:
            widget.blockSignals(False)
        self.update_swatch()

    def update_swatch(self):
        t = self.ctx.theme
        self.swatch.setStyleSheet(
            f"border: none; border-radius: 5px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t['accent']}, stop:1 {t['accent2']});"
        )

    def sync_theme(self):
        self.theme_box.blockSignals(True)
        self.theme_box.setCurrentText(self.ctx.config.get("theme"))
        self.theme_box.blockSignals(False)
        self.update_swatch()

    def on_top_toggled(self, value):
        self.ctx.config.set("always_on_top", value)
        self.ctx.window_flags_changed.emit()

    def reset_defaults(self):
        answer = QMessageBox.question(
            self,
            "Reset settings",
            "Restore all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for key, value in DEFAULTS.items():
            self.ctx.config.set(key, value)
        self.load()
        self.ctx.theme_changed.emit()
        self.ctx.window_flags_changed.emit()
        self.ctx.notify.emit("Settings restored to defaults")


class AboutPage(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.setObjectName("Page")
        self.ctx = ctx

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        self.view = QTextBrowser()
        self.view.setObjectName("AboutView")
        self.view.setOpenExternalLinks(True)
        root.addWidget(self.view, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.btn_info = make_button("📋 Copy Build Info", None, 36)
        self.btn_info.clicked.connect(self.copy_info)
        self.btn_folder = make_button("📁 Open Data Folder", None, 36)
        self.btn_folder.clicked.connect(self.open_folder)
        footer.addWidget(self.btn_info)
        footer.addWidget(self.btn_folder)
        footer.addStretch(1)
        footer.addWidget(muted_label(f"{APP_BRAND} · v{APP_VERSION} {APP_STAGE}"))
        root.addLayout(footer)

        ctx.theme_changed.connect(self.render)
        self.render()

    def render(self):
        self.view.setHtml(build_about_html(self.ctx.theme))

    def copy_info(self):
        QApplication.clipboard().setText(build_info_text())
        self.ctx.notify.emit("Build info copied to clipboard")

    def open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(data_dir()))


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(f"{APP_NAME} — by {APP_BRAND}  ·  v{APP_VERSION} {APP_STAGE}")
        self.setMinimumSize(780, 640)
        self.resize(900, 720)
        geometry = ctx.config.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 10)
        layout.setSpacing(12)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        titles.addWidget(title)
        titles.addWidget(muted_label(f"by {APP_BRAND}  ·  instant, key-free @handle availability scanner"))
        header.addLayout(titles)
        header.addStretch(1)
        badge = QLabel(f"v{APP_VERSION}  {APP_STAGE.upper()}")
        badge.setObjectName("Badge")
        header.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        self.checker = CheckerPage(ctx)
        self.bulk = BulkPage(ctx)
        self.history = HistoryPage(ctx)
        self.settings_page = SettingsPage(ctx)
        self.about = AboutPage(ctx)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.checker, "🔍 Checker")
        self.tabs.addTab(self.bulk, "📦 Bulk Scan")
        self.tabs.addTab(self.history, "🕘 History")
        self.tabs.addTab(self.settings_page, "⚙ Settings")
        self.tabs.addTab(self.about, "ℹ About & Credits")
        layout.addWidget(self.tabs, 1)

        self.session_label = QLabel()
        self.statusBar().addPermanentWidget(self.session_label)
        self.statusBar().addPermanentWidget(QLabel(f"  © {APP_BRAND}  "))
        self.statusBar().showMessage("Ready", 4000)

        self.build_menu()
        self.build_shortcuts()

        self.checker.alternatives_requested.connect(self.on_alternatives)
        self.history.recheck_requested.connect(self.on_recheck)
        ctx.notify.connect(self.show_message)
        ctx.stats_changed.connect(self.update_session)
        ctx.theme_changed.connect(self.apply_theme)
        ctx.window_flags_changed.connect(self.apply_window_flags)

        self.update_session()
        self.apply_theme()
        self.apply_window_flags()

    def build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        export_action = QAction("Export History…", self)
        export_action.triggered.connect(self.history.export_csv)
        file_menu.addAction(export_action)
        folder_action = QAction("Open Data Folder", self)
        folder_action.triggered.connect(self.about.open_folder)
        file_menu.addAction(folder_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menubar.addMenu("&View")
        theme_menu = view_menu.addMenu("Theme")
        group = QActionGroup(self)
        group.setExclusive(True)
        self.theme_actions = {}
        for name in THEMES:
            action = QAction(name, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, n=name: self.ctx.set_theme(n))
            group.addAction(action)
            theme_menu.addAction(action)
            self.theme_actions[name] = action
        self.top_action = QAction("Always on Top", self)
        self.top_action.setCheckable(True)
        self.top_action.toggled.connect(self.on_top_menu)
        view_menu.addAction(self.top_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction(f"About {APP_NAME}", self)
        about_action.setShortcut(QKeySequence("F1"))
        about_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.about))
        help_menu.addAction(about_action)

    def build_shortcuts(self):
        for index in range(self.tabs.count()):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self)
            shortcut.activated.connect(lambda i=index: self.tabs.setCurrentIndex(i))
        focus_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_shortcut.activated.connect(self.focus_input)
        theme_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        theme_shortcut.activated.connect(self.ctx.cycle_theme)

    def focus_input(self):
        self.tabs.setCurrentWidget(self.checker)
        self.checker.entry.setFocus()
        self.checker.entry.selectAll()

    def on_alternatives(self, handles):
        self.bulk.set_handles(handles)
        self.tabs.setCurrentWidget(self.bulk)
        self.bulk.start_bulk()

    def on_recheck(self, handle):
        self.tabs.setCurrentWidget(self.checker)
        self.checker.check_handle(handle)

    def show_message(self, message):
        self.statusBar().showMessage(message, 6000)

    def update_session(self):
        self.session_label.setText(
            f"Session: {self.ctx.session_checked} checked · {self.ctx.session_available} available"
        )

    def on_top_menu(self, checked):
        self.ctx.config.set("always_on_top", checked)
        self.ctx.window_flags_changed.emit()

    def apply_theme(self):
        theme = self.ctx.theme
        app = QApplication.instance()
        app.setStyleSheet(build_stylesheet(theme))
        icon = build_app_icon(theme)
        app.setWindowIcon(icon)
        self.setWindowIcon(icon)
        current = self.ctx.config.get("theme")
        for name, action in self.theme_actions.items():
            action.blockSignals(True)
            action.setChecked(name == current)
            action.blockSignals(False)

    def apply_window_flags(self):
        wanted = self.ctx.config.get("always_on_top")
        self.top_action.blockSignals(True)
        self.top_action.setChecked(wanted)
        self.top_action.blockSignals(False)
        current = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        if current != wanted:
            was_visible = self.isVisible()
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, wanted)
            if was_visible:
                self.show()

    def closeEvent(self, event):
        self.ctx.config.settings.setValue("geometry", self.saveGeometry())
        self.checker.shutdown()
        self.bulk.shutdown()
        self.ctx.flush()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName(ORG_ID)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    setup_logging()
    install_exception_hook()
    log.info("Starting %s v%s %s", APP_NAME, APP_VERSION, APP_STAGE)
    ctx = Context()
    window = MainWindow(ctx)
    window.show()
    code = app.exec()
    log.info("Exited with code %s", code)
    sys.exit(code)


if __name__ == "__main__":
    main()