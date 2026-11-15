"""Writing tools and crash-recovery snapshots for Qalam."""
import json
import uuid
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QTimer, Qt, QSaveFile, QIODevice
from PySide6.QtGui import QAction, QKeySequence, QTextCursor, QTextDocument
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                              QPushButton, QLabel, QCheckBox, QToolBar,
                              QFileDialog, QMessageBox)


class WritingTools:
    def setup_writing_tools(self, draft_dir=None):
        self.draft_dir = Path(draft_dir) if draft_dir else Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        ) / 'drafts'
        self.draft_path = self.draft_dir / (uuid.uuid4().hex + '.json')
        self.draft_timer = QTimer(self)
        self.draft_timer.setInterval(2000)
        self.draft_timer.timeout.connect(self.snapshot_draft)
        self.draft_timer.start()
        menu = self.menuBar().addMenu('تحرير')
        for title, shortcut, callback in [
            ('بحث', 'Ctrl+F', self.show_search),
            ('بحث واستبدال', 'Ctrl+H', self.show_search),
            ('استعادة مسودة', '', self.choose_draft),
        ]:
            action = QAction(title, self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            menu.addAction(action)
        self.addToolBarBreak()
        bar = QToolBar('تنسيق Markdown', self)
        bar.setMovable(False)
        self.addToolBar(bar)
        for title, prefix, suffix, shortcut in [
            ('عريض', '**', '**', 'Ctrl+B'), ('مائل', '*', '*', 'Ctrl+I'),
            ('عنوان', '## ', '', ''), ('قائمة', '- ', '', ''),
            ('اقتباس', '> ', '', ''), ('كود', '`', '`', ''),
            ('رابط', '[', '](https://example.com)', ''),
        ]:
            action = QAction(title, self)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(lambda checked=False, p=prefix, s=suffix: self.insert_markdown(p, s))
            bar.addAction(action)
        from table_builder import TablePickerButton
        self.table_button = TablePickerButton(self)
        bar.addWidget(self.table_button)
        self.format_bar = bar
        bar.setVisible(self.stack.currentWidget() is self.editor)
        self.search_dialog = None

    def show_table_dialog(self, *_):
        from table_builder import TableDialog
        dialog = TableDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.insert_markdown(dialog.table_source(), '')

    def insert_markdown(self, prefix, suffix):
        self.toggle_mode(True)
        cursor = self.editor.textCursor()
        selected = cursor.selectedText().replace('\u2029', '\n')
        cursor.beginEditBlock()
        if prefix in ('## ', '- ', '> '):
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            start = cursor.position()
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            selected = cursor.selectedText().replace('\u2029', '\n')
            cursor.insertText('\n'.join(prefix + line if line else prefix for line in selected.split('\n')))
        else:
            cursor.insertText(prefix + (selected or ('نص' if suffix else '')) + suffix)
        cursor.endEditBlock()
        self.editor.setTextCursor(cursor)

    def show_search(self, *_):
        self.toggle_mode(True)
        if self.search_dialog is None:
            dialog = QDialog(self)
            dialog.setWindowTitle('بحث واستبدال')
            dialog.setMinimumWidth(390)
            layout = QVBoxLayout(dialog)
            self.find_input = QLineEdit()
            self.replace_input = QLineEdit()
            self.find_input.setPlaceholderText('النص المطلوب')
            self.replace_input.setPlaceholderText('الاستبدال بـ')
            layout.addWidget(QLabel('بحث'))
            layout.addWidget(self.find_input)
            layout.addWidget(QLabel('استبدال'))
            layout.addWidget(self.replace_input)
            self.case_sensitive = QCheckBox('مطابقة حالة الأحرف')
            layout.addWidget(self.case_sensitive)
            self.search_feedback = QLabel()
            layout.addWidget(self.search_feedback)
            row = QHBoxLayout()
            for title, callback in [('التالي', self.find_next), ('استبدال', self.replace_one), ('استبدال الكل', self.replace_all)]:
                button = QPushButton(title)
                button.clicked.connect(callback)
                row.addWidget(button)
            layout.addLayout(row)
            self.find_input.returnPressed.connect(self.find_next)
            self.search_dialog = dialog
        self.search_dialog.show()
        self.search_dialog.raise_()
        self.find_input.setFocus()

    def search_flags(self):
        return QTextDocument.FindFlag.FindCaseSensitively if self.case_sensitive.isChecked() else QTextDocument.FindFlag(0)

    def find_next(self, *_):
        query = self.find_input.text()
        if not query:
            self.search_feedback.setText('أدخل نصًا للبحث')
            return False
        document = self.editor.document()
        cursor = document.find(query, self.editor.textCursor(), self.search_flags())
        if cursor.isNull():
            cursor = document.find(query, 0, self.search_flags())
        if cursor.isNull():
            self.search_feedback.setText('لا توجد نتائج')
            return False
        self.editor.setTextCursor(cursor)
        self.search_feedback.setText('تم العثور على النص')
        return True

    def replace_one(self, *_):
        query = self.find_input.text()
        if not query:
            return
        cursor = self.editor.textCursor()
        text = cursor.selectedText()
        matches = text == query if self.case_sensitive.isChecked() else text.casefold() == query.casefold()
        if not matches and not self.find_next():
            return
        self.editor.textCursor().insertText(self.replace_input.text())
        self.find_next()

    def replace_all(self, *_):
        query = self.find_input.text()
        if not query:
            self.search_feedback.setText('أدخل نصًا للبحث')
            return
        document = self.editor.document()
        edit = QTextCursor(document)
        edit.beginEditBlock()
        position = 0
        count = 0
        while True:
            cursor = document.find(query, position, self.search_flags())
            if cursor.isNull():
                break
            cursor.insertText(self.replace_input.text())
            position = cursor.position()
            count += 1
        edit.endEditBlock()
        self.search_feedback.setText(f'تم استبدال {count} نتيجة')

    def snapshot_draft(self):
        if not self.editor.document().isModified():
            return
        try:
            self.draft_dir.mkdir(parents=True, exist_ok=True)
            data = json.dumps({'text': self.editor.toPlainText(), 'rtl': self.rtl,
                               'source': str(self.current_path) if self.current_path else None}, ensure_ascii=False).encode()
            output = QSaveFile(str(self.draft_path))
            if not output.open(QIODevice.OpenModeFlag.WriteOnly):
                raise OSError(output.errorString())
            if output.write(data) != len(data) or not output.commit():
                raise OSError(output.errorString())
        except OSError:
            self.statusBar().showMessage('تعذّر حفظ نسخة الاستعادة؛ احفظ المستند يدويًا.', 5000)

    def clear_draft(self):
        if hasattr(self, 'draft_path'):
            try:
                self.draft_path.unlink(missing_ok=True)
            except OSError:
                self.statusBar().showMessage('تعذّر حذف نسخة الاستعادة القديمة.', 5000)

    def choose_draft(self, *_):
        path, _ = QFileDialog.getOpenFileName(self, 'اختر مسودة لاستعادتها', str(self.draft_dir), 'مسودات قلم (*.json)')
        if path and self.maybe_save():
            self.restore_draft(Path(path))

    def restore_draft(self, path):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data.get('text'), str):
                raise ValueError('invalid draft')
        except (OSError, ValueError, AttributeError):
            QMessageBox.warning(self, 'قلم', 'تعذّر قراءة المسودة.')
            return
        self.clear_draft()
        # Restore as an unsaved copy; never overwrite an externally modified source.
        self.current_path = None
        self.editor.setPlainText(data['text'])
        self.editor.document().setModified(True)
        self.set_direction(bool(data.get('rtl', True)))
        self.toggle_mode(True)
        self.snapshot_draft()
        self.refresh_title()

    def offer_recovery(self):
        if self.draft_dir.exists() and any(self.draft_dir.glob('*.json')):
            if QMessageBox.question(self, 'استعادة المسودات', 'توجد مسودات محفوظة. هل تريد اختيار مسودة لاستعادتها؟') == QMessageBox.StandardButton.Yes:
                self.choose_draft()
