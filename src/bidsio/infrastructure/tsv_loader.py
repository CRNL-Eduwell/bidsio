"""
TSV file loading utilities.

This module provides functions for loading and parsing BIDS TSV files,
particularly for iEEG metadata files like _channels.tsv and _electrodes.tsv.
"""

import csv
from pathlib import Path
from typing import Optional

from .logging_config import get_logger

logger = get_logger(__name__)


def load_tsv_file(file_path: Path) -> list[dict]:
    """
    Load a TSV file and return list of row dictionaries.
    
    Each row becomes a dictionary mapping column names to values.
    
    Args:
        file_path: Path to the TSV file.
        
    Returns:
        List of dictionaries, one per row (excluding header).
        Returns empty list if file doesn't exist or cannot be parsed.
    """
    if not file_path.exists():
        logger.debug(f"TSV file not found: {file_path}")
        return []
    
    try:
        rows = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                # Strip whitespace from keys and values
                cleaned_row = {k.strip(): v.strip() for k, v in row.items()}
                rows.append(cleaned_row)
        
        logger.debug(f"Loaded {len(rows)} rows from {file_path.name}")
        return rows
        
    except Exception as e:
        logger.error(f"Failed to load TSV file {file_path}: {e}")
        return []


def get_tsv_headers(file_path: Path) -> list[str]:
    """
    Get the column headers from a TSV file without loading all data.
    
    Args:
        file_path: Path to the TSV file.
        
    Returns:
        List of column names, or empty list if file cannot be read.
    """
    if not file_path.exists():
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            return list(reader.fieldnames) if reader.fieldnames else []
    except Exception as e:
        logger.error(f"Failed to read TSV headers from {file_path}: {e}")
        return []


def find_ieeg_tsv_files(subject_path: Path, tsv_type: str) -> list[Path]:
    """
    Find all iEEG TSV files of a specific type for a subject.
    
    Args:
        subject_path: Path to the subject directory (e.g., /dataset/sub-01).
        tsv_type: Type of TSV file ('channels' or 'electrodes').
        
    Returns:
        List of paths to matching TSV files.
    """
    pattern = f"*_{tsv_type}.tsv"
    tsv_files = []
    
    # Search in subject directory and all subdirectories
    for tsv_file in subject_path.rglob(pattern):
        tsv_files.append(tsv_file)
    
    logger.debug(f"Found {len(tsv_files)} {tsv_type} files for {subject_path.name}")
    return tsv_files


def find_sidecar_tsv(data_file: Path, tsv_type: str) -> Optional[Path]:
    """
    Find the corresponding TSV sidecar file for a data file.
    
    BIDS TSV files follow similar naming conventions as JSON sidecars.
    For example:
    - sub-01_task-rest_ieeg.edf -> sub-01_task-rest_channels.tsv
    - sub-01_task-rest_ieeg.edf -> sub-01_task-rest_electrodes.tsv
    
    Args:
        data_file: Path to the data file.
        tsv_type: Type of TSV ('channels', 'electrodes', 'events', etc.).
        
    Returns:
        Path to the TSV file if found, None otherwise.
    """
    # Build expected TSV filename
    # Remove extension(s) from data file
    stem = data_file.name
    for ext in ['.edf', '.vhdr', '.eeg', '.nii.gz', '.nii', '.json']:
        if stem.endswith(ext):
            stem = stem[:-len(ext)]
    
    # Construct TSV filename
    tsv_filename = f"{stem}_{tsv_type}.tsv"
    tsv_path = data_file.parent / tsv_filename
    
    if tsv_path.exists():
        return tsv_path
    
    return None
