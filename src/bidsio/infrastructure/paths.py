"""
Path utilities and constants.

This module provides helper functions for working with paths in the application.
"""

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


def get_config_dir() -> Path:
    """
    Get the directory where configuration files are stored.
    
    Returns:
        Path to configuration directory.
    """
    # TODO: consider user-specific config directory
    # TODO: handle different platforms (Windows, macOS, Linux)
    # TODO: create directory if it doesn't exist
    
    # For now, return a config/ subdirectory in the app root
    return get_application_dir() / "config"


def get_log_dir() -> Path:
    """
    Get the directory where log files should be stored.
    
    Returns:
        Path to log directory.
    """
    # TODO: consider user-specific log directory
    # TODO: use platform-appropriate locations (e.g., %APPDATA% on Windows)
    # TODO: create directory if it doesn't exist
    
    # For now, return a logs/ subdirectory in the app root
    log_dir = get_application_dir() / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir


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


# TODO: add functions for handling BIDS-specific paths
# TODO: add function to sanitize filenames for cross-platform compatibility
# TODO: add function to check available disk space before export
