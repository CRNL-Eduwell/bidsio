"""
Application settings and configuration.

This module provides centralized access to application settings.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import logging


@dataclass
class AppSettings:
    """Application-wide settings."""
    
    # Logging settings
    log_level: int = logging.INFO
    log_to_file: bool = False
    log_file_path: Optional[Path] = None
    
    # UI settings
    window_width: int = 1200
    window_height: int = 800
    theme: str = "default"  # TODO: support custom themes
    
    # BIDS settings
    validate_bids_on_load: bool = True
    cache_dataset_index: bool = True
    cache_directory: Optional[Path] = None
    
    # Export settings
    default_copy_mode: str = "copy"  # 'copy', 'symlink', or 'hardlink'
    verify_exports: bool = True
    
    # Performance settings
    max_threads: int = 4
    enable_progress_callbacks: bool = True
    
    # Recent files
    recent_datasets: list[str] = field(default_factory=list)
    max_recent_items: int = 10
    
    # TODO: add settings for filter defaults
    # TODO: add settings for export templates


class SettingsManager:
    """
    Manages loading and saving application settings.
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize the settings manager.
        
        Args:
            config_file: Path to configuration file. If None, uses default location.
        """
        self.config_file = config_file
        self._settings = AppSettings()
        
        # TODO: determine default config file location if not provided
        # TODO: load settings from file if it exists
    
    def load(self) -> AppSettings:
        """
        Load settings from configuration file.
        
        Returns:
            The loaded settings object.
        """
        # TODO: implement loading from JSON or TOML file
        # TODO: handle missing file (use defaults)
        # TODO: handle invalid/corrupted config file
        # TODO: validate loaded settings
        return self._settings
    
    def save(self, settings: Optional[AppSettings] = None) -> None:
        """
        Save settings to configuration file.
        
        Args:
            settings: Settings object to save. If None, saves current settings.
        """
        if settings is not None:
            self._settings = settings
        
        # TODO: implement saving to JSON or TOML file
        # TODO: ensure config directory exists
        # TODO: handle write errors gracefully
        # TODO: consider atomic writes (write to temp, then rename)
        pass
    
    def get(self) -> AppSettings:
        """
        Get the current settings.
        
        Returns:
            The current settings object.
        """
        return self._settings
    
    def update(self, **kwargs) -> None:
        """
        Update specific settings.
        
        Args:
            **kwargs: Setting names and values to update.
        """
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        
        # TODO: validate updated settings
        # TODO: optionally auto-save after update
    
    def add_recent_dataset(self, path: str) -> None:
        """
        Add a dataset path to the recent datasets list.
        
        Args:
            path: Path to the dataset to add.
        """
        # TODO: remove if already in list
        # TODO: add to front of list
        # TODO: trim to max_recent_items
        # TODO: optionally auto-save
        pass
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to their default values."""
        self._settings = AppSettings()


# Global settings instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """
    Get the global settings manager instance.
    
    Returns:
        The global SettingsManager.
    """
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
        _settings_manager.load()
    return _settings_manager


def get_settings() -> AppSettings:
    """
    Get the current application settings.
    
    Returns:
        The current AppSettings object.
    """
    return get_settings_manager().get()


# TODO: add validators for settings values
# TODO: add migration logic for settings file format changes
# TODO: consider using environment variables for some settings
