"""
Export functionality for BIDS dataset subsets.

This module handles exporting filtered BIDS datasets to new locations.
"""

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .models import BIDSDataset, BIDSSubject, BIDSSession, BIDSFile


@dataclass
class SelectedEntities:
    """
    Entities selected for export.
    
    This represents which entity values should be included in the export.
    Each entity maps to a list of selected values.
    """
    
    entities: dict[str, list[str]] = field(default_factory=dict)
    """Dictionary mapping entity codes to selected values (e.g., {'sub': ['01', '02'], 'task': ['rest']})."""
    
    derivative_pipelines: list[str] = field(default_factory=list)
    """List of derivative pipeline names to include (e.g., ['fmriprep', 'freesurfer'])."""


@dataclass
class ExportRequest:
    """
    Specification for exporting a subset of a BIDS dataset.
    """
    
    source_dataset: BIDSDataset
    """The source dataset to export from."""
    
    selected_entities: SelectedEntities
    """Entities selected for export."""
    
    output_path: Path
    """Destination directory for the exported dataset."""
    
    overwrite: bool = False
    """Whether to overwrite/merge with existing destination."""


@dataclass
class ExportStats:
    """
    Statistics about files to be exported.
    """
    
    file_count: int = 0
    """Number of files to export."""
    
    total_size: int = 0
    """Total size in bytes."""
    
    def get_size_string(self) -> str:
        """Get human-readable size string."""
        if self.total_size < 1024:
            return f"{self.total_size} B"
        elif self.total_size < 1024 ** 2:
            return f"{self.total_size / 1024:.1f} KB"
        elif self.total_size < 1024 ** 3:
            return f"{self.total_size / (1024 ** 2):.1f} MB"
        else:
            return f"{self.total_size / (1024 ** 3):.2f} GB"


def export_dataset(
    request: ExportRequest,
    progress_callback: Optional[Callable[[int, int, Path], None]] = None
) -> Path:
    """
    Export a filtered subset of a BIDS dataset.
    
    Creates a new BIDS-compliant dataset at the output location containing
    only the data matching the entity selection.
    
    Args:
        request: Export request specifying source, entity selection, and destination.
        progress_callback: Optional callback(current, total, filepath) for progress updates.
        
    Returns:
        Path to the exported dataset root.
        
    Raises:
        ValueError: If export parameters are invalid.
        IOError: If export fails due to filesystem issues.
    """
    output_path = request.output_path
    source_dataset = request.source_dataset
    
    # Validate output path
    if not output_path.parent.exists():
        raise ValueError(f"Parent directory does not exist: {output_path.parent}")
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate list of files to export
    files_to_export = generate_file_list(source_dataset, request.selected_entities)
    
    if not files_to_export:
        raise ValueError("No files match the selected entities")
    
    # Copy files
    copy_file_tree(
        file_list=files_to_export,
        source_root=source_dataset.root_path,
        dest_root=output_path,
        progress_callback=progress_callback
    )
    
    # Copy dataset-level metadata files
    _copy_dataset_metadata(source_dataset, output_path)
    
    # Copy derivative pipeline metadata files
    if request.selected_entities.derivative_pipelines:
        _copy_derivative_metadata(
            source_dataset=source_dataset,
            output_path=output_path,
            selected_pipelines=request.selected_entities.derivative_pipelines
        )
    
    # Create filtered participants.tsv
    selected_subjects = request.selected_entities.entities.get('sub', [])
    if selected_subjects:
        source_participants = source_dataset.root_path / 'participants.tsv'
        if source_participants.exists():
            create_participants_tsv(
                source_participants=source_participants,
                selected_subjects=selected_subjects,
                output_path=output_path / 'participants.tsv'
            )
    
    return output_path


def generate_file_list(
    dataset: BIDSDataset, 
    selected_entities: SelectedEntities
) -> list[Path]:
    """
    Generate a list of file paths that match the selected entities.
    
    A file matches if all entities it possesses are in the selected lists.
    
    Args:
        dataset: The source dataset.
        selected_entities: The selected entities for export.
        
    Returns:
        List of absolute paths to files that match selection.
    """
    matching_files = []
    
    # Extract selected subject IDs
    # If 'sub' key is present with empty list, no subjects are selected
    if 'sub' in selected_entities.entities:
        selected_subjects = selected_entities.entities['sub']
        if not selected_subjects:
            # Empty selection - no subjects to export
            return []
    else:
        # No subject filter - export all subjects
        selected_subjects = []
    
    # Traverse subjects
    for subject in dataset.subjects:
        # Skip subject if not selected
        if selected_subjects and subject.subject_id not in selected_subjects:
            continue
        
        # Process subject-level files
        for file in subject.files:
            if _file_matches_entities(file, subject.subject_id, None, selected_entities):
                matching_files.append(file.path)
                # Include JSON sidecar if exists
                sidecar_path = _get_sidecar_path(file.path)
                if sidecar_path and sidecar_path.exists():
                    matching_files.append(sidecar_path)
        
        # Process session-level files
        for session in subject.sessions:
            # Check if session is selected
            selected_sessions = selected_entities.entities.get('ses', [])
            if selected_sessions and session.session_id and session.session_id not in selected_sessions:
                continue
            
            for file in session.files:
                if _file_matches_entities(file, subject.subject_id, session.session_id, selected_entities):
                    matching_files.append(file.path)
                    # Include JSON sidecar if exists
                    sidecar_path = _get_sidecar_path(file.path)
                    if sidecar_path and sidecar_path.exists():
                        matching_files.append(sidecar_path)
    
    # Handle derivatives if selected
    if selected_entities.derivative_pipelines:
        derivative_files = _get_derivative_files(dataset, selected_entities)
        matching_files.extend(derivative_files)
    
    # Remove duplicates and return
    return list(set(matching_files))


def copy_file_tree(
    file_list: list[Path],
    source_root: Path,
    dest_root: Path,
    progress_callback: Optional[Callable[[int, int, Path], None]] = None
) -> None:
    """
    Copy a list of files from source to destination, preserving structure.
    
    Args:
        file_list: List of files to copy (absolute paths).
        source_root: Root of the source dataset.
        dest_root: Root of the destination dataset.
        progress_callback: Optional callback(current, total, filepath) for progress updates.
        
    Raises:
        IOError: If file operations fail.
    """
    total_files = len(file_list)
    
    for i, source_file in enumerate(file_list, start=1):
        # Calculate relative path
        try:
            rel_path = source_file.relative_to(source_root)
        except ValueError:
            # File is not under source_root, skip it
            continue
        
        # Create destination path
        dest_file = dest_root / rel_path
        
        # Create parent directories if needed
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        try:
            shutil.copy2(source_file, dest_file)
        except IOError as e:
            # Log error but continue with other files
            print(f"Error copying {source_file}: {e}")
            continue
        
        # Call progress callback
        if progress_callback:
            progress_callback(i, total_files, source_file)


def create_participants_tsv(
    source_participants: Path,
    selected_subjects: list[str],
    output_path: Path
) -> None:
    """
    Create a participants.tsv file with only selected subjects.
    
    Args:
        source_participants: Path to source participants.tsv.
        selected_subjects: List of subject IDs to include.
        output_path: Path where new participants.tsv should be written.
    """
    if not source_participants.exists():
        return
    
    # Read source file
    with open(source_participants, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        return
    
    # First line is header
    header = lines[0]
    filtered_lines = [header]
    
    # Filter rows
    for line in lines[1:]:
        if not line.strip():
            continue
        
        # Extract participant_id (first column)
        parts = line.split('\t')
        if parts:
            participant_id = parts[0].strip()
            # Remove 'sub-' prefix if present
            subject_id = participant_id.replace('sub-', '')
            
            if subject_id in selected_subjects:
                filtered_lines.append(line)
    
    # Write filtered file
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(filtered_lines)


def calculate_export_stats(
    dataset: BIDSDataset,
    selected_entities: SelectedEntities
) -> ExportStats:
    """
    Calculate statistics about files to be exported.
    
    Args:
        dataset: The source dataset.
        selected_entities: The selected entities for export.
        
    Returns:
        ExportStats with file count and total size.
    """
    stats = ExportStats()
    
    # Generate file list
    files = generate_file_list(dataset, selected_entities)
    stats.file_count = len(files)
    
    # Calculate total size
    for file_path in files:
        if file_path.exists():
            stats.total_size += file_path.stat().st_size
    
    return stats


def _file_matches_entities(
    file: BIDSFile,
    subject_id: str,
    session_id: Optional[str],
    selected_entities: SelectedEntities
) -> bool:
    """
    Check if a file matches the selected entities.
    
    A file matches if ALL entities it possesses are in the selected lists.
    
    Args:
        file: The file to check.
        subject_id: The subject ID this file belongs to.
        session_id: The session ID this file belongs to (if any).
        selected_entities: The selected entities.
        
    Returns:
        True if the file matches, False otherwise.
    """
    # Check subject (always required)
    selected_subjects = selected_entities.entities.get('sub', [])
    if selected_subjects and subject_id not in selected_subjects:
        return False
    
    # Check session if file has one
    if session_id:
        selected_sessions = selected_entities.entities.get('ses', [])
        if selected_sessions and session_id not in selected_sessions:
            return False
    
    # Check all other entities in the file
    for entity_key, entity_value in file.entities.items():
        # Skip 'sub' and 'ses' as we already checked them
        if entity_key in ('sub', 'ses'):
            continue
        
        # If this entity is in the selection criteria (user has interacted with it)
        if entity_key in selected_entities.entities:
            selected_values = selected_entities.entities[entity_key]
            # If the list is empty or file's value is not in the list, exclude the file
            if not selected_values or entity_value not in selected_values:
                return False
    
    return True


def _get_sidecar_path(file_path: Path) -> Optional[Path]:
    """
    Get the JSON sidecar path for a data file.
    
    Args:
        file_path: Path to the data file.
        
    Returns:
        Path to JSON sidecar, or None if not applicable.
    """
    # Don't get sidecar for JSON files themselves
    if file_path.suffix == '.json':
        return None
    
    # Handle compound extensions like .nii.gz
    stem = file_path.name
    for ext in ['.nii.gz', '.nii', '.tsv', '.tsv.gz']:
        if stem.endswith(ext):
            stem = stem[:-len(ext)]
            break
    
    sidecar_path = file_path.parent / (stem + '.json')
    return sidecar_path if sidecar_path.exists() else None


def _get_derivative_files(
    dataset: BIDSDataset,
    selected_entities: SelectedEntities
) -> list[Path]:
    """
    Get all derivative files matching the selected entities.
    
    Uses the loaded derivative data from the dataset model to efficiently
    retrieve files without filesystem scanning.
    
    Args:
        dataset: The source dataset with loaded derivatives.
        selected_entities: The selected entities.
        
    Returns:
        List of derivative file paths.
    """
    derivative_files = []
    
    # Get selected subjects (if any)
    selected_subjects = selected_entities.entities.get('sub', [])
    
    # Iterate through subjects
    for subject in dataset.subjects:
        # Skip subject if not selected
        if selected_subjects and subject.subject_id not in selected_subjects:
            continue
        
        # Iterate through subject's derivatives
        for derivative in subject.derivatives:
            # Skip pipeline if not selected
            if derivative.pipeline_name not in selected_entities.derivative_pipelines:
                continue
            
            # Process derivative-level files (no session)
            for file in derivative.files:
                if _file_matches_entities(file, subject.subject_id, None, selected_entities):
                    derivative_files.append(file.path)
                    # Include JSON sidecar if exists
                    sidecar_path = _get_sidecar_path(file.path)
                    if sidecar_path and sidecar_path.exists():
                        derivative_files.append(sidecar_path)
            
            # Process derivative session files
            for session in derivative.sessions:
                # Check if session is selected
                selected_sessions = selected_entities.entities.get('ses', [])
                if selected_sessions and session.session_id and session.session_id not in selected_sessions:
                    continue
                
                for file in session.files:
                    if _file_matches_entities(file, subject.subject_id, session.session_id, selected_entities):
                        derivative_files.append(file.path)
                        # Include JSON sidecar if exists
                        sidecar_path = _get_sidecar_path(file.path)
                        if sidecar_path and sidecar_path.exists():
                            derivative_files.append(sidecar_path)
    
    return derivative_files


def _copy_dataset_metadata(source_dataset: BIDSDataset, output_path: Path) -> None:
    """
    Copy dataset-level metadata files.
    
    Args:
        source_dataset: The source dataset.
        output_path: The output directory.
    """
    source_root = source_dataset.root_path
    
    # Copy dataset_description.json
    dataset_desc = source_root / 'dataset_description.json'
    if dataset_desc.exists():
        shutil.copy2(dataset_desc, output_path / 'dataset_description.json')
    
    # Copy README
    readme = source_root / 'README'
    if readme.exists():
        shutil.copy2(readme, output_path / 'README')
    
    # Copy CHANGES
    changes = source_root / 'CHANGES'
    if changes.exists():
        shutil.copy2(changes, output_path / 'CHANGES')
    
    # Copy LICENSE
    license_file = source_root / 'LICENSE'
    if license_file.exists():
        shutil.copy2(license_file, output_path / 'LICENSE')


def _copy_derivative_metadata(
    source_dataset: BIDSDataset,
    output_path: Path,
    selected_pipelines: list[str]
) -> None:
    """
    Copy derivative pipeline metadata files.
    
    Copies dataset_description.json files for each selected derivative pipeline
    to maintain BIDS compliance in the exported dataset.
    
    Uses standard BIDS derivatives structure: derivatives/pipeline_name/dataset_description.json
    
    Args:
        source_dataset: The source dataset.
        output_path: The output directory.
        selected_pipelines: List of selected pipeline names.
    """
    # Get list of all subjects with derivatives
    subjects_with_derivatives = [s for s in source_dataset.subjects if s.derivatives]
    
    if not subjects_with_derivatives:
        return
    
    # Copy pipeline descriptions for each selected pipeline
    # Pipeline descriptions are at derivatives/pipeline_name/dataset_description.json
    for pipeline_name in selected_pipelines:
        # Source path: derivatives/pipeline_name/dataset_description.json
        source_desc_path = (
            source_dataset.root_path / 
            "derivatives" / 
            pipeline_name / 
            "dataset_description.json"
        )
        
        if source_desc_path.exists():
            # Destination path: same structure in output
            dest_desc_path = (
                output_path / 
                "derivatives" / 
                pipeline_name / 
                "dataset_description.json"
            )
            dest_desc_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_desc_path, dest_desc_path)
