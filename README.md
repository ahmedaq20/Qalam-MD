# Qalam MD

## English

Qalam MD is a simple Markdown viewer and editor built with Python and PySide6/Qt. It is designed for Arabic and bilingual writing, with easy RTL/LTR switching, Arabic text detection, live Markdown preview, theme support, and PDF export.

Qalam MD can run on Linux, Windows, and macOS as long as Python and the required Python packages are installed. The included `run.sh` and `.desktop` launcher are intended for Linux desktop environments.

### Supported Operating Systems

- Linux, including Fedora, Ubuntu, Debian, Arch, and other desktop distributions
- Windows 10 and newer
- macOS

### Requirements

- Python 3.10 or newer
- PySide6
- Markdown
- Pygments

### Install and Run on Linux

```bash
git clone git@github.com:ahmedaq20/Qalam-MD.git
cd Qalam-MD
python3 -m venv .venv
source .venv/bin/activate
pip install PySide6 Markdown Pygments
./run.sh
```

Open a Markdown file directly:

```bash
./run.sh example-ar.md
```

If `run.sh` is not executable:

```bash
chmod +x run.sh
```

### Install and Run on Windows

```powershell
git clone git@github.com:ahmedaq20/Qalam-MD.git
cd Qalam-MD
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install PySide6 Markdown Pygments
python md_viewer.py
```

Open a Markdown file directly:

```powershell
python md_viewer.py example-ar.md
```

### Install and Run on macOS

```bash
git clone git@github.com:ahmedaq20/Qalam-MD.git
cd Qalam-MD
python3 -m venv .venv
source .venv/bin/activate
pip install PySide6 Markdown Pygments
python3 md_viewer.py
```

Open a Markdown file directly:

```bash
python3 md_viewer.py example-ar.md
```

### Features

- Open, edit, and save Markdown files
- Preview rendered Markdown
- Switch the whole document between RTL and LTR
- Apply RTL or LTR direction to selected text blocks
- Automatic Arabic text detection
- Light, dark, and sepia themes
- Export rendered Markdown to PDF

## العربية

Qalam MD هو تطبيق بسيط لعرض وتحرير ملفات Markdown، مبني باستخدام Python و PySide6/Qt. صمم التطبيق للكتابة العربية والمحتوى ثنائي اللغة، مع دعم سهل للتبديل بين اتجاهي RTL و LTR، واكتشاف النص العربي، ومعاينة Markdown، ودعم السمات، وتصدير الملفات إلى PDF.

يمكن تشغيل Qalam MD على Linux و Windows و macOS عند تثبيت Python والحزم المطلوبة. ملفات `run.sh` و `.desktop` الموجودة في المشروع مخصصة لبيئات سطح مكتب Linux.

### أنظمة التشغيل المدعومة

- Linux، مثل Fedora و Ubuntu و Debian و Arch وغيرها من توزيعات سطح المكتب
- Windows 10 والإصدارات الأحدث
- macOS

### المتطلبات

- Python 3.10 أو أحدث
- PySide6
- Markdown
- Pygments

### التثبيت والتشغيل على Linux

```bash
git clone git@github.com:ahmedaq20/Qalam-MD.git
cd Qalam-MD
python3 -m venv .venv
source .venv/bin/activate
pip install PySide6 Markdown Pygments
./run.sh
```

فتح ملف Markdown مباشرة:

```bash
./run.sh example-ar.md
```

إذا لم يكن ملف `run.sh` قابلا للتشغيل:

```bash
chmod +x run.sh
```

### التثبيت والتشغيل على Windows

```powershell
git clone git@github.com:ahmedaq20/Qalam-MD.git
cd Qalam-MD
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install PySide6 Markdown Pygments
python md_viewer.py
```

فتح ملف Markdown مباشرة:

```powershell
python md_viewer.py example-ar.md
```

### التثبيت والتشغيل على macOS

```bash
git clone git@github.com:ahmedaq20/Qalam-MD.git
cd Qalam-MD
python3 -m venv .venv
source .venv/bin/activate
pip install PySide6 Markdown Pygments
python3 md_viewer.py
```

فتح ملف Markdown مباشرة:

```bash
python3 md_viewer.py example-ar.md
```

### المميزات

- فتح وتحرير وحفظ ملفات Markdown
- معاينة Markdown بعد تحويله
- تبديل اتجاه المستند بالكامل بين RTL و LTR
- تطبيق اتجاه RTL أو LTR على جزء محدد من النص
- اكتشاف النص العربي تلقائيا
- سمات فاتحة وداكنة وبنية
- تصدير Markdown المعروض إلى PDF

## تحديث الواجهة العربية

أصبح اسم التطبيق **قلم**، مع شاشة ترحيب ومعاينة مباشرة بجانب المحرر وعداد كلمات ومظاهر فاتح وداكن وورقي. راجع [سجل التغييرات](CHANGELOG.md) للتفاصيل والاختصارات.

من قائمة **عرض** يمكن إظهار أو إخفاء المعاينة المباشرة، أو استخدام `Ctrl+Shift+P`. تُحفظ السمة المختارة للتشغيل التالي.

### اختصار Linux

يتضمن المشروع `md-viewer.desktop` والأيقونة `assets/qalam-icon.png`. قبل تثبيت الاختصار على جهاز آخر، عدّل حقلي `Exec` و`Icon` في ملف الاختصار إلى المسارات المطلقة لمجلد المشروع على جهازك. اجعل `run.sh` قابلاً للتنفيذ وثبّت المتطلبات أولاً.

انسخ الاختصار إلى `~/.local/share/applications/` ليظهر «قلم» في قائمة التطبيقات. يمكن نسخه أيضًا إلى سطح المكتب وجعله قابلاً للتنفيذ. قد يطلب Dolphin تأكيد **Launch** عند فتح ملف الاختصار مباشرة.

### التحقق من التعديلات

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python smoke_test.py
```
