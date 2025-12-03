# GitHub Copilot Instructions for BIDSIO

You are assisting in developing **BIDSIO**, a Python desktop application for exploring, filtering, and exporting BIDS (Brain Imaging Data Structure) datasets.

## Project Overview

**BIDSIO** is a neuroimaging dataset management tool that provides:
- Loading and indexing of BIDS-compliant datasets
- Browsing and inspecting dataset contents (subjects, sessions, runs, files)
- Filtering data by various criteria (subject IDs, sessions, tasks, modalities)
- Exporting subsets of datasets based on user selections
- Both GUI and CLI interfaces

## Tech Stack

- **Python Version**: 3.13.7 (strictly enforced)
- **GUI Framework**: PySide6 (Qt6 for Python)
- **UI Design**: Qt Designer `.ui` files for all static interfaces
- **BIDS Libraries**: pybids, nibabel (with abstraction layer)
- **Data Validation**: Pydantic for models
- **Testing**: pytest with pytest-qt for GUI tests
- **Environment**: Standard `venv` + `requirements.txt` (no Poetry/Conda)

## Architecture Principles

### 🚨 Critical Rules

1. **Language: English Only**
   - **ALL code, comments, docstrings, variable names, and documentation MUST be in English**
   - This applies even if user prompts are in French or other languages
   - Respond to the user in their language, but generate all code artifacts in English
   - Examples: use `subject_id` not `id_sujet`, `load_dataset()` not `charger_dataset()`

2. **Strict Separation of Concerns**
   - **NEVER import PySide6, Qt, or any GUI framework in `core/` or `infrastructure/`**
   - These modules must remain GUI-agnostic and independently testable
   - All business logic belongs in `core/`, not in UI classes

3. **UI Design Workflow**
   - All static UI layouts MUST be defined in Qt Designer `.ui` files
   - Place `.ui` files in `src/bidsio/ui/ui_files/`
   - Load `.ui` files using `QUiLoader` or `uic.loadUi`
   - Only create widgets programmatically if they are truly dynamic
   - Keep GUI classes thin - they should wire up view models, not implement logic

4. **Domain Logic First**
   - Core business logic must work without any UI
   - Use typed dataclasses or Pydantic models for data
   - All operations should be testable in isolation

## Project Structure

```
.
├── .github/
│   └── copilot-instructions.md   # This file
├── .vscode/
│   ├── launch.json               # Debug configurations
│   └── settings.json             # Python interpreter, testing
├── src/
│   └── bidsio/
│       ├── __init__.py
│       ├── config/               # Application settings
│       │   ├── __init__.py
│       │   └── settings.py
│       ├── core/                 # Pure domain logic (NO GUI imports!)
│       │   ├── __init__.py
│       │   ├── models.py         # Data models (BIDSDataset, FilterCriteria, etc.)
│       │   ├── repository.py    # BidsRepository pattern
│       │   ├── filters.py       # Filtering operations
│       │   └── export.py        # Export functionality
│       ├── infrastructure/       # I/O, filesystem, external systems (NO GUI!)
│       │   ├── __init__.py
│       │   ├── bids_loader.py   # BIDS dataset loading from filesystem
│       │   ├── logging_config.py # Logging setup
│       │   └── paths.py         # Path utilities
│       ├── ui/                   # GUI layer (PySide6 only here)
│       │   ├── __init__.py
│       │   ├── app.py           # Application entry point
│       │   ├── main_window.py   # Main window controller
│       │   ├── view_models.py   # Qt models for views
│       │   ├── widgets/         # Custom widgets
│       │   │   └── __init__.py
│       │   └── ui_files/        # Qt Designer .ui files
│       │       └── main_window.ui
│       └── cli/                  # Command-line interface
│           ├── __init__.py
│           └── main.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_core_models.py
│   └── test_filters.py
├── .gitignore
├── README.md
├── requirements.txt
└── pyproject.toml
```

## Module Responsibilities

### `core/` - Domain Logic
**Purpose**: Pure business logic, data models, operations  
**Dependencies**: Python standard library, pydantic, typing  
**Forbidden**: Any GUI imports (PySide6, Qt)

- `models.py`: Dataclasses for BIDS entities (BIDSFile, BIDSRun, BIDSSession, BIDSSubject, BIDSDataset, FilterCriteria, ExportRequest)
- `repository.py`: Repository pattern for dataset access
- `filters.py`: Functions for filtering datasets by criteria
- `export.py`: Logic for exporting dataset subsets

### `infrastructure/` - External Systems
**Purpose**: Filesystem I/O, BIDS loading, logging, external APIs  
**Dependencies**: Python standard library, pathlib, json, logging  
**Forbidden**: Any GUI imports (PySide6, Qt)

- `bids_loader.py`: Scan filesystem and build BIDS dataset models
- `logging_config.py`: Configure application-wide logging
- `paths.py`: Path utilities and directory management

### `ui/` - GUI Layer
**Purpose**: User interface, event handling, view models  
**Dependencies**: PySide6, core modules, infrastructure modules  
**Requirements**: Load UI from `.ui` files, delegate logic to core/infrastructure

- `app.py`: QApplication initialization and entry point
- `main_window.py`: Main window controller, loads `main_window.ui`
- `view_models.py`: Qt models (QAbstractTableModel, QAbstractItemModel) for views
- `widgets/`: Custom reusable widgets
- `ui_files/`: Qt Designer `.ui` files (XML)

### `cli/` - Command Line Interface
**Purpose**: Command-line tools for dataset operations  
**Dependencies**: argparse, core modules, infrastructure modules

- `main.py`: CLI commands (info, validate, export)

### `config/` - Configuration
**Purpose**: Application settings and configuration management

- `settings.py`: AppSettings dataclass, SettingsManager

## Coding Standards

### Python Style
- Follow PEP 8 conventions
- Use `snake_case` for functions and variables
- Use `PascalCase` for classes
- Use type hints for all function signatures
- Write comprehensive docstrings for all public APIs

### Type Hints
Always use Python 3.10+ type hint syntax:
```python
from typing import Optional
from pathlib import Path

def load_dataset(path: Path) -> BIDSDataset:
    """Load a BIDS dataset from path."""
    pass

def filter_subjects(
    subjects: list[BIDSSubject], 
    ids: list[str] | None = None
) -> list[BIDSSubject]:
    """Filter subjects by ID list."""
    pass
```

### Docstrings
Use Google-style docstrings:
```python
def export_dataset(request: ExportRequest) -> Path:
    """
    Export a filtered subset of a BIDS dataset.
    
    Creates a new BIDS-compliant dataset at the output location containing
    only the data matching the filter criteria.
    
    Args:
        request: Export request specifying source, filters, and destination.
        
    Returns:
        Path to the exported dataset root.
        
    Raises:
        ValueError: If export parameters are invalid.
        IOError: If export fails due to filesystem issues.
    """
    pass
```

### TODO Comments
When implementing skeletons or placeholders, add detailed TODOs:
```python
def _scan_files(self, session_path: Path) -> tuple[list[BIDSRun], list[BIDSFile]]:
    """Scan a session directory for BIDS files."""
    # TODO: scan modality directories (anat, func, dwi, fmap, etc.)
    # TODO: parse BIDS filenames to extract entities
    # TODO: group files into runs based on entities
    # TODO: identify session-level files vs run-level files
    raise NotImplementedError("_scan_files() is not implemented yet.")
```

## Development Workflow

### TODO-First Approach
When adding new features:
1. Create the **structure** (classes, functions, files)
2. Add **detailed TODOs** explaining what each part should do
3. Write **type hints** and **docstrings**
4. Provide **minimal stub implementations** (raise NotImplementedError)
5. Implement incrementally, following TODOs

### GUI Development
1. Design UI in Qt Designer and save as `.ui` file in `src/bidsio/ui/ui_files/`
2. Create controller class in `ui/` that loads the `.ui` file
3. Wire up signals/slots to methods
4. Delegate all business logic to `core/` or `infrastructure/`
5. Use view models to present data to Qt views

Example:
```python
from PySide6.QtWidgets import QMainWindow
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Slot

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._load_ui()
        self._connect_signals()
    
    def _load_ui(self):
        ui_file = QFile("src/bidsio/ui/ui_files/main_window.ui")
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        ui_file.close()
    
    def _connect_signals(self):
        # TODO: connect UI signals to slots
        pass
    
    @Slot()
    def open_dataset(self):
        # Delegate to core/infrastructure
        repository = BidsRepository(path)
        dataset = repository.load()
        # Update UI
```

### Testing
- Write tests for all `core/` and `infrastructure/` modules
- Use pytest fixtures in `tests/conftest.py`
- Test domain logic independently of UI
- Use pytest-qt for GUI testing when necessary

## Common Patterns

### Data Models
Use dataclasses for immutable data:
```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class BIDSSubject:
    """Represents a subject in a BIDS dataset."""
    subject_id: str
    sessions: list[BIDSSession] = field(default_factory=list)
    files: list[BIDSFile] = field(default_factory=list)
```

### Repository Pattern
Use repository for data access:
```python
class BidsRepository:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self._dataset: Optional[BIDSDataset] = None
    
    def load(self) -> BIDSDataset:
        """Load and index the BIDS dataset."""
        # Delegate to BidsLoader in infrastructure
        loader = BidsLoader(self.root_path)
        self._dataset = loader.load()
        return self._dataset
```

### Logging
Use the logging module, not print statements:
```python
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)

logger.info("Loading dataset from: {path}")
logger.debug("Found {count} subjects")
logger.error(f"Failed to load: {e}")
```

## When Reviewing or Editing Code

### ✅ Encourage
- Separation of concerns
- Type hints and docstrings
- Detailed TODOs for unimplemented features
- Testing domain logic
- Using `.ui` files for static layouts
- Logging instead of print statements

### ❌ Discourage
- GUI imports in `core/` or `infrastructure/`
- Business logic in UI classes
- Hard-coded widget creation (use `.ui` files)
- Global mutable state
- Missing type hints or docstrings
- Print statements (use logging)

### 🔧 Suggest Improvements
If the user writes GUI code in `core/`:
> "This logic should remain in the `ui/` module to maintain separation. Let's move it and create a method in `core/` that returns the data needed for display."

If the user hard-codes widgets:
> "Consider designing this in Qt Designer and saving it as a `.ui` file. This keeps the layout separate from logic and makes it easier to iterate on the design."

## VS Code Integration

### Debugging
Use provided launch configurations:
- **Run GUI**: Launches `src/bidsio/ui/app.py`
- **Run CLI**: Launches `src/bidsio/cli/main.py`
- **pytest: Current File**: Runs tests in the current file

### Python Environment
- Virtual environment: `.venv/` in project root
- Interpreter path: `.venv/Scripts/python.exe` (Windows)
- Testing: pytest enabled in VS Code

## BIDS Dataset Concepts

### Structure
BIDS datasets follow this hierarchy:
```
dataset/
├── dataset_description.json    # Required
├── participants.tsv            # Participant metadata
├── README
├── CHANGES
└── sub-<label>/               # Subject directories
    ├── [ses-<label>/]         # Optional session directories
    │   ├── anat/              # Anatomical scans
    │   ├── func/              # Functional scans
    │   ├── dwi/               # Diffusion scans
    │   └── ...
    └── sub-<label>_<entities>_<suffix>.<ext>
```

### BIDS Entities
Files contain entities in the filename:
- `sub-01`: subject ID
- `ses-pre`: session ID
- `task-rest`: task name
- `run-01`: run number
- `acq-highres`: acquisition parameter

### Modalities
Common modality types:
- `anat`: Anatomical (T1w, T2w)
- `ieeg`: Intracranial EEG

## Resources

- BIDS Specification: https://bids-specification.readthedocs.io/
- PySide6 Documentation: https://doc.qt.io/qtforpython-6/
- Qt Designer: Use for creating `.ui` files
- pybids: https://bids-standard.github.io/pybids/

## Project Status

This project is in **early development** with skeleton implementations. Many modules contain TODOs and `NotImplementedError` stubs. When implementing:

1. Start with `infrastructure/bids_loader.py` for actual BIDS parsing
2. Implement filtering logic in `core/filters.py`
3. Build export functionality in `core/export.py`
4. Design complete UI in Qt Designer
5. Wire up UI to domain logic

Focus on **incremental, testable progress** while maintaining architectural boundaries.
