"""
Script to generate Python files from Qt Designer .ui files and compile resources.

This script:
1. Converts all .ui files in src/bidsio/ui/forms/ to Python modules using pyside6-uic
2. Compiles resources/resources.qrc to src/bidsio/ui/resources_rc.py using pyside6-rcc

The generated files are named with a '_ui' suffix.

Usage:
    python scripts/generate_ui.py
"""

import subprocess
import sys
from pathlib import Path
import re


def compile_resources():
    """Compile Qt resource files to Python module."""
    project_root = Path(__file__).parent.parent
    qrc_file = project_root / "src" / "bidsio" / "ui" / "resources" / "resources.qrc"
    output_file = project_root / "src" / "bidsio" / "ui" / "resources" / "resources_rc.py"
    
    if not qrc_file.exists():
        print(f"Warning: Resource file not found: {qrc_file}")
        return True  # Not an error, just skip
    
    print(f"\nCompiling resources:")
    print(f"  Input:  {qrc_file.name}")
    print(f"  Output: {output_file.name}")
    
    try:
        subprocess.run(
            ["pyside6-rcc", str(qrc_file), "-o", str(output_file)],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  ✓ Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Error: {e}")
        if e.stderr:
            print(f"    {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"  ✗ Error: pyside6-rcc not found")
        return False


def fix_resource_imports(ui_file_path):
    """Fix resource imports in generated UI files to use full module path."""
    try:
        content = ui_file_path.read_text()
        # Replace 'import resources_rc' with 'import bidsio.ui.resources.resources_rc as resources_rc'
        if 'import resources_rc' in content and 'import bidsio.ui.resources.resources_rc' not in content:
            content = re.sub(
                r'^import resources_rc$',
                'import bidsio.ui.resources.resources_rc as resources_rc',
                content,
                flags=re.MULTILINE
            )
            ui_file_path.write_text(content)
            return True
        return False
    except Exception as e:
        print(f"    Warning: Could not fix imports in {ui_file_path.name}: {e}")
        return False


def generate_ui_files():
    """Generate Python files from all .ui files."""
    # Get project root (parent of scripts/)
    project_root = Path(__file__).parent.parent
    ui_files_dir = project_root / "src" / "bidsio" / "ui" / "forms"
    
    if not ui_files_dir.exists():
        print(f"Error: UI files directory not found: {ui_files_dir}")
        return 1
    
    # Find all .ui files
    ui_files = list(ui_files_dir.glob("*.ui"))
    
    if not ui_files:
        print(f"No .ui files found in {ui_files_dir}")
        return 0
    
    print(f"Found {len(ui_files)} .ui file(s) to convert:")
    
    success_count = 0
    error_count = 0
    
    for ui_file in ui_files:
        # Generate output filename: main_window.ui -> main_window_ui.py
        output_file = ui_files_dir / f"{ui_file.stem}_ui.py"
        
        print(f"\n  Converting: {ui_file.name}")
        print(f"  Output:     {output_file.name}")
        
        try:
            # Run pyside6-uic
            result = subprocess.run(
                ["pyside6-uic", str(ui_file), "-o", str(output_file)],
                capture_output=True,
                text=True,
                check=True
            )
            
            print(f"  ✓ Success")
            
            # Fix resource imports in generated file
            if fix_resource_imports(output_file):
                print(f"    Fixed resource imports")
            
            success_count += 1
            
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Error: {e}")
            if e.stderr:
                print(f"    {e.stderr}")
            error_count += 1
        except FileNotFoundError:
            print(f"  ✗ Error: pyside6-uic not found")
            print(f"    Make sure PySide6 is installed: pip install PySide6")
            return 1
    
    print(f"\n{'='*60}")
    print(f"Conversion complete:")
    print(f"  Success: {success_count}")
    print(f"  Errors:  {error_count}")
    print(f"{'='*60}")
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    # Compile resources first
    resources_ok = compile_resources()
    
    # Then generate UI files
    ui_result = generate_ui_files()
    
    # Exit with error if either failed
    sys.exit(0 if (resources_ok and ui_result == 0) else 1)
