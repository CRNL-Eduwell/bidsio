"""
Path utilities and constants.

This module provides helper functions for working with paths in the application.
"""

import platform
from pathlib import Path
from typing import Optional
import os


def get_application_dir() -> Path:
    """
    Get the application's installation directory.
    
    Returns:
        Path to the application root (parent of src/).
    """
    # This file is in src/bidsio/infrastructure/
    # Application root is 3 levels up
    return Path(__file__).parent.parent.parent.parent


def get_cache_dir() -> Path:
    """
    Get the directory for caching temporary data.
    
    Returns:
        Path to cache directory.
    """
    # TODO: use platform-appropriate cache locations
    # TODO: implement cache cleanup strategy
    # TODO: create directory if it doesn't exist
    
    cache_dir = get_application_dir() / ".cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Path to the directory.
        
    Returns:
        The path (for chaining).
        
    Raises:
        IOError: If directory cannot be created.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as e:
        raise IOError(f"Failed to create directory {path}: {e}")


def is_subdirectory(child: Path, parent: Path) -> bool:
    """
    Check if one path is a subdirectory of another.
    
    Args:
        child: Potential child path.
        parent: Potential parent path.
        
    Returns:
        True if child is within parent, False otherwise.
    """
    try:
        child_resolved = child.resolve()
        parent_resolved = parent.resolve()
        return parent_resolved in child_resolved.parents or child_resolved == parent_resolved
    except (OSError, RuntimeError):
        return False


def get_relative_path(path: Path, base: Path) -> Optional[Path]:
    """
    Get the relative path from base to path.
    
    Args:
        path: The target path.
        base: The base path.
        
    Returns:
        Relative path from base to path, or None if not possible.
    """
    try:
        return path.relative_to(base)
    except ValueError:
        return None


def get_persistent_data_directory() -> Path:
    """
    Get the persistent data directory for the application (cross-platform).
    
    Similar to Unity's persistentDataPath, this provides a location where
    application data can be saved persistently across sessions.
    
    Returns:
        Path to the persistent data directory.
        
    Platform-specific locations:
        - Windows: %APPDATA%/LocalLow/bidsio
        - macOS: ~/Library/Application Support/bidsio
        - Linux: ~/.config/bidsio
    """
    system = platform.system()
    app_name = "bidsio"
    
    if system == "Windows":
        # Windows: %APPDATA%/LocalLow/bidsio
        base = Path.home() / "AppData" / "LocalLow"
    elif system == "Darwin":
        # macOS: ~/Library/Application Support/bidsio
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux/Unix: ~/.config/bidsio
        base = Path.home() / ".config"
    
    data_dir = base / app_name
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir


def get_settings_file_path() -> Path:
    """
    Get the path to the settings file.
    
    Returns:
        Path to the settings.json file.
    """
    return get_persistent_data_directory() / "settings.json"


def get_log_file_path() -> Path:
    """
    Get the path to the main log file.
    
    Returns:
        Path to the log.txt file.
    """
    return get_persistent_data_directory() / "log.txt"


def get_old_log_file_path() -> Path:
    """
    Get the path to the old log file.
    
    Returns:
        Path to the log.old.txt file.
    """
    return get_persistent_data_directory() / "log.old.txt"


# TODO: add functions for handling BIDS-specific paths
# TODO: add function to sanitize filenames for cross-platform compatibility
# TODO: add function to check available disk space before export
