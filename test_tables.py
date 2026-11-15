import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication
from md_viewer import MainWindow, THEMES
from table_builder import build_table, TableDialog
app = QApplication([])
with tempfile.TemporaryDirectory() as tmp:
    w = MainWindow(draft_dir=tmp)
    w.new_file()
    for style in ('markdown', 'green', 'striped', 'plain'):
        for header in (False, True):
            for alignment in ('left', 'right', 'center'):
                source = build_table(2, 3, alignment, style, header)
                w.editor.setPlainText(source)
                body = w._render_body(THEMES['Light'])
                assert body.count('<tr>') == 2 + int(header)
                assert body.count('<td ') == 6 or body.count('<td>') == 6
                w.render()
                assert 'نص' in w.viewer.toPlainText()
    w.editor.clear()
    w.insert_markdown(build_table(2, 2, style='green'), '')
    w.editor.undo()
    assert not w.editor.toPlainText()
    w.editor.redo()
    w.export_pdf(Path(tmp) / 'table.pdf')
    assert (Path(tmp) / 'table.pdf').read_bytes().startswith(b'%PDF')
    d = TableDialog(w)
    d.style.setCurrentIndex(1)
    assert '#145c48' in d.table_source()
    d.show(); app.processEvents()
    d.grab().save('/tmp/qalam-table-dialog.png')
print('Table styles, alignment, insertion undo and PDF checks passed')

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from table_builder import quick_table_source
with tempfile.TemporaryDirectory() as tmp:
    window = MainWindow(draft_dir=tmp)
    window.new_file()
    window.show()
    app.processEvents()
    button = window.table_button
    from PySide6.QtGui import QEnterEvent
    from PySide6.QtCore import QPointF
    app.sendEvent(button, QEnterEvent(QPointF(5, 5), QPointF(5, 5), QPointF(button.mapToGlobal(QPoint(5, 5)))))
    QTest.qWait(250)
    assert button.picker.isVisible(), 'Hover should open the picker'
    grid = button.grid
    point = QPoint(grid.width() - grid.margin - 3 * grid.cell + 5,
                   grid.margin + 3 * grid.cell + 5)
    QTest.mouseMove(grid, point)
    assert (grid.columns, grid.rows) == (3, 4)
    button.picker.grab().save('/tmp/qalam-table-picker.png')
    QTest.mouseClick(grid, Qt.MouseButton.LeftButton, pos=point)
    assert not button.picker.isVisible()
    assert window._render_body(THEMES['Light']).count('<tr>') == 4
    window.editor.undo()
    assert window.editor.toPlainText() == ''
    button.open_picker()
    QTest.keyClick(grid, Qt.Key.Key_Escape)
    app.processEvents()
    assert not button.picker.isVisible()
    window.editor.setPlainText(quick_table_source(1, 1))
    assert window._render_body(THEMES['Light']).count('<tr>') == 1
    window.draft_timer.stop()
print('Hover grid, RTL dimensions, insertion, undo and Escape passed')
