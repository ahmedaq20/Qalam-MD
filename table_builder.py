"""Table insertion dialog with a preview of the generated Markdown/HTML."""
import markdown
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QSpinBox,
                              QComboBox, QCheckBox, QTextBrowser, QLabel,
                              QDialogButtonBox)


def build_table(rows, columns, alignment='right', style='markdown', header=True):
    """Rows counts data rows, excluding the optional header."""
    if not 1 <= rows <= 100 or not 1 <= columns <= 12:
        raise ValueError('Table dimensions out of range')
    if alignment not in ('right', 'center', 'left'):
        raise ValueError('Unknown alignment')
    if style not in ('markdown', 'green', 'striped', 'plain'):
        raise ValueError('Unknown style')
    if style == 'markdown' and header:
        separator = {'right': '---:', 'center': ':---:', 'left': ':---'}[alignment]
        lines = ['| ' + ' | '.join(f'عنوان {i+1}' for i in range(columns)) + ' |',
                 '| ' + ' | '.join([separator] * columns) + ' |']
        lines += ['| ' + ' | '.join(['نص'] * columns) + ' |' for _ in range(rows)]
        return '\n\n' + '\n'.join(lines) + '\n\n'
    border = '0' if style == 'plain' else '1'
    lines = [f'<table border="{border}" cellspacing="0" cellpadding="8" width="100%">']
    if header:
        color = '#145c48' if style == 'green' else '#e4e9e6'
        foreground = '#ffffff' if style == 'green' else '#193c32'
        cells = ''.join(f'<th align="{alignment}" bgcolor="{color}" style="color:{foreground}">عنوان {i+1}</th>' for i in range(columns))
        lines.append('<tr>' + cells + '</tr>')
    for row in range(rows):
        color = '#edf4ef' if style == 'striped' and row % 2 == 0 else '#ffffff'
        cells = ''.join(f'<td align="{alignment}" bgcolor="{color}" style="color:#193c32">نص</td>' for _ in range(columns))
        lines.append('<tr>' + cells + '</tr>')
    lines.append('</table>')
    return '\n\n' + '\n'.join(lines) + '\n\n'


class TableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('إدراج جدول')
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.resize(620, 540)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.rows = QSpinBox()
        self.rows.setRange(1, 100)
        self.rows.setValue(3)
        self.columns = QSpinBox()
        self.columns.setRange(1, 12)
        self.columns.setValue(3)
        self.alignment = QComboBox()
        for label, value in [('يمين', 'right'), ('وسط', 'center'), ('يسار', 'left')]:
            self.alignment.addItem(label, value)
        self.style = QComboBox()
        for label, value in [('بسيط — Markdown', 'markdown'), ('ترويسة خضراء', 'green'), ('صفوف متناوبة', 'striped'), ('بدون حدود', 'plain')]:
            self.style.addItem(label, value)
        self.header = QCheckBox('إضافة صف عناوين')
        self.header.setChecked(True)
        form.addRow('صفوف البيانات', self.rows)
        form.addRow('الأعمدة', self.columns)
        form.addRow('محاذاة النص', self.alignment)
        form.addRow('شكل الجدول', self.style)
        form.addRow(self.header)
        layout.addLayout(form)
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        layout.addWidget(QLabel('معاينة الجدول'))
        self.preview = QTextBrowser()
        layout.addWidget(self.preview, 1)
        buttons = QDialogButtonBox()
        buttons.addButton('إدراج الجدول', QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton('إلغاء', QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.rows.valueChanged.connect(self.update_preview)
        self.columns.valueChanged.connect(self.update_preview)
        self.alignment.currentIndexChanged.connect(self.update_preview)
        self.style.currentIndexChanged.connect(self.update_preview)
        self.header.toggled.connect(self.update_preview)
        self.update_preview()

    def table_source(self):
        return build_table(self.rows.value(), self.columns.value(),
                           self.alignment.currentData(), self.style.currentData(), self.header.isChecked())

    def update_preview(self, *_):
        source = self.table_source()
        html = markdown.markdown(source, extensions=['tables'])
        html = html.replace('<table>', '<table border="1" cellspacing="0" cellpadding="8" width="100%">')
        # Match the app's RTL table column order.
        from md_viewer import ROW_RE, MainWindow
        if self.parent() is not None and self.parent().rtl:
            html = ROW_RE.sub(MainWindow._flip_row, html)
        self.preview.setHtml(html)
        is_markdown = self.style.currentData() == 'markdown' and self.header.isChecked()
        self.note.setText('جدول Markdown قابل للتحرير. عدد الصفوف لا يشمل صف العناوين.' if is_markdown else
                          'سيُدرج الجدول بصيغة HTML داخل المستند للحفاظ على الشكل؛ يمكنك تعديل نصوص الخلايا من المحرر.')


# Quick insertion follows Word's grid: dimensions include the heading row.
from PySide6.QtCore import Signal, QSize, QTimer, QPoint
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QWidget, QWidgetAction, QMenu, QToolButton


class TableGrid(QWidget):
    chosen = Signal(int, int)
    dimensionsChanged = Signal(int, int)
    columns_limit = 10
    rows_limit = 8
    cell = 28
    margin = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.colors = ("#d5e2db", "#eff5f1", "#16775a", "#bda66d")
        self.columns = self.rows = 0
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('حجم الجدول؛ استخدم الأسهم ثم Enter للإدراج')
        self.setFixedSize(self.columns_limit * self.cell + self.margin * 2,
                          self.rows_limit * self.cell + self.margin * 2)

    def select_size(self, columns, rows):
        self.columns, self.rows = columns, rows
        self.dimensionsChanged.emit(columns, rows)
        self.update()

    def mouseMoveEvent(self, event):
        x = self.width() - self.margin - 1 - int(event.position().x())
        y = int(event.position().y()) - self.margin
        if 0 <= x < self.columns_limit * self.cell and 0 <= y < self.rows_limit * self.cell:
            self.select_size(x // self.cell + 1, y // self.cell + 1)
        else:
            self.select_size(0, 0)

    def leaveEvent(self, event):
        self.select_size(0, 0)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        self.mouseMoveEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.columns and self.rows:
            self.chosen.emit(self.columns, self.rows)

    def keyPressEvent(self, event):
        key = event.key()
        columns, rows = self.columns or 1, self.rows or 1
        if key == Qt.Key.Key_Left:
            columns = min(self.columns_limit, columns + 1)
        elif key == Qt.Key.Key_Right:
            columns = max(1, columns - 1)
        elif key == Qt.Key.Key_Down:
            rows = min(self.rows_limit, rows + 1)
        elif key == Qt.Key.Key_Up:
            rows = max(1, rows - 1)
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.chosen.emit(columns, rows)
            return
        else:
            super().keyPressEvent(event)
            return
        self.select_size(columns, rows)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for row in range(self.rows_limit):
            for column in range(self.columns_limit):
                active = column < self.columns and row < self.rows
                painter.setPen(QColor(self.colors[3] if active else self.colors[0]))
                painter.setBrush(QColor(self.colors[2] if active else self.colors[1]))
                x = self.width() - self.margin - (column + 1) * self.cell
                painter.drawRoundedRect(x, self.margin + row * self.cell,
                                        self.cell - 5, self.cell - 5, 5, 5)


def quick_table_source(columns, rows):
    if rows == 1:
        # Python-Markdown synthesizes an empty data row; use HTML for exactly one row.
        cells = ''.join(f'<th align="right">عنوان {i+1}</th>' for i in range(columns))
        return '\n\n<table border="1" cellspacing="0" cellpadding="6"><tr>' + cells + '</tr></table>\n\n'
    return build_table(rows - 1, columns)


class TablePickerButton(QToolButton):
    def __init__(self, owner):
        super().__init__(owner)
        self.setText('جدول ▾')
        self.setToolTip('مرّر المؤشر أو اضغط لاختيار حجم الجدول')
        self.setAccessibleName('إدراج جدول')
        self.owner = owner
        self.picker = QMenu(self)
        panel = QWidget()
        panel.setObjectName("tablePickerPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)
        from PySide6.QtWidgets import QHBoxLayout
        heading = QHBoxLayout()
        title = QLabel('إدراج جدول')
        title.setObjectName('pickerTitle')
        self.badge = QLabel('10 × 8')
        self.badge.setObjectName('pickerBadge')
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.badge)
        layout.addLayout(heading)
        self.label = QLabel('حرّك المؤشر لتحديد الحجم')
        self.label.setObjectName('pickerSubtitle')
        layout.addWidget(self.label)
        self.grid = TableGrid()
        layout.addWidget(self.grid)
        hint = QLabel('يشمل صف العناوين  ·  اضغط للإدراج')
        hint.setObjectName('pickerHint')
        layout.addWidget(hint)
        action = QWidgetAction(self.picker)
        action.setDefaultWidget(panel)
        self.picker.addAction(action)
        self.picker.addSeparator()
        advanced = self.picker.addAction('خيارات متقدمة…')
        advanced.triggered.connect(lambda: QTimer.singleShot(0, owner.show_table_dialog))
        self.grid.dimensionsChanged.connect(self.update_label)
        self.grid.chosen.connect(self.insert_table)
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(180)
        self.hover_timer.timeout.connect(self.open_picker)
        self.clicked.connect(self.open_picker)

    def update_label(self, columns, rows):
        self.label.setText(f'{columns} أعمدة × {rows} صفوف' if columns else 'حرّك المؤشر لتحديد الحجم')
        self.badge.setText(f'{columns} × {rows}' if columns else '10 × 8')

    def style_picker(self):
        theme = self.owner.theme_name
        dark = theme == 'Dark'
        paper = theme == 'Sepia'
        surface = '#22312c' if dark else ('#fff9ed' if paper else '#ffffff')
        text = '#edf5ef' if dark else '#183f32'
        muted = '#adc2b5' if dark else '#6b8074'
        border = '#40574a' if dark else ('#e1d6bd' if paper else '#dce7df')
        soft = '#2d4639' if dark else ('#f3ead5' if paper else '#edf5ef')
        self.grid.colors = (border, soft, '#36a17c' if dark else '#16775a', '#bda66d')
        self.picker.setStyleSheet(f"""
            QMenu {{ background: {surface}; color: {text}; border: 1px solid {border}; border-radius: 14px; padding: 6px; }}
            QWidget#tablePickerPanel {{ background: transparent; }}
            QLabel {{ color: {text}; background: transparent; }}
            QLabel#pickerTitle {{ font-size: 17px; font-weight: bold; }}
            QLabel#pickerSubtitle {{ color: {muted}; font-size: 13px; }}
            QLabel#pickerHint {{ color: {muted}; font-size: 11px; padding-top: 4px; }}
            QLabel#pickerBadge {{ background: {soft}; color: {text}; border-radius: 9px; padding: 5px 11px; font-size: 13px; font-weight: bold; min-width: 48px; }}
            QMenu::separator {{ height: 1px; background: {border}; margin: 5px 16px; }}
            QMenu::item {{ padding: 12px 18px; margin: 3px 8px; border-radius: 8px; }}
            QMenu::item:selected {{ background: {soft}; color: {text}; }}
        """)

    def enterEvent(self, event):
        self.hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_timer.stop()
        super().leaveEvent(event)

    def hideEvent(self, event):
        self.hover_timer.stop()
        self.picker.hide()
        super().hideEvent(event)

    def open_picker(self):
        if self.picker.isVisible() or not self.isVisible():
            return
        self.style_picker()
        self.grid.select_size(0, 0)
        width = self.picker.sizeHint().width()
        self.picker.popup(self.mapToGlobal(QPoint(self.width() - width, self.height())))
        self.grid.setFocus()

    def insert_table(self, columns, rows):
        self.picker.close()
        self.owner.insert_markdown(quick_table_source(columns, rows), '')
