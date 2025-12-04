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
    # Setup logging
    settings = get_settings()
    log_file = settings.log_file_path if settings.log_to_file else None
    setup_logging(level=settings.log_level, log_file=log_file)
    
    logger.info("Starting bidsio application")
    
    # TODO: set application metadata (name, organization, version)
    # TODO: handle high DPI displays appropriately
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("bidsio")
    app.setOrganizationName("bidsio")
    app.setApplicationVersion(__version__)
    
    # Set application icon
    app.setWindowIcon(QIcon(":/icon.png"))
    
    # Apply Material Design theme for consistent cross-platform appearance
    # Available themes: dark_teal.xml, dark_blue.xml, dark_amber.xml, 
    #                   light_teal.xml, light_blue.xml, light_amber.xml, etc.
    apply_stylesheet(app, theme='dark_blue.xml')
    
    # Create and show main window
    window = MainWindow()
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
