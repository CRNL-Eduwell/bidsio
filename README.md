# bidsio

<p align="center">
  <img src="https://raw.githubusercontent.com/CRNL-Eduwell/bidsio/master/src/bidsio/ui/resources/icon.png" alt="bidsio icon" width="128" height="128">
</p>

A Python desktop application for exploring, filtering, and exporting BIDS (Brain Imaging Data Structure) datasets.

## Overview

bidsio provides a graphical interface for:

- **Loading and indexing** BIDS-compliant neuroimaging datasets
- **Browsing and inspecting** dataset contents (subjects, sessions, runs, files)
- **Filtering** data by various criteria (subject IDs, sessions, tasks, modalities)
- **Exporting** subsets of datasets based on selections

## Requirements

- Python 3.13.7
- PySide6 (Qt6 for Python)
- See `requirements.txt` for full dependency list

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### GUI Application

Run the graphical interface:

```bash
python src/bidsio/ui/app.py
```

Or use the VS Code debugger with the "Run GUI" configuration.

### CLI (Optional)

```bash
python src/bidsio/cli/main.py --help
```

## Development

### Project Structure

```
src/bidsio/
├── config/          # Application configuration and settings
├── core/            # Pure domain logic (GUI-agnostic)
├── infrastructure/  # I/O, BIDS loading, filesystem, logging
├── ui/              # PySide6 GUI layer
│   └── forms/       # Qt Designer .ui files and generated Python modules
└── cli/             # Optional command-line interface
```

### Architecture Principles

- **Strict separation** between domain logic (`core/`) and UI (`ui/`)
- `core/` and `infrastructure/` modules are GUI-agnostic and independently testable
- UI layouts defined in Qt Designer `.ui` files, not hard-coded in Python
- Type hints and comprehensive docstrings throughout

### UI Development Workflow

1. **Design UI** in Qt Designer and save `.ui` files in `src/bidsio/ui/forms/`
2. **Compile `.ui` files** to Python modules:
   - **Option A**: Run `python scripts/generate_ui.py` (auto-detects all `.ui` files)
   - **Option B**: Right-click the `.ui` file in VS Code → "Compile Qt UI file" (requires Qt extension)
   - **Option C**: Run `pyside6-uic <file>.ui -o <file>_ui.py` manually
   - Generated files are named `<original_name>_ui.py` (e.g., `main_window.ui` → `main_window_ui.py`)
3. **Import and use** the generated UI classes in your Python code:
   ```python
   from bidsio.ui.forms.main_window_ui import Ui_MainWindow
   
   class MainWindow(QMainWindow):
       def __init__(self):
           super().__init__()
           self.ui = Ui_MainWindow()
           self.ui.setupUi(self)
   ```

**Note:** Recompile UI files after modifying `.ui` files in Qt Designer. When debugging, UI files are automatically compiled via the preLaunchTask.

### Resources Management

Icons and other resources are managed using Qt's resource system:

1. **Add resources** to `src/bidsio/ui/resources/resources.qrc` file
2. **Compile resources** (automated with UI generation):
   ```bash
   python scripts/generate_ui.py  # Compiles both UI files and resources
   ```
   Or manually:
   ```bash
   pyside6-rcc src/bidsio/ui/resources/resources.qrc -o src/bidsio/ui/resources/resources_rc.py
   ```
3. **Import resources** in your application:
   ```python
   import bidsio.ui.resources.resources_rc  # Registers resources
   ```
4. **Use resources** with the `:/` prefix:
   ```python
   QIcon(":/icon.png")
   ```

**Note:** The `generate_ui.py` script automatically compiles resources and fixes imports when debugging.

### Testing

Run tests with pytest:

```bash
pytest
```

## TODO

This project is in early bootstrap phase. Many modules contain skeleton implementations with detailed TODOs.

See individual module files for specific implementation tasks.

## License

TODO: Add license information
