"""
Preferences dialog for application settings.

This dialog allows users to view and modify application settings.
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox
from PySide6.QtCore import Slot, Signal
from PySide6.QtWidgets import QMessageBox as QB

from bidsio.config.settings import get_settings_manager, get_settings, AppSettings
from bidsio.infrastructure.logging_config import get_logger
from bidsio.ui.forms.preferences_dialog_ui import Ui_PreferencesDialog

logger = get_logger(__name__)


class PreferencesDialog(QDialog):
    """
    Dialog for editing application preferences.
    
    Allows users to modify settings organized by category.
    """
    
    # Signal emitted when preferences are saved
    close_preferences_dialog = Signal()
    preview_theme_changed = Signal(str)
    
    # Color name mappings
    COLOR_DISPLAY_TO_VALUE = {
        "Blue": "blue",
        "Amber": "amber",
        "Cyan": "cyan",
        "Light Green": "lightgreen",
        "Pink": "pink",
        "Purple": "purple",
        "Red": "red",
        "Teal": "teal",
        "Yellow": "yellow",
    }
    
    COLOR_VALUE_TO_DISPLAY = {v: k for k, v in COLOR_DISPLAY_TO_VALUE.items()}
    
    # Log level mappings
    LOG_LEVEL_DISPLAY_TO_VALUE = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    
    LOG_LEVEL_VALUE_TO_DISPLAY = {v: k for k, v in LOG_LEVEL_DISPLAY_TO_VALUE.items()}
    
    def __init__(self, parent=None):
        """
        Initialize the preferences dialog.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self._settings_manager = get_settings_manager()
        self._original_settings: Optional[AppSettings] = None
        
        self._setup_ui()
        self._connect_signals()
        self._load_settings()
        
        logger.debug("PreferencesDialog initialized")
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_PreferencesDialog()
        self.ui.setupUi(self)
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
        self.ui.btnSave.clicked.connect(self._on_save)
        self.ui.btnCancel.clicked.connect(self._on_cancel)
        self.ui.btnResetDefaults.clicked.connect(self._on_reset_defaults)
        self.ui.btnBrowseLogFile.clicked.connect(self._on_browse_log_file)
        self.ui.checkLogToFile.toggled.connect(self._on_log_to_file_toggled)
        self.ui.radioDark.toggled.connect(self._on_theme_settings_changed) # Only connect one radio button to avoid duplicate calls
        self.ui.comboPrimaryColor.currentTextChanged.connect(self._on_theme_settings_changed)
    
    def _load_settings(self):
        """Load current settings into the UI."""
        settings = get_settings()
        
        # Store original settings for comparison
        self._original_settings = settings
        
        # Logging settings
        log_level_name = self.LOG_LEVEL_VALUE_TO_DISPLAY.get(settings.log_level, "INFO")
        self.ui.comboLogLevel.setCurrentText(log_level_name)
        
        self.ui.checkLogToFile.setChecked(settings.log_to_file)
        
        if settings.log_file_path:
            self.ui.editLogFilePath.setText(str(settings.log_file_path))
        
        # Enable/disable log file path based on log_to_file
        self._on_log_to_file_toggled(settings.log_to_file)
        
        # UI settings - parse theme into mode and color
        theme = settings.theme
        if theme.startswith("dark_"):
            self.ui.radioDark.setChecked(True)
            color = theme[5:]  # Remove "dark_" prefix
        elif theme.startswith("light_"):
            self.ui.radioLight.setChecked(True)
            color = theme[6:]  # Remove "light_" prefix
        else:
            self.ui.radioDark.setChecked(True)
            color = "blue"
        
        color_display = self.COLOR_VALUE_TO_DISPLAY.get(color, "Blue")
        self.ui.comboPrimaryColor.setCurrentText(color_display)
        
        # BIDS settings
        self.ui.checkLazyLoading.setChecked(settings.lazy_loading)
        self.ui.spinMaxRecentItems.setValue(settings.max_recent_items)
        
        logger.debug("Settings loaded into UI")
    
    def _save_settings(self):
        """Save settings from UI to configuration."""
        # Get log level
        log_level_name = self.ui.comboLogLevel.currentText()
        log_level = self.LOG_LEVEL_DISPLAY_TO_VALUE.get(log_level_name, logging.INFO)
        
        # Get log file settings
        log_to_file = self.ui.checkLogToFile.isChecked()
        log_file_path = Path(self.ui.editLogFilePath.text()) if self.ui.editLogFilePath.text() else None
        
        # Get theme - construct from mode and color
        mode = "dark" if self.ui.radioDark.isChecked() else "light"
        color_display = self.ui.comboPrimaryColor.currentText()
        color = self.COLOR_DISPLAY_TO_VALUE.get(color_display, "blue")
        theme = f"{mode}_{color}"
        
        # Get BIDS settings
        lazy_loading = self.ui.checkLazyLoading.isChecked()
        max_recent_items = self.ui.spinMaxRecentItems.value()
        
        # Update settings
        self._settings_manager.update(
            log_level=log_level,
            log_to_file=log_to_file,
            log_file_path=log_file_path,
            theme=theme,
            lazy_loading=lazy_loading,
            max_recent_items=max_recent_items
        )
        
        logger.info("Settings saved")
    
    @Slot()
    def _on_save(self):
        """Handle Save button click."""
        try:
            self._save_settings()
            self.accept()
            self.close_preferences_dialog.emit()
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings:\n{str(e)}"
            )

    @Slot()
    def _on_cancel(self):
        """Handle Cancel button click."""
        self.reject()
        self.close_preferences_dialog.emit()

    @Slot()
    def _on_reset_defaults(self):
        """Handle Reset to Defaults button click."""
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all settings to their default values?",
            QB.StandardButton.Yes | QB.StandardButton.No,
            QB.StandardButton.No
        )
        
        if reply == QB.StandardButton.Yes:
            # Reset to defaults
            self._settings_manager.reset_to_defaults()
            
            # Reload UI with default values
            self._load_settings()
            
            logger.info("Settings reset to defaults")
            
            QMessageBox.information(
                self,
                "Reset Complete",
                "Settings have been reset to default values."
            )
    
    @Slot()
    def _on_browse_log_file(self):
        """Handle Browse button click for log file path."""
        current_path = self.ui.editLogFilePath.text()
        
        if current_path:
            initial_dir = str(Path(current_path).parent)
        else:
            initial_dir = str(Path.home())
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Log File",
            initial_dir,
            "Log Files (*.txt *.log);;All Files (*.*)"
        )
        
        if file_path:
            self.ui.editLogFilePath.setText(file_path)
    
    @Slot(bool)
    def _on_log_to_file_toggled(self, checked: bool):
        """Handle log to file checkbox toggle."""
        self.ui.editLogFilePath.setEnabled(checked)
        self.ui.btnBrowseLogFile.setEnabled(checked)
        self.ui.labelLogFilePath.setEnabled(checked)

    @Slot()
    def _on_theme_settings_changed(self):
        """Handle theme mode or color change."""
        mode = "dark" if self.ui.radioDark.isChecked() else "light"
        color_display = self.ui.comboPrimaryColor.currentText()
        color = self.COLOR_DISPLAY_TO_VALUE.get(color_display, "blue")
        theme = f"{mode}_{color}"
        self.preview_theme_changed.emit(theme)
