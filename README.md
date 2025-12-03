# BIDSIO

A Python desktop application for exploring, filtering, and exporting BIDS (Brain Imaging Data Structure) datasets.

## Overview

BIDSIO provides a graphical interface for:

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
└── cli/             # Optional command-line interface
```

### Architecture Principles

- **Strict separation** between domain logic (`core/`) and UI (`ui/`)
- `core/` and `infrastructure/` modules are GUI-agnostic and independently testable
- UI layouts defined in Qt Designer `.ui` files, not hard-coded in Python
- Type hints and comprehensive docstrings throughout

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
