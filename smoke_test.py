#!/usr/bin/env python3
"""Headless smoke test for MD Viewer (run with the project venv)."""

import os
import re
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtGui import QPalette, QTextCursor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from md_viewer import THEMES, MainWindow, looks_arabic  # noqa: E402

app = QApplication([])
w = MainWindow()
sample = Path(__file__).parent / "example-ar.md"

# 1. Open Arabic file -> should auto-switch to RTL
w.open_path(sample)
assert w.current_path == sample, "file path not set"
assert w.rtl is True, "Arabic file should auto-switch to RTL"
assert looks_arabic(sample.read_text(encoding="utf-8"))
assert not looks_arabic("plain english text")

# 2. Preview rendered RTL (Qt re-serializes <html dir> into per-block dir='rtl')
assert "dir='rtl'" in w.viewer.toHtml(), "preview not RTL"
assert "مرحبًا" in w.viewer.toPlainText(), "Arabic content missing from preview"

# 2b. Tables get visible borders + fenced code gets syntax colors
html = w.viewer.toHtml()
assert "<table" in html and "border" in html, "table borders missing"
assert re.search(r"color:\s*#", html), "syntax colors missing"

# 2c. RTL mode: table columns flipped + code blocks forced LTR
assert html.index("الاختصار") < html.index("الزر"), "table columns not flipped in RTL"
pre_sec = html[html.find("<pre"):html.find("</pre>")]
assert "dir='rtl'" in html and "dir='rtl'" not in pre_sec, "code block not forced LTR"

# 3. Switch to edit mode and back
w.toggle_mode(True)
assert w.stack.currentWidget() is w.editor
w.toggle_mode(False)
assert w.stack.currentWidget() is w.viewer

# 4. Switch direction to LTR (Qt omits dir attr for default LTR blocks)
w.set_direction(False)
ltr_html = w.viewer.toHtml()
assert "dir='rtl'" not in ltr_html.replace("dir='ltr'", ""), "preview still RTL after toggle"
assert ltr_html.index("الزر") < ltr_html.index("الاختصار"), "LTR table order wrong"
w.set_direction(True)

# 5. Edit + save roundtrip
w.toggle_mode(True)
w.editor.setPlainText("# اختبار حفظ\n\nنص عربي للتجربة.\n")
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "out.md"
    w.current_path = out
    w.save()
    assert out.read_text(encoding="utf-8") == "# اختبار حفظ\n\nنص عربي للتجربة.\n"
    assert not w.editor.document().isModified(), "modified flag not cleared"

# 5b. Export rendered Markdown to PDF
with tempfile.TemporaryDirectory() as tmp:
    pdf = Path(tmp) / "out.pdf"
    w.export_pdf(pdf)
    assert pdf.is_file(), "PDF file was not created"
    assert pdf.stat().st_size > 0, "PDF file is empty"
    assert pdf.read_bytes().startswith(b"%PDF"), "exported file is not a PDF"

# 6. Selection direction wrapping (and re-applying without nesting)
w.editor.setPlainText("فقرة عربية للتجربة.\n\nسطر ثانٍ.\n")
c = w.editor.textCursor()
c.movePosition(QTextCursor.MoveOperation.Start)
c.movePosition(
    QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor
)
w.editor.setTextCursor(c)
w.set_selection_direction(True)
txt = w.editor.toPlainText()
assert '<div dir="rtl" markdown="block">' in txt, "selection not wrapped RTL"
start = txt.find('<div dir="rtl"')
end = txt.find("</div>", start) + len("</div>")
c = w.editor.textCursor()
c.setPosition(start)
c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
w.editor.setTextCursor(c)
w.set_selection_direction(False)
txt = w.editor.toPlainText()
assert txt.count("<div") == 1 and 'dir="ltr"' in txt, "re-wrap created nesting"
assert "فقرة عربية للتجربة." in txt

# 7. Themes recolor preview + editor + code highlighting
w.open_path(sample)  # reload content (has table + code)
for name, theme in THEMES.items():
    w.apply_theme(name)
    assert w.theme_name == name
    assert w.viewer.palette().color(QPalette.ColorRole.Base).name() == theme["page_bg"]
    assert w.editor.palette().color(QPalette.ColorRole.Base).name() == theme["editor_bg"]
    assert theme["page_bg"] in w.viewer.toHtml().lower(), f"{name} bg not in preview"
    assert re.search(r"color:\s*#", w.viewer.toHtml()), f"{name}: no code colors"
w.apply_theme("Light")
assert w.theme_combo.currentText() == "فاتح"

print("SMOKE TEST: all checks passed ✔")

# Welcome actions and debounced live preview.
from PySide6.QtTest import QTest
fresh = MainWindow()
assert fresh.stack.currentWidget() is fresh.welcome
fresh.new_file()
assert fresh.rtl and fresh.stack.currentWidget() is fresh.editor
fresh.editor.setPlainText('# معاينة حية\n\nنص جديد')
QTest.qWait(350)
assert 'معاينة حية' in fresh.live_view.toPlainText()
assert '5 كلمة' in fresh.status_label.text()
print('Arabic welcome and live preview checks passed')
