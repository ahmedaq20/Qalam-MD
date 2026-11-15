"""Regression checks for editing and recovery, isolated from personal drafts."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextCursor
from md_viewer import MainWindow

app = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    w = MainWindow(draft_dir=directory)
    w.new_file()
    w.editor.insertPlainText('مرحبا مرحبا')
    w.snapshot_draft()
    snapshot = w.draft_path
    assert snapshot.is_file()
    recovered = MainWindow(draft_dir=directory)
    recovered.restore_draft(snapshot)
    assert recovered.editor.toPlainText() == 'مرحبا مرحبا'
    assert recovered.editor.document().isModified()
    assert recovered.current_path is None
    assert recovered.rtl
    assert snapshot.exists(), 'Recovery must preserve the original backup'
    target = Path(directory) / 'saved.md'
    recovered._write(target)
    assert not recovered.draft_path.exists()
    assert target.read_text() == 'مرحبا مرحبا'
    w.show_search()
    w.find_input.setText('مرحبا')
    assert w.find_next()
    w.replace_input.setText('مرحبا بكم')
    w.replace_all()
    assert w.editor.toPlainText() == 'مرحبا بكم مرحبا بكم'
    w.editor.undo()
    assert w.editor.toPlainText() == 'مرحبا مرحبا'
    w.replace_input.setText('')
    w.replace_all()
    assert w.editor.toPlainText() == ' '
    w.editor.undo()
    w.find_input.setText('غير موجود')
    assert not w.find_next()
    w.editor.selectAll()
    w.insert_markdown('**', '**')
    assert w.editor.toPlainText() == '**مرحبا مرحبا**'
    w.editor.undo()
    assert w.editor.toPlainText() == 'مرحبا مرحبا'
    w.clear_draft()
    assert not snapshot.exists()
    w.draft_timer.stop()
    recovered.draft_timer.stop()
    w.show(); app.processEvents()
    w.grab().save('/tmp/qalam-writing-tools.png')
print('Writing tools and draft recovery checks passed')

# Returning home must honor cancel/save and hide editing tools.
from unittest.mock import patch
from PySide6.QtWidgets import QMessageBox
with tempfile.TemporaryDirectory() as directory:
    home = MainWindow(draft_dir=directory)
    home.new_file()
    home.editor.insertPlainText('نص مهم')
    with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Cancel):
        home.go_home()
    assert home.editor.toPlainText() == 'نص مهم'
    assert home.stack.currentWidget() is home.editor
    home.current_path = Path(directory) / 'home.md'
    with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Save):
        home.go_home()
    assert (Path(directory) / 'home.md').read_text() == 'نص مهم'
    assert home.stack.currentWidget() is home.welcome
    assert home.format_bar.isHidden() and home.preview_dock.isHidden()
    assert home.current_path is None
    home.draft_timer.stop()
print('Home navigation, cancel and save checks passed')
