# bidsio

<p align="center">
  <img src="https://raw.githubusercontent.com/CRNL-Eduwell/bidsio/master/src/bidsio/ui/resources/icon.png" alt="bidsio icon" width="128" height="128">
</p>

A Python desktop application for exploring, filtering, and exporting BIDS (Brain Imaging Data Structure) datasets.

## Overview

**bidsio** is a comprehensive tool for managing and working with BIDS-compliant neuroimaging datasets. It provides both a modern graphical interface and command-line tools for dataset operations.

### Core Features

- **Dataset Loading & Indexing**
  - Full BIDS-compliant dataset parsing
  - Support for derivatives (fmriprep, freesurfer, etc.)
  - iEEG-specific data loading (channels and electrodes TSV files)
  - Eager and lazy loading modes for optimal performance
  - Recent datasets menu for quick access

- **Dataset Exploration**
  - Hierarchical tree view (subjects → sessions → modalities → files)
  - Detailed information panel with file metadata
  - File viewers for JSON, TSV, and text files
  - Dataset statistics and entity summaries
  - Participant metadata display (from participants.tsv)

- **Advanced Filtering**
  - **Simple Mode**: Quick row-based filtering with AND logic
  - **Advanced Mode**: Full logical expressions with AND/OR/NOT operations
  - Filter by multiple criteria:
    - Subject IDs
    - Sessions
    - Tasks, acquisitions, runs, and other BIDS entities
    - Modalities (anat, func, dwi, ieeg, etc.)
    - Participant attributes (age, sex, group, etc.)
    - iEEG channel attributes (type, status, etc.)
    - iEEG electrode attributes (name, location, etc.)
  - Filter presets: Save and load frequently-used filters
  - Visual filter expression editor with tree view
  - Real-time preview of filter results

- **Dataset Export**
  - Export filtered dataset subsets while maintaining BIDS structure
  - Entity-based selection with preview statistics
  - Include/exclude derivatives selectively
  - Preserve all BIDS metadata and sidecar files
  - Progress tracking with file-by-file updates
  - Automatic validation of exported datasets

- **Customization**
  - Multiple Qt Material themes (dark/light variants)
  - Adjustable UI colors (blue, amber, cyan, pink, purple, red, light green)
  - Configurable logging levels
  - Persistent user preferences

## Requirements

- **Python**: 3.13.7 (strictly enforced)
- **GUI Framework**: PySide6 (Qt6 for Python)
- **Dependencies**: See [`requirements.txt`](requirements.txt) for complete list

### Key Dependencies

- **PySide6**: Qt6 bindings for modern GUI
- **qt-material**: Material Design themes
- **Pydantic**: Data validation and models
- **NumPy**: Numerical operations
- Various utilities for JSON parsing, file operations, etc.

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

Launch the graphical interface:

```bash
python src/bidsio/ui/app.py
```

Or use the VS Code debugger with the **"Run GUI"** configuration (F5).

#### Main Workflow

1. **Load Dataset**: Click "Load Dataset" or press `Ctrl+O` to select a BIDS dataset directory
2. **Browse**: Navigate the hierarchical tree view to explore subjects, sessions, and files
3. **Inspect**: Click any item to view detailed information in the right panel
4. **Filter** (optional):
   - Click "Filter" button or press `Ctrl+F`
   - Choose Simple Mode for quick AND-based filtering
   - Choose Advanced Mode for complex logical expressions (AND/OR/NOT)
   - Save filters as presets for reuse
5. **Export**:
   - Click "Export" button or press `Ctrl+E`
   - Select entities to include (subjects, sessions, tasks, etc.)
   - Choose whether to include derivatives
   - Preview statistics (file count and total size)
   - Select output directory and confirm export

#### Keyboard Shortcuts

- `Ctrl+O`: Load Dataset
- `Ctrl+F`: Open Filter Dialog
- `Ctrl+E`: Export Dataset
- `Ctrl+,`: Open Preferences
- `Ctrl+Q`: Quit Application
- `F1`: Show Help/About

#### File Viewers

Double-click files in the tree view to open specialized viewers:
- **JSON files**: Syntax-highlighted JSON viewer with expand/collapse
- **TSV files**: Tabular data viewer with sortable columns
- **Text files**: Plain text viewer (README, CHANGES, etc.)

## Development

### Project Structure

```
src/bidsio/
├── config/              # Application configuration and settings
│   ├── settings.py      # AppSettings, SettingsManager (persistent JSON storage)
│   └── __init__.py
├── core/                # Pure domain logic (GUI-agnostic)
│   ├── models.py        # Data models: BIDSDataset, BIDSSubject, BIDSSession, BIDSFile, etc.
│   ├── repository.py    # BidsRepository: Dataset access pattern
│   ├── filters.py       # Filter conditions: SubjectIdFilter, EntityFilter, LogicalOperation, etc.
│   ├── export.py        # Export functionality: ExportRequest, calculate stats, copy files
│   ├── entity_config.py # BIDS entity definitions (sub, ses, task, run, etc.)
│   └── __init__.py
├── infrastructure/      # I/O, BIDS loading, filesystem, logging
│   ├── bids_loader.py   # BidsLoader: Scan filesystem and build dataset models
│   ├── tsv_loader.py    # TSV file parsing (participants.tsv, channels.tsv, electrodes.tsv)
│   ├── logging_config.py # Logging configuration
│   ├── paths.py         # Path utilities (user data directories, config paths)
│   └── __init__.py
├── ui/                  # PySide6 GUI layer
│   ├── app.py           # Application entry point and initialization
│   ├── main_window.py   # Main window controller
│   ├── about_dialog.py  # About dialog
│   ├── preferences_dialog.py # Settings editor
│   ├── filter_builder_dialog.py # Filter creation (Simple & Advanced modes)
│   ├── export_dialog.py # Export configuration
│   ├── entity_selector_dialog.py # Entity value selection
│   ├── json_viewer_dialog.py # JSON file viewer
│   ├── table_viewer_dialog.py # TSV file viewer
│   ├── text_viewer_dialog.py # Text file viewer
│   ├── progress_dialog.py # Progress tracking for long operations
│   ├── workers.py       # Background worker threads for loading/exporting
│   ├── forms/           # Qt Designer .ui files and generated Python modules
│   │   ├── *.ui         # XML UI definitions (edited in Qt Designer)
│   │   └── *_ui.py      # Generated Python code (auto-compiled)
│   ├── widgets/         # Reusable custom widgets
│   │   ├── details_panel.py # File details display
│   │   ├── simple_filter_builder_widget.py # Simple filter mode widget
│   │   ├── advanced_filter_builder_widget.py # Advanced filter mode widget
│   │   └── __init__.py
│   ├── resources/       # Icons, stylesheets, documentation
│   │   ├── resources.qrc # Qt resource file
│   │   ├── resources_rc.py # Compiled resources
│   │   ├── icons/       # SVG icons (Material Design)
│   │   ├── custom.qss   # Custom stylesheet additions
│   │   └── filtering_help.md # Filter syntax help
│   └── __init__.py

tests/                   # Test suite
├── conftest.py          # pytest fixtures and configuration
├── test_core_models.py  # Core model tests
├── test_filters.py      # Filter logic tests
├── test_export.py       # Export functionality tests
├── test_bids_loader.py  # BIDS loading tests
├── test_derivatives.py  # Derivative handling tests
├── test_integration.py  # End-to-end integration tests
├── test_settings.py     # Settings persistence tests
└── __init__.py

scripts/
└── generate_ui.py       # UI compilation script (compiles .ui and .qrc files)
```

### Architecture Principles

- **Strict Separation of Concerns**
  - `core/`: Pure domain logic - NO GUI imports allowed
  - `infrastructure/`: External systems (filesystem, logging) - NO GUI imports allowed
  - `ui/`: PySide6 GUI layer only - delegates all logic to core/infrastructure
  - This enables independent testing and potential future CLI development

- **UI Design Philosophy**
  - ALL UI layouts defined in Qt Designer `.ui` files (XML format)
  - NEVER create widgets programmatically in Python code
  - Python UI classes only import generated UI, call `setupUi()`, and wire signals
  - Exceptions: Truly dynamic widgets whose structure depends on runtime data

- **Type Safety**
  - Comprehensive type hints throughout the codebase
  - Pydantic models for data validation where appropriate
  - Python 3.10+ type hint syntax (e.g., `list[str]` instead of `List[str]`)

- **Testing**
  - Pytest-based test suite with high coverage
  - Core business logic tested independently of UI
  - Integration tests for end-to-end workflows
  - pytest-qt for GUI component testing when necessary

- **Code Quality**
  - Google-style docstrings for all public APIs
  - PEP 8 compliance
  - Comprehensive logging instead of print statements
  - Detailed TODO comments for unimplemented features

### UI Development Workflow

**All UI layouts MUST be created in Qt Designer - never hard-code widgets in Python!**

1. **Design UI** in Qt Designer and save `.ui` files in `src/bidsio/ui/forms/`
2. **Compile `.ui` files** to Python modules (choose one method):
   - **Option A** (Recommended): Run `python scripts/generate_ui.py` (auto-detects all `.ui` files and resources)
   - **Option B**: Right-click the `.ui` file in VS Code → "Compile Qt UI file" (requires Qt extension)
   - **Option C**: Run `pyside6-uic <file>.ui -o <file>_ui.py` manually
   - Generated files use `<name>_ui.py` naming (e.g., `main_window.ui` → `main_window_ui.py`)
3. **Import and use** the generated UI classes in your Python code:
   ```python
   from bidsio.ui.forms.main_window_ui import Ui_MainWindow
   
   class MainWindow(QMainWindow):
       def __init__(self):
           super().__init__()
           self.ui = Ui_MainWindow()
           self.ui.setupUi(self)
           self._connect_signals()  # Wire up event handlers
       
       def _connect_signals(self):
           """Connect UI signals to handler methods."""
           self.ui.actionOpen.triggered.connect(self.open_dataset)
   ```

**Important Notes:**
- Always recompile UI files after modifying `.ui` files in Qt Designer
- When debugging with F5, UI files are automatically compiled via preLaunchTask
- Python UI classes should be thin - they wire up view models but don't implement business logic
- Keep all business logic in `core/` and `infrastructure/` modules

### Resources Management

Icons and other resources are managed using Qt's resource system for efficient bundling.

#### Adding New Resources

1. **Add resources** to `src/bidsio/ui/resources/resources.qrc` file:
   ```xml
   <RCC>
     <qresource prefix="/">
       <file>icons/new_icon.svg</file>
     </qresource>
   </RCC>
   ```

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
   import bidsio.ui.resources.resources_rc  # Registers all resources
   ```

4. **Use resources** with the `:/` prefix:
   ```python
   from PySide6.QtGui import QIcon
   
   # Icons
   icon = QIcon(":/icons/folder.svg")
   button.setIcon(icon)
   
   # In .ui files, set icon property to: :/icons/folder.svg
   ```

#### Icon Guidelines

- **NEVER use emoji characters** in UI code (causes Unicode issues on Windows)
- Use Material Design icons from [Google Fonts Icons](https://fonts.google.com/icons)
- Download icons with "Fill" and "Outlined" styles for best appearance
- Store icons in `src/bidsio/ui/resources/icons/` as SVG files
- Always recompile resources after adding new icons: `python scripts/generate_ui.py`

**Note:** The `generate_ui.py` script automatically compiles resources and fixes imports in generated UI files.

### Testing

Run the complete test suite:

```bash
pytest
```

Run specific test modules:

```bash
pytest tests/test_filters.py      # Filter logic tests
pytest tests/test_export.py       # Export functionality
pytest tests/test_integration.py  # End-to-end workflows
```

Run with coverage report:

```bash
pytest --cov=bidsio --cov-report=html
```

#### Test Organization

- **`test_core_models.py`**: Data model validation and methods
- **`test_filters.py`**: All filter condition types and logical operations
- **`test_export.py`**: Export statistics, file matching, and dataset copying
- **`test_bids_loader.py`**: Dataset loading from filesystem
- **`test_derivatives.py`**: Derivative pipeline handling
- **`test_integration.py`**: Full workflows (load → filter → export)
- **`test_settings.py`**: Settings persistence and configuration
- **`conftest.py`**: Shared pytest fixtures (sample datasets, etc.)

#### Writing Tests

- Use pytest fixtures from `conftest.py` for test datasets
- Test core logic independently of UI (no Qt dependencies in core tests)
- Use `pytest-qt` for GUI component testing when necessary
- Mock filesystem operations for unit tests, use real files for integration tests

## Supported BIDS Features

### Dataset Structure

- ✅ Standard BIDS hierarchy (subjects, sessions, modalities)
- ✅ Subject-level files (no session directory)
- ✅ Session-level files
- ✅ Dataset-level files (README, CHANGES, participants.tsv, etc.)
- ✅ Derivatives (fmriprep, freesurfer, custom pipelines)

### Modalities

- ✅ Anatomical (anat): T1w, T2w, FLAIR, etc.
- ✅ Functional (func): bold, events, physio
- ✅ Diffusion (dwi): dwi, bval, bvec
- ✅ Intracranial EEG (ieeg): ieeg, channels.tsv, electrodes.tsv
- ✅ Field maps (fmap)
- ✅ All other BIDS modalities

### Entities

Supports all BIDS entities including:
- Core: `sub`, `ses`, `task`, `run`, `acq`
- Advanced: `dir`, `echo`, `flip`, `inv`, `mt`, `part`, `proc`
- Descriptive: `desc`, `label`, `space`, `res`, `den`
- Specialized: `tracksys`, `nuc`, `voi`, `ce`, `trc`, `stain`, `rec`, `mod`, `hemi`, `split`, `recording`, `chunk`, `seg`, `sample`

### Metadata Files

- ✅ `dataset_description.json`
- ✅ `participants.tsv` (with filtering support)
- ✅ JSON sidecar files (per-file metadata)
- ✅ `*_channels.tsv` (iEEG channel metadata)
- ✅ `*_electrodes.tsv` (iEEG electrode locations)
- ✅ `*_events.tsv` (task events)
- ✅ Text files (README, CHANGES, LICENSE, etc.)

## Configuration

### Application Settings

Settings are automatically persisted in platform-specific locations:

- **Windows**: `%APPDATA%\LocalLow\bidsio\settings.json`
- **macOS**: `~/Library/Application Support/bidsio/settings.json`
- **Linux**: `~/.config/bidsio/settings.json`

### Available Settings

Access via **File → Preferences** (Ctrl+,):

#### General
- **Loading Mode**: Eager (load all data) or Lazy (load on-demand) - affects initial loading speed
- **Recent Datasets**: Maximum number of recent datasets to track

#### Appearance
- **Theme**: Multiple Qt Material themes available
  - Dark: Blue (default), Teal, Amber
  - Light: Blue, Teal, Amber
- **Color Accent**: Blue, Amber, Cyan, Light Green, Pink, Purple, Red
- **Window Size**: Preserved between sessions

#### Logging
- **Log Level**: Debug, Info, Warning, Error
- **Log to File**: Enable/disable file logging
- **Log Location**: View and change log file path

### Filter Presets

Save frequently-used filters in: `%APPDATA%\LocalLow\bidsio\filter_presets\`

Filter presets are JSON files that can be:
- Created via the Filter Builder dialog ("Save Preset" button)
- Loaded via the Filter Builder dialog ("Load Preset" button)
- Shared with other users by copying JSON files

## Performance Considerations

### Loading Modes

- **Eager Loading** (default): Loads all dataset information upfront
  - Slower initial load for large datasets
  - Faster subsequent operations (filtering, browsing)
  - Recommended for datasets < 1000 subjects

- **Lazy Loading**: Loads minimal information initially
  - Very fast initial load
  - Loads data on-demand as you navigate
  - Recommended for very large datasets (> 1000 subjects)

### Export Performance

- Export operations use background threads to keep UI responsive
- Progress updates show current file being copied
- Large exports can be cancelled mid-operation

### Filter Performance

- Simple filters (subject IDs, sessions) are very fast
- Complex filters with participant/channel/electrode attributes may be slower on large datasets
- Filter preview shows match count before applying

## Troubleshooting

### Common Issues

**Q: UI doesn't load or shows errors about missing UI files**  
A: Run `python scripts/generate_ui.py` to compile all `.ui` files from Qt Designer sources.

**Q: Icons don't appear or show as broken**  
A: Resources haven't been compiled. Run `python scripts/generate_ui.py` to compile the resource file.

**Q: Dataset loading is very slow**  
A: For large datasets (>1000 subjects), enable Lazy Loading mode in Preferences.

**Q: Export fails with permission errors**  
A: Ensure the output directory is writable and not currently in use by another application.

**Q: Filter doesn't match expected subjects**  
A: Check filter logic in Advanced Mode tree view. Ensure entity values are exact matches (case-sensitive).

### Debug Logging

Enable debug logging for detailed troubleshooting:

1. Open **File → Preferences**
2. Set **Log Level** to **Debug**
3. Enable **Log to File**
4. View log file location in Preferences
5. Reproduce the issue
6. Check log file for detailed error messages

### Getting Help

- Check the [BIDS Specification](https://bids-specification.readthedocs.io/) for dataset structure questions
- Review filter help in the Filter Builder dialog (Help button)
- Enable debug logging and check log files for errors

## Known Limitations

- **Performance**: Very large datasets (>5000 subjects) may experience slow filtering with complex conditions
- **Validation**: Dataset validation is basic - use [BIDS Validator](https://github.com/bids-standard/bids-validator) for comprehensive validation
- **Edit Mode**: No support for modifying datasets in-place (read-only tool)

## License

**bidsio** is released under the **BSD-3-Clause License**.

Copyright © 2025  
Benjamin BONTEMPS

This license allows unrestricted use, modification, and redistribution of the software, while prohibiting the use of the author's name for endorsement without permission. See the [`LICENSE`](https://raw.githubusercontent.com/CRNL-Eduwell/bidsio/master/LICENSE) file for details.