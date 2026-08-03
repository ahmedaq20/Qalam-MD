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

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from PySide6.QtCore import QMarginsF, QSettings, Qt, QUrl
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
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
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QStackedWidget,
    QTextBrowser,
    QToolBar,
)

APP_NAME = "MD Viewer"

HTML_TEMPLATE = """<!DOCTYPE html>
<html dir="{direction}">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Noto Sans','Noto Naskh Arabic','DejaVu Sans',sans-serif;
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
  body {{ font-family: 'Noto Sans','Noto Naskh Arabic','DejaVu Sans',sans-serif;
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
        "page_bg": "#1e1e2e", "text": "#e8e8e8", "link": "#89b4fa",
        "code_fg": "#f38ba8", "code_bg": "#313244", "pre_bg": "#313244",
        "quote_fg": "#a6adc8", "th_bg": "#313244", "heading_border": "#45475a",
        "editor_bg": "#1e1e2e", "editor_fg": "#e8e8e8",
        "highlight": "#89b4fa", "highlighted_text": "#1e1e2e",
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.current_path: Path | None = None
        self.rtl = False
        self.theme_name = "Light"

        # ---------------- widgets ----------------
        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(True)

        self.editor = QPlainTextEdit()
        font = QFont("Noto Sans Mono")
        font.setStyleHint(QFont.StyleHint.Monospace)
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
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        def add(text, shortcut, slot, checkable=False):
            action = QAction(text, self)
            action.setShortcut(QKeySequence(shortcut))
            action.setCheckable(checkable)
            action.triggered.connect(slot)
            tb.addAction(action)
            self.addAction(action)  # shortcut works even if toolbar is hidden
            return action

        add("Open…", "Ctrl+O", self.open_dialog)
        add("New", "Ctrl+N", self.new_file)
        add("Save", "Ctrl+S", self.save)
        add("Save As…", "Ctrl+Shift+S", self.save_as)
        add("Download PDF…", "Ctrl+P", self.export_pdf_dialog)
        tb.addSeparator()
        self.edit_action = add("✏ Edit", "Ctrl+E", self.toggle_mode, checkable=True)
        self.dir_action = add("⇄ RTL", "Ctrl+R", self.toggle_direction, checkable=True)
        tb.addSeparator()
        add(
            "Sel RTL",
            "Ctrl+Shift+R",
            lambda _c=False: self.set_selection_direction(True),
        )
        add(
            "Sel LTR",
            "Ctrl+Shift+L",
            lambda _c=False: self.set_selection_direction(False),
        )

        # editor right-click menu gets the selection-direction actions too
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self._editor_menu)

        tb.addSeparator()
        tb.addWidget(QLabel(" Theme: "))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES))
        tb.addWidget(self.theme_combo)

        self.status_label = QLabel()
        self.statusBar().addPermanentWidget(self.status_label)

        self.editor.document().modificationChanged.connect(self.refresh_title)

        self.resize(1000, 700)
        self.set_direction(False)
        self.toggle_mode(False)
        self.refresh_title()

        # restore last used theme
        saved = QSettings("md-viewer", "md-viewer").value("theme", "Light")
        if saved not in THEMES:
            saved = "Light"
        self.theme_combo.setCurrentText(saved)
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        self.apply_theme(saved)

    # ---------------- file operations ----------------

    def open_dialog(self, *_):
        if not self.maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Markdown file",
            "",
            "Markdown files (*.md *.markdown *.mdown *.txt);;All files (*)",
        )
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not open file:\n{exc}")
            return
        self.current_path = path
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        # Auto RTL when the file looks Arabic; user can override with Ctrl+R.
        self.set_direction(looks_arabic(text))
        self.toggle_mode(False)
        self.refresh_title()
        self.statusBar().showMessage(f"Opened: {path}", 3000)

    def new_file(self, *_):
        if not self.maybe_save():
            return
        self.current_path = None
        self.editor.clear()
        self.editor.document().setModified(False)
        self.toggle_mode(True)  # go straight to editing
        self.refresh_title()

    def save(self, *_):
        if self.current_path is None:
            return self.save_as()
        self._write(self.current_path)

    def save_as(self, *_):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Markdown file", "", "Markdown files (*.md);;All files (*)"
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".md"
        self.current_path = Path(path)
        self._write(self.current_path)

    def _write(self, path: Path):
        try:
            path.write_text(self.editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not save file:\n{exc}")
            return
        self.editor.document().setModified(False)
        self.refresh_title()
        self.statusBar().showMessage(f"Saved: {path}", 3000)

    def export_pdf_dialog(self, *_):
        default_path = self._default_pdf_path()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Download PDF",
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
        doc.setDefaultFont(QFont("Noto Sans", 11))
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
            QMessageBox.critical(self, APP_NAME, "Could not create PDF file.")
            return
        self.statusBar().showMessage(f"Downloaded PDF: {path}", 3000)

    def maybe_save(self) -> bool:
        if not self.editor.document().isModified():
            return True
        ret = QMessageBox.warning(
            self,
            APP_NAME,
            "The document has unsaved changes.\nDo you want to save them?",
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
        if edit:
            self.stack.setCurrentWidget(self.editor)
            self.editor.setFocus()
        else:
            self.render()
            self.stack.setCurrentWidget(self.viewer)
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
        for widget, bg, fg in (
            (self.viewer, theme["page_bg"], theme["text"]),
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
        if self.theme_combo.currentText() != name:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText(name)
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
            "Make selection RTL\tCtrl+Shift+R",
            lambda: self.set_selection_direction(True),
        )
        menu.addAction(
            "Make selection LTR\tCtrl+Shift+L",
            lambda: self.set_selection_direction(False),
        )
        menu.exec(self.editor.viewport().mapToGlobal(pos))

    # ---------------- misc ----------------

    def refresh_title(self, *_):
        name = self.current_path.name if self.current_path else "Untitled"
        star = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"{star}{name} — {APP_NAME}")

    def update_status(self):
        mode = "Edit" if self.stack.currentWidget() is self.editor else "Preview"
        self.status_label.setText(
            f" {mode} | {'RTL' if self.rtl else 'LTR'} "
        )

    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    win = MainWindow()
    if len(sys.argv) > 1:
        path = Path(sys.argv[1]).expanduser()
        if path.is_file():
            win.open_path(path)
        else:
            QMessageBox.warning(win, APP_NAME, f"File not found:\n{path}")
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
