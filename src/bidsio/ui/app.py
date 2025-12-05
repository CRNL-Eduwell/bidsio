"""
Main application entry point.

This module initializes and runs the PySide6 application.
"""

import sys
from pathlib import Path

# Add parent directory to path to allow relative imports when run directly
if __name__ == "__main__":
    src_path = Path(__file__).parent.parent.parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from qt_material import apply_stylesheet

from bidsio import __version__
from bidsio.infrastructure.logging_config import setup_logging, get_logger
from bidsio.config.settings import get_settings
from bidsio.ui.main_window import MainWindow
import bidsio.ui.resources.resources_rc  # Import resources to register them


logger = get_logger(__name__)


def main():
    """
    Main entry point for the GUI application.
    """
    # Setup logging (logs to persistent data directory with rotation)
    settings = get_settings()
    setup_logging(
        level=settings.log_level,
        log_file=settings.log_file_path,
        log_to_file=settings.log_to_file
    )
    
    logger.info("Starting bidsio application")
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("bidsio")
    app.setOrganizationName("Eduwell")
    app.setApplicationVersion(__version__)
    
    # Set application icon
    app.setWindowIcon(QIcon(":/icon.png"))
    
    # Create and show main window
    window = MainWindow()
    window.apply_theme(settings.theme)
    window.show()
    
    logger.info("Main window displayed")
    
    # TODO: handle command-line arguments (e.g., open dataset path)
    # TODO: restore window geometry from settings
    
    # Run event loop
    exit_code = app.exec()
    
    logger.info(f"Application exiting with code {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
