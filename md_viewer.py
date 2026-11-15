#!/usr/bin/env python3
"""
MD Viewer - A simple Markdown viewer & editor for Fedora
with one-click RTL/LTR switching (full Arabic support).

Usage:
    ./run.sh              # start empty
    ./run.sh file.md      # open a file directly
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from editor_features import WritingTools

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from PySide6.QtCore import QMarginsF, QSettings, QSize, QTimer, Qt, QUrl
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QPainter,
    QPageLayout,
    QPageSize,
    QKeySequence,
    QPalette,
    QTextDocument,
    QTextCursor,
)
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QListView,
    QStyle,
    QStyleOptionComboBox,
    QStylePainter,
    QDockWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QStackedWidget,
    QTextBrowser,
    QToolBar,
)

APP_NAME = "قلم"

HTML_TEMPLATE = """<!DOCTYPE html>
<html dir="{direction}">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Cairo','Noto Sans','Noto Naskh Arabic','DejaVu Sans',sans-serif;
         font-size: 16px; line-height: 1.7; margin: 24px;
         color: {text}; background-color: {page_bg}; }}
  a {{ color: {link}; }}
  code {{ font-family: 'Noto Sans Mono','DejaVu Sans Mono',monospace;
         color: {code_fg}; background-color: {code_bg}; }}
  pre {{ font-family: 'Noto Sans Mono','DejaVu Sans Mono',monospace;
        background-color: {pre_bg}; padding: 8px; }}
  blockquote {{ color: {quote_fg}; }}
  th {{ background-color: {th_bg}; }}
  h1, h2 {{ border-bottom: 1px solid {heading_border}; }}
</style>
</head>
<body>
{content}
</body>
</html>
"""

PDF_HTML_TEMPLATE = """<!DOCTYPE html>
<html dir="{direction}">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Cairo','Noto Sans','Noto Naskh Arabic','DejaVu Sans',sans-serif;
         font-size: 11pt; line-height: 1.45; margin: 0;
         color: #1a1a1a; background-color: #ffffff; }}
  h1 {{ font-size: 22pt; margin: 0 0 14pt; padding-bottom: 5pt;
        border-bottom: 1px solid #d0d0d0; }}
  h2 {{ font-size: 17pt; margin: 18pt 0 10pt; padding-bottom: 4pt;
        border-bottom: 1px solid #d0d0d0; }}
  h3 {{ font-size: 13pt; margin: 14pt 0 8pt; }}
  p {{ margin: 0 0 9pt; }}
  ul, ol {{ margin-top: 0; margin-bottom: 9pt; }}
  a {{ color: #1f5fbf; }}
  code {{ font-family: 'Noto Sans Mono','DejaVu Sans Mono',monospace;
         font-size: 9.5pt; color: #9c2f45; background-color: #f5f5f5; }}
  pre {{ font-family: 'Noto Sans Mono','DejaVu Sans Mono',monospace;
        font-size: 9.5pt; background-color: #f5f5f5; padding: 7pt; }}
  blockquote {{ color: #555555; margin: 0 0 9pt 12pt; }}
  th {{ background-color: #f0f0f0; }}
  table {{ margin: 8pt 0 12pt; }}
</style>
</head>
<body>
{content}
</body>
</html>
"""

THEMES = {
    "Light": {
        "page_bg": "#ffffff", "text": "#1a1a1a", "link": "#2f6fdf",
        "code_fg": "#c7254e", "code_bg": "#f9f2f4", "pre_bg": "#f6f8fa",
        "quote_fg": "#555555", "th_bg": "#f0f0f0", "heading_border": "#cccccc",
        "editor_bg": "#ffffff", "editor_fg": "#1a1a1a",
        "highlight": "#2f6fdf", "highlighted_text": "#ffffff",
        "pygments": "friendly",
    },
    "Dark": {
        "page_bg": "#17231f", "text": "#edf5ef", "link": "#8ccaff",
        "code_fg": "#f1c985", "code_bg": "#263b31", "pre_bg": "#263b31",
        "quote_fg": "#b6cbbf", "th_bg": "#2b4437", "heading_border": "#496254",
        "editor_bg": "#17231f", "editor_fg": "#edf5ef",
        "highlight": "#9ce0bf", "highlighted_text": "#10251b",
        "pygments": "monokai",
    },
    "Sepia": {
        "page_bg": "#f4ecd8", "text": "#5b4636", "link": "#af5f00",
        "code_fg": "#9c3d54", "code_bg": "#eadfc3", "pre_bg": "#eadfc3",
        "quote_fg": "#8a7968", "th_bg": "#e6dabf", "heading_border": "#d3c4a5",
        "editor_bg": "#f4ecd8", "editor_fg": "#5b4636",
        "highlight": "#cb4b16", "highlighted_text": "#ffffff",
        "pygments": "pastie",
    },
}

PDF_THEME = {
    "page_bg": "#ffffff", "text": "#1a1a1a", "link": "#1f5fbf",
    "code_fg": "#9c2f45", "code_bg": "#f5f5f5", "pre_bg": "#f5f5f5",
    "quote_fg": "#555555", "th_bg": "#f0f0f0", "heading_border": "#d0d0d0",
    "pygments": "friendly",
}

# Arabic + Arabic Supplement + Presentation Forms
ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")

ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t[hd][^>]*>.*?</t[hd]>", re.S)
DIV_DIR_RE = re.compile(
    r'\s*<div dir="(?:rtl|ltr)" markdown="block">\s*(.*?)\s*</div>\s*', re.S
)


def looks_arabic(text: str) -> bool:
    """Heuristic: does this text contain Arabic characters?"""
    return bool(ARABIC_RE.search(text[:5000]))


class ThemeComboBox(QComboBox):
    def paintEvent(self, event):
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option)
        icon_rect = self.rect().adjusted(self.width() - 62, 0, -42, 0)
        icon_rect.setTop((self.height() - 20) // 2)
        icon_rect.setHeight(20)
        self.itemIcon(self.currentIndex()).paint(painter, icon_rect)
        painter.setPen(self.palette().color(QPalette.ColorRole.Text))
        painter.drawText(self.rect().adjusted(12, 0, -68, 0), Qt.AlignmentFlag.AlignCenter, self.currentText())


class MainWindow(QMainWindow, WritingTools):
    def __init__(self, draft_dir=None) -> None:
        super().__init__()
        if not getattr(QApplication.instance(), '_qalam_font_loaded', False):
            font_id = QFontDatabase.addApplicationFont(str(Path(__file__).resolve().parent / 'assets/fonts/Cairo.ttf'))
            if font_id >= 0:
                QApplication.instance()._qalam_font_loaded = True
                QApplication.instance().setFont(QFont('Cairo', 10))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "assets/qalam-icon.png")))
        self.current_path: Path | None = None
        self.rtl = False
        self.theme_name = "Light"

        # ---------------- widgets ----------------
        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(True)

        self.editor = QPlainTextEdit()
        font = QFont("Cairo")
        font.setPointSize(12)
        self.editor.setFont(font)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.editor.setTabStopDistance(
            4 * self.editor.fontMetrics().horizontalAdvance(" ")
        )
        self.editor.setPlaceholderText("اكتب Markdown هنا… / Write Markdown here…")

        self.stack = QStackedWidget()
        self.stack.addWidget(self.viewer)
        self.stack.addWidget(self.editor)
        self.setCentralWidget(self.stack)

        # ---------------- actions / toolbar ----------------
        tb = QToolBar("أدوات المستند")
        tb.setIconSize(QSize(22, 22))
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        def add(text, shortcut, slot, checkable=False):
            action = QAction(text, self)
            icons = {"فتح": "document-open", "جديد": "document-new", "حفظ": "document-save", "حفظ باسم": "document-save-as", "تصدير PDF": "document-export", "تحرير": "document-edit", "اتجاه عربي": "format-text-direction-rtl"}
            action.setIcon(QIcon.fromTheme(icons.get(text, "format-text-direction-ltr")))
            action.setToolTip(f"{text} ({shortcut})")
            action.setShortcut(QKeySequence(shortcut))
            action.setCheckable(checkable)
            action.triggered.connect(slot)
            tb.addAction(action)
            self.addAction(action)  # shortcut works even if toolbar is hidden
            return action

        self.home_action = add("الرئيسية", "Alt+Home", self.go_home)
        self.home_action.setIcon(QIcon.fromTheme("go-home"))
        add("فتح", "Ctrl+O", self.open_dialog)
        add("جديد", "Ctrl+N", self.new_file)
        add("حفظ", "Ctrl+S", self.save)
        add("حفظ باسم", "Ctrl+Shift+S", self.save_as)
        add("تصدير PDF", "Ctrl+P", self.export_pdf_dialog)
        tb.addSeparator()
        self.edit_action = add("تحرير", "Ctrl+E", self.toggle_mode, checkable=True)
        self.dir_action = add("اتجاه عربي", "Ctrl+R", self.toggle_direction, checkable=True)
        tb.addSeparator()
        add(
            "تحديد عربي",
            "Ctrl+Shift+R",
            lambda _c=False: self.set_selection_direction(True),
        )
        add(
            "تحديد لاتيني",
            "Ctrl+Shift+L",
            lambda _c=False: self.set_selection_direction(False),
        )

        # editor right-click menu gets the selection-direction actions too
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self._editor_menu)

        tb.addSeparator()
        theme_label = QLabel("  المظهر  ")
        self.theme_combo = ThemeComboBox()
        self.theme_combo.setObjectName("themeSelector")
        self.theme_combo.setMinimumWidth(164)
        theme_list = QListView(self.theme_combo)
        theme_list.setObjectName("themeOptions")
        theme_list.setSpacing(3)
        theme_list.setMouseTracking(True)
        self.theme_combo.setView(theme_list)
        self.theme_combo.addItems(["فاتح", "داكن", "ورقي"])
        self.theme_combo.setIconSize(QSize(20, 20))
        for index, icon_name in enumerate(("theme-light.svg", "theme-dark.svg", "theme-paper.svg")):
            self.theme_combo.setItemIcon(index, QIcon(str(Path(__file__).resolve().parent / "assets" / icon_name)))
        first_action = tb.actions()[0]
        tb.insertWidget(first_action, theme_label)
        tb.insertWidget(first_action, self.theme_combo)
        tb.insertSeparator(first_action)

        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)

        self.editor.document().modificationChanged.connect(self.refresh_title)

        self.preview_dock = QDockWidget("المعاينة المباشرة", self)
        self.preview_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.live_view = QTextBrowser()
        self.live_view.setMinimumWidth(280)
        self.live_view.setOpenExternalLinks(True)
        self.live_view.setDocument(self.viewer.document())
        self.preview_dock.setWidget(self.live_view)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.preview_dock)
        self.preview_dock.hide()
        view_menu = self.menuBar().addMenu("عرض")
        view_menu.addAction(self.home_action)
        live_action = self.preview_dock.toggleViewAction()
        live_action.setText("المعاينة المباشرة")
        live_action.setShortcut(QKeySequence("Ctrl+Shift+P"))
        view_menu.addAction(live_action)
        file_menu = self.menuBar().addMenu("ملف")
        for action in [a for a in tb.actions() if a.text() in ("فتح", "جديد", "حفظ", "حفظ باسم", "تصدير PDF")]:
            file_menu.addAction(action)
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(220)
        self.render_timer.timeout.connect(self.render)
        self.editor.textChanged.connect(lambda: self.render_timer.start())
        self.editor.textChanged.connect(self.update_status)
        self.welcome = self.build_welcome()
        self.stack.addWidget(self.welcome)
        self.resize(1180, 780)
        self.setMinimumSize(780, 560)
        self.set_direction(False)
        self.toggle_mode(False)
        self.refresh_title()

        # restore last used theme
        saved = QSettings("md-viewer", "md-viewer").value("theme", "Light")
        if saved not in THEMES:
            saved = "Light"
        self.theme_combo.setCurrentIndex(list(THEMES).index(saved))
        self.theme_combo.currentIndexChanged.connect(lambda index: self.apply_theme(list(THEMES)[index]))
        self.apply_theme(saved)
        self.stack.setCurrentWidget(self.welcome)
        self.update_status()
        self.setup_writing_tools(draft_dir)

    def build_welcome(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(48, 32, 48, 40)
        layout.addStretch()
        logo = QLabel()
        logo.setPixmap(self.windowIcon().pixmap(112, 112))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        title = QLabel("أفكارك تبدأ بقلم")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        subtitle = QLabel("مساحة هادئة للكتابة بالعربية، وتحرير ملفات Markdown ومعاينتها.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(28)
        cards = QHBoxLayout()
        for text, hint, icon, callback in [
            ("مستند جديد", "Ctrl + N", "document-new", self.new_file),
            ("فتح مستند", "Ctrl + O", "document-open", self.open_dialog),
            ("جرّب قلم", "مثال عربي جاهز", "help-about", self.open_example),
        ]:
            button = QPushButton(f"{text}\n{hint}")
            button.setObjectName("welcomeCard")
            button.setIcon(QIcon.fromTheme(icon))
            button.setIconSize(QSize(28, 28))
            button.setMinimumHeight(108)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(callback)
            cards.addWidget(button)
        layout.addLayout(cards)
        layout.addSpacing(24)
        hint = QLabel("كتابة عربية  •  معاينة مباشرة  •  تصدير PDF")
        hint.setObjectName("subtitle")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        layout.addStretch()
        return page

    def open_example(self):
        if self.maybe_save():
            self.open_path(Path(__file__).parent / "example-ar.md")

    def go_home(self, *_):
        if not self.maybe_save():
            return
        self.clear_draft()
        self.current_path = None
        self.editor.clear()
        self.editor.document().setModified(False)
        self.toggle_mode(False)
        if self.search_dialog is not None:
            self.search_dialog.hide()
        self.stack.setCurrentWidget(self.welcome)
        self.refresh_title()
        self.status_label.setText("الرئيسية")
        self.statusBar().clearMessage()

    # ---------------- file operations ----------------

    def open_dialog(self, *_):
        if not self.maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "فتح مستند Markdown",
            "",
            "Markdown files (*.md *.markdown *.mdown *.txt);;All files (*)",
        )
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.critical(self, APP_NAME, f"تعذّر فتح الملف:\n{exc}")
            return
        self.clear_draft()
        self.current_path = path
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        # Auto RTL when the file looks Arabic; user can override with Ctrl+R.
        self.set_direction(looks_arabic(text))
        self.toggle_mode(False)
        self.refresh_title()
        self.statusBar().showMessage(f"تم فتح: {path}", 3000)

    def new_file(self, *_):
        if not self.maybe_save():
            return
        self.clear_draft()
        self.current_path = None
        self.editor.clear()
        self.editor.document().setModified(False)
        self.set_direction(True)
        self.toggle_mode(True)  # go straight to editing
        self.refresh_title()

    def save(self, *_):
        if self.current_path is None:
            return self.save_as()
        self._write(self.current_path)

    def save_as(self, *_):
        path, _ = QFileDialog.getSaveFileName(
            self, "حفظ المستند", "", "Markdown files (*.md);;All files (*)"
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".md"
        self._write(Path(path))

    def _write(self, path: Path):
        try:
            path.write_text(self.editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, f"تعذّر حفظ الملف:\n{exc}")
            return
        self.current_path = path
        self.clear_draft()
        self.editor.document().setModified(False)
        self.refresh_title()
        self.statusBar().showMessage(f"تم حفظ: {path}", 3000)

    def export_pdf_dialog(self, *_):
        default_path = self._default_pdf_path()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "تصدير PDF",
            str(default_path),
            "PDF files (*.pdf);;All files (*)",
        )
        if not path:
            return
        path_obj = Path(path)
        if not path_obj.suffix:
            path_obj = path_obj.with_suffix(".pdf")
        self.export_pdf(path_obj)

    def _default_pdf_path(self) -> Path:
        if self.current_path is not None:
            return self.current_path.with_suffix(".pdf")
        return Path.home() / "Untitled.pdf"

    def export_pdf(self, path: Path):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(path))
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(
            QMarginsF(16, 16, 16, 16),
            QPageLayout.Unit.Millimeter,
        )

        doc = QTextDocument()
        doc.setDefaultFont(QFont("Cairo", 11))
        if self.current_path is not None and hasattr(doc, "setBaseUrl"):
            doc.setBaseUrl(QUrl.fromLocalFile(str(self.current_path.parent) + "/"))
        doc.setHtml(
            PDF_HTML_TEMPLATE.format(
                direction="rtl" if self.rtl else "ltr",
                content=self._render_body(PDF_THEME),
            )
        )
        doc.setPageSize(printer.pageRect(QPrinter.Unit.Point).size())
        doc.print_(printer)
        if not path.is_file():
            QMessageBox.critical(self, APP_NAME, "تعذّر إنشاء ملف PDF.")
            return
        self.statusBar().showMessage(f"تم تصدير PDF: {path}", 3000)

    def maybe_save(self) -> bool:
        if not self.editor.document().isModified():
            return True
        ret = QMessageBox.warning(
            self,
            APP_NAME,
            "يوجد تعديل لم يتم حفظه.\nهل تريد حفظ التغييرات؟",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if ret == QMessageBox.StandardButton.Save:
            self.save()
            return not self.editor.document().isModified()
        return ret == QMessageBox.StandardButton.Discard

    # ---------------- view / edit / direction ----------------

    def toggle_mode(self, edit: bool = False):
        """Switch between rendered preview and raw-text editing."""
        if hasattr(self, "format_bar"):
            self.format_bar.setVisible(edit)
        if edit:
            self.stack.setCurrentWidget(self.editor)
            self.editor.setFocus()
        else:
            self.render()
            self.stack.setCurrentWidget(self.viewer)
        self.preview_dock.setVisible(edit)
        if edit:
            self.resizeDocks([self.preview_dock], [self.width() // 2], Qt.Orientation.Horizontal)
        self.edit_action.setChecked(edit)
        self.update_status()

    def toggle_direction(self, rtl: bool = False):
        self.set_direction(rtl)

    def set_direction(self, rtl: bool):
        self.rtl = rtl
        qt_dir = (
            Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
        )
        # Editor direction (layout + default paragraph direction)
        self.editor.setLayoutDirection(qt_dir)
        opt = self.editor.document().defaultTextOption()
        opt.setTextDirection(qt_dir)
        self.editor.document().setDefaultTextOption(opt)
        # Viewer direction (scrollbar side; text direction set via HTML dir=)
        self.viewer.setLayoutDirection(qt_dir)
        self.dir_action.setChecked(rtl)
        self.render()
        self.update_status()

    def apply_theme(self, name: str):
        """Apply a color theme to the preview, editor, and code highlighting."""
        if name not in THEMES:
            name = "Light"
        self.theme_name = name
        theme = THEMES[name]
        dark = name == "Dark"
        arrow_icon = (Path(__file__).resolve().parent / "assets" / ("chevron-down-light.svg" if dark else "chevron-down.svg")).as_posix()
        bg = "#101a16" if dark else ("#f4ecd8" if name == "Sepia" else "#f4f7f5")
        surface = "#21332a" if dark else ("#fff8e8" if name == "Sepia" else "#ffffff")
        fg = "#edf5ef" if dark else "#193c32"
        border = "#496254" if dark else "#d9e3dd"
        palette = QPalette(self.style().standardPalette())
        for role, color in (
            (QPalette.ColorRole.Window, bg), (QPalette.ColorRole.WindowText, fg),
            (QPalette.ColorRole.Base, theme['editor_bg']), (QPalette.ColorRole.Text, fg),
            (QPalette.ColorRole.Button, surface), (QPalette.ColorRole.ButtonText, fg),
            (QPalette.ColorRole.Highlight, theme['highlight']),
            (QPalette.ColorRole.HighlightedText, theme['highlighted_text']),
            (QPalette.ColorRole.PlaceholderText, '#a5bbae' if dark else '#62796e'),
        ):
            palette.setColor(role, QColor(color))
        self.setPalette(palette)
        self.setStyleSheet(f"""
            QMainWindow, QMenuBar, QStatusBar {{ background: {bg}; color: {fg}; }}
            QDialog {{ background: {bg}; color: {fg}; }}
            QSpinBox {{ background: {surface}; color: {fg}; border: 1px solid {border}; padding: 6px; border-radius: 6px; }}
            QLineEdit {{ background: {surface}; color: {fg}; border: 1px solid {border}; padding: 8px; selection-background-color: {theme['highlight']}; selection-color: {theme['highlighted_text']}; }}
            QCheckBox {{ color: {fg}; }}
            QPushButton {{ background: {surface}; color: {fg}; border: 1px solid {border}; padding: 8px; border-radius: 5px; }}
            QPushButton:hover {{ border-color: #b79a55; }}
            QWidget {{ font-family: 'Cairo', 'Noto Sans Arabic', 'Noto Sans'; font-size: 13px; }}
            QLabel {{ color: {fg}; background: transparent; }}
            QToolBar {{ background: {surface}; border: 1px solid {border}; padding: 10px; spacing: 5px; }}
            QToolButton {{ color: {fg}; padding: 9px; border-radius: 7px; }}
            QToolButton:hover {{ background: {border}; }}
            QToolButton:checked {{ background: #28664d; color: #ffffff; border: 1px solid #75b99a; }}
            QToolButton:focus {{ border: 1px solid #b79a55; }}
            QMenuBar::item:selected {{ background: {surface}; }}
            QToolTip {{ background: {surface}; color: {fg}; border: 1px solid {border}; padding: 6px; }}
            QScrollBar:vertical {{ background: {bg}; width: 12px; margin: 0; }}
            QScrollBar:horizontal {{ background: {bg}; height: 12px; margin: 0; }}
            QScrollBar::handle {{ background: {border}; border-radius: 5px; min-height: 24px; min-width: 24px; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
            QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
            QComboBox {{ background: {surface}; color: {fg}; padding: 7px; border: 1px solid {border}; border-radius: 6px; }}
            QComboBox#themeSelector {{ padding: 9px 14px 9px 32px; border-radius: 10px; min-height: 22px; }}
            QComboBox#themeSelector:hover, QComboBox#themeSelector:focus {{ border: 1px solid #b79a55; }}
            QComboBox#themeSelector::drop-down {{ subcontrol-origin: padding; subcontrol-position: left center; width: 26px; border: 0; }}
            QComboBox#themeSelector::down-arrow {{ image: url("{arrow_icon}"); width: 16px; height: 16px; }}
            QListView#themeOptions {{ background: {surface}; color: {fg}; border: 1px solid {border}; border-radius: 10px; padding: 6px; outline: 0; }}
            QListView#themeOptions::item {{ min-height: 34px; padding: 4px 14px; border-radius: 7px; }}
            QListView#themeOptions::item:hover {{ background: {border}; color: {fg}; }}
            QListView#themeOptions::item:selected {{ background: #236c53; color: #ffffff; }}
            QMenu {{ background: {surface}; color: {fg}; }}
            QMenu::item:selected {{ background: {border}; }}
            QPlainTextEdit, QTextBrowser {{
                border: 0; padding: 16px;
                background-color: {theme['editor_bg']};
                color: {theme['editor_fg']};
                selection-background-color: {theme['highlight']};
                selection-color: {theme['highlighted_text']};
            }}
            QDockWidget {{ color: {fg}; font-weight: bold; }}
            QDockWidget::title {{ background: {surface}; padding: 12px; }}
            QLabel#welcomeTitle {{ font-size: 36px; font-weight: bold; }}
            QLabel#subtitle {{ color: {('#a8bbb3' if dark else '#62796e')}; font-size: 16px; }}
            QPushButton#welcomeCard {{ background: {surface}; color: {fg}; border: 1px solid {border}; border-radius: 14px; font-size: 17px; padding: 14px; }}
            QPushButton#welcomeCard:hover {{ border: 2px solid #b79a55; background: {bg}; }}
            QPushButton#welcomeCard:focus {{ border: 2px solid #b79a55; }}
            QStatusBar {{ padding: 6px; border-top: 1px solid {border}; }}
        """)
        # Native icon themes may provide black icons even with a dark stylesheet.
        for control in self.findChildren(QAction) + self.findChildren(QPushButton):
            original = control.property('qalamOriginalIcon')
            if original is None:
                original = control.icon()
                control.setProperty('qalamOriginalIcon', original)
            if original.isNull():
                continue
            if dark:
                pixmap = original.pixmap(32, 32)
                painter = QPainter(pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(pixmap.rect(), QColor('#d7eadf'))
                painter.end()
                control.setIcon(QIcon(pixmap))
            else:
                control.setIcon(original)
        for widget, bg, fg in (
            (self.viewer, theme["page_bg"], theme["text"]),
            (self.live_view, theme["page_bg"], theme["text"]),
            (self.editor, theme["editor_bg"], theme["editor_fg"]),
        ):
            pal = widget.palette()
            pal.setColor(QPalette.ColorRole.Base, QColor(bg))
            pal.setColor(QPalette.ColorRole.Text, QColor(fg))
            pal.setColor(QPalette.ColorRole.Highlight, QColor(theme["highlight"]))
            pal.setColor(
                QPalette.ColorRole.HighlightedText,
                QColor(theme["highlighted_text"]),
            )
            widget.setPalette(pal)
        if self.theme_combo.currentIndex() != list(THEMES).index(name):
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(list(THEMES).index(name))
            self.theme_combo.blockSignals(False)
        self.render()
        QSettings("md-viewer", "md-viewer").setValue("theme", name)

    def render(self):
        theme = THEMES[self.theme_name]
        doc = self.viewer.document()
        if self.current_path is not None and hasattr(doc, "setBaseUrl"):
            # so relative images in the markdown resolve correctly
            doc.setBaseUrl(QUrl.fromLocalFile(str(self.current_path.parent) + "/"))
        self.viewer.setHtml(
            HTML_TEMPLATE.format(
                direction="rtl" if self.rtl else "ltr",
                content=self._render_body(theme),
                **theme,
            )
        )

    def _render_body(self, theme: dict[str, str]) -> str:
        body = markdown.markdown(
            self.editor.toPlainText(),
            extensions=[
                "extra",
                "sane_lists",
                # syntax coloring with inline colors (Qt-friendly)
                CodeHiliteExtension(
                    noclasses=True,
                    guess_lang=False,
                    pygments_style=theme["pygments"],
                ),
            ],
        )
        # let the theme control the code background, not the pygments style
        body = re.sub(
            r'(<div class="codehilite")\s+style="background: #[0-9a-fA-F]+"',
            r"\1",
            body,
        )
        # Qt's rich-text engine only draws table borders via the border attribute
        table_tag = '<table border="1" cellspacing="0" cellpadding="6"'
        table_tag += ' align="right">' if self.rtl else ">"
        body = body.replace("<table>", table_tag)
        if self.rtl:
            # Qt ignores table direction: flip column order manually
            body = ROW_RE.sub(self._flip_row, body)
        # code is always LTR, even inside an RTL document
        body = re.sub(r"<pre(?=[\s>])", '<pre dir="ltr"', body)
        return body

    @staticmethod
    def _flip_row(match):
        cells = CELL_RE.findall(match.group(1))
        if not cells:
            return match.group(0)
        return "<tr>" + "".join(reversed(cells)) + "</tr>"

    def set_selection_direction(self, rtl: bool):
        """Wrap the selected text (or current paragraph) in a dir= div."""
        if self.stack.currentWidget() is not self.editor:
            self.toggle_mode(True)
        direction = "rtl" if rtl else "ltr"
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        # Qt uses U+2029 as paragraph separator in selectedText()
        text = cursor.selectedText().replace("\u2029", "\n")
        m = DIV_DIR_RE.fullmatch(text)
        # re-applying to an already-wrapped block swaps its direction (no nesting)
        inner = m.group(1).strip("\n") if m else text.strip("\n")
        cursor.insertText(
            f'<div dir="{direction}" markdown="block">\n\n{inner}\n\n</div>'
        )
        self.editor.setTextCursor(cursor)

    def _editor_menu(self, pos):
        menu = self.editor.createStandardContextMenu()
        menu.addSeparator()
        menu.addAction(
            "اتجاه التحديد عربي\tCtrl+Shift+R",
            lambda: self.set_selection_direction(True),
        )
        menu.addAction(
            "اتجاه التحديد لاتيني\tCtrl+Shift+L",
            lambda: self.set_selection_direction(False),
        )
        menu.exec(self.editor.viewport().mapToGlobal(pos))

    # ---------------- misc ----------------

    def refresh_title(self, *_):
        name = self.current_path.name if self.current_path else "مستند جديد"
        star = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"{star}{name} — {APP_NAME}")

    def update_status(self):
        mode = "تحرير" if self.stack.currentWidget() is self.editor else "معاينة"
        words = len(self.editor.toPlainText().split())
        self.status_label.setText(
            f" {mode}   •   {words} كلمة   •   {'من اليمين إلى اليسار' if self.rtl else 'من اليسار إلى اليمين'} "
        )

    def closeEvent(self, event):
        if self.maybe_save():
            self.clear_draft()
            event.accept()
        else:
            event.ignore()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "qalam-icon.png")))
    app.setDesktopFileName("md-viewer")
    win = MainWindow()
    if len(sys.argv) > 1:
        path = Path(sys.argv[1]).expanduser()
        if path.is_file():
            win.open_path(path)
        else:
            QMessageBox.warning(win, APP_NAME, f"File not found:\n{path}")
    win.show()
    QTimer.singleShot(0, win.offer_recovery)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
