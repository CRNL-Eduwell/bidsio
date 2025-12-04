"""
BIDS dataset loading and indexing.

This module is responsible for reading BIDS datasets from the filesystem
and constructing in-memory representations.
"""

import csv
import json
import re
from pathlib import Path
from typing import Optional

from ..core.models import (
    BIDSDataset,
    BIDSSubject,
    BIDSSession,
    BIDSRun,
    BIDSFile
)
from .logging_config import get_logger

logger = get_logger(__name__)


class BidsLoader:
    """
    Loads and indexes BIDS datasets from the filesystem.
    
    This class handles the low-level details of scanning directories,
    parsing BIDS filenames, and building the dataset model.
    """
    
    def __init__(self, root_path: Path):
        """
        Initialize the loader with a dataset root path.
        
        Args:
            root_path: Path to the root directory of a BIDS dataset.
        """
        self.root_path = Path(root_path)
    
    def load(self) -> BIDSDataset:
        """
        Load and index the BIDS dataset.
        
        Returns:
            A fully populated BIDSDataset object.
            
        Raises:
            FileNotFoundError: If root_path does not exist.
            ValueError: If the directory is not a valid BIDS dataset.
        """
        logger.info(f"Loading BIDS dataset from: {self.root_path}")
        
        # Validate that root_path exists
        if not self.root_path.exists():
            raise FileNotFoundError(f"Dataset path does not exist: {self.root_path}")
        
        if not self.root_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.root_path}")
        
        # Validate BIDS structure
        if not self._validate_bids_root():
            raise ValueError(f"Directory is not a valid BIDS dataset: {self.root_path}")
        
        # Load dataset description
        dataset_description = self._load_dataset_description()
        logger.debug(f"Dataset: {dataset_description.get('Name', 'Unknown')}")
        
        # Load participant metadata
        participant_metadata = self._load_participants_tsv()
        
        # Scan for subjects
        subjects = self._scan_subjects(participant_metadata)
        logger.info(f"Found {len(subjects)} subjects")
        
        # Scan for dataset-level files
        dataset_files = self._scan_dataset_files()
        logger.debug(f"Found {len(dataset_files)} dataset-level files")
        
        # Create dataset object
        dataset = BIDSDataset(
            root_path=self.root_path,
            subjects=subjects,
            dataset_description=dataset_description,
            dataset_files=dataset_files
        )
        
        return dataset
    
    def _validate_bids_root(self) -> bool:
        """
        Check if the root path is a valid BIDS dataset.
        
        Returns:
            True if valid, False otherwise.
        """
        desc_path = self.root_path / "dataset_description.json"
        
        if not desc_path.exists():
            logger.error("Missing dataset_description.json")
            return False
        
        try:
            with open(desc_path, 'r', encoding='utf-8') as f:
                desc = json.load(f)
                
            # Check required fields
            if "Name" not in desc:
                logger.warning("dataset_description.json missing 'Name' field")
            
            if "BIDSVersion" not in desc:
                logger.warning("dataset_description.json missing 'BIDSVersion' field")
            
            return True
            
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read dataset_description.json: {e}")
            return False
    
    def _load_dataset_description(self) -> dict:
        """
        Load the dataset_description.json file.
        
        Returns:
            Dictionary with dataset description metadata.
        """
        desc_path = self.root_path / "dataset_description.json"
        
        if not desc_path.exists():
            logger.warning("dataset_description.json not found")
            return {}
        
        try:
            with open(desc_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse dataset_description.json: {e}")
            return {}
    
    def _load_participants_tsv(self) -> dict[str, dict[str, str]]:
        """
        Load the participants.tsv file and parse metadata.
        
        Returns:
            Dictionary mapping subject IDs to their metadata.
        """
        participants_path = self.root_path / "participants.tsv"
        
        if not participants_path.exists():
            logger.info("participants.tsv not found, skipping metadata loading")
            return {}
        
        try:
            participants_metadata = {}
            
            with open(participants_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                
                for row in reader:
                    # Extract participant_id (should be first column)
                    participant_id = row.get('participant_id', '')
                    
                    if participant_id:
                        # Remove 'sub-' prefix if present for consistency
                        subject_id = participant_id.replace('sub-', '')
                        
                        # Store all other columns as metadata
                        metadata = {k: v for k, v in row.items() if k != 'participant_id'}
                        participants_metadata[subject_id] = metadata
                        
            logger.debug(f"Loaded metadata for {len(participants_metadata)} participants")
            return participants_metadata
            
        except Exception as e:
            logger.error(f"Failed to load participants.tsv: {e}")
            return {}
    
    def _scan_dataset_files(self) -> list[BIDSFile]:
        """
        Scan the dataset root for dataset-level files (README, LICENSE, CHANGES).
        
        Returns:
            List of BIDSFile objects for dataset-level files.
        """
        dataset_files = []
        
        # List of common dataset-level files to look for
        file_names = ['README', 'README.md', 'README.txt', 'LICENSE', 'CHANGES', 'CHANGES.md']
        
        for file_name in file_names:
            file_path = self.root_path / file_name
            
            if file_path.exists() and file_path.is_file():
                # Create a BIDSFile object for the dataset-level file
                dataset_file = BIDSFile(
                    path=file_path,
                    modality=None,
                    suffix=None,
                    extension=file_path.suffix if file_path.suffix else None,
                    entities={}
                )
                dataset_files.append(dataset_file)
                logger.debug(f"Found dataset file: {file_name}")
        
        return dataset_files
    
    def _scan_subjects(self, participant_metadata: dict[str, dict[str, str]]) -> list[BIDSSubject]:
        """
        Scan the dataset root for subject directories.
        
        Args:
            participant_metadata: Dictionary mapping subject IDs to their metadata.
        
        Returns:
            List of BIDSSubject objects.
        """
        subjects = []
        
        # Find all directories matching pattern 'sub-*'
        subject_dirs = sorted(self.root_path.glob('sub-*'))
        
        for subject_dir in subject_dirs:
            if not subject_dir.is_dir():
                continue
            
            # Extract subject ID from directory name
            subject_id = subject_dir.name.replace('sub-', '')
            
            logger.debug(f"Scanning subject: {subject_id}")
            
            # Get metadata for this subject
            metadata = participant_metadata.get(subject_id, {})
            
            # Scan for sessions
            sessions = self._scan_sessions(subject_dir)
            
            # If no sessions, scan the subject directory directly for files
            subject_files = []
            if not sessions:
                # Single-session dataset, scan subject directory directly
                _, subject_files = self._scan_files(subject_dir)
            
            # Create subject object
            subject = BIDSSubject(
                subject_id=subject_id,
                sessions=sessions,
                files=subject_files,
                metadata=metadata
            )
            
            subjects.append(subject)
        
        return subjects
    
    def _scan_sessions(self, subject_path: Path) -> list[BIDSSession]:
        """
        Scan a subject directory for session directories.
        
        Args:
            subject_path: Path to the subject directory.
            
        Returns:
            List of BIDSSession objects.
        """
        sessions = []
        
        # Find all directories matching pattern 'ses-*'
        session_dirs = sorted(subject_path.glob('ses-*'))
        
        for session_dir in session_dirs:
            if not session_dir.is_dir():
                continue
            
            # Extract session ID from directory name
            session_id = session_dir.name.replace('ses-', '')
            
            logger.debug(f"  Scanning session: {session_id}")
            
            # Scan for files in this session
            runs, session_files = self._scan_files(session_dir)
            
            # Create session object
            session = BIDSSession(
                session_id=session_id,
                runs=runs,
                files=session_files
            )
            
            sessions.append(session)
        
        return sessions
    
    def _scan_files(self, session_path: Path) -> tuple[list[BIDSRun], list[BIDSFile]]:
        """
        Scan a session directory for BIDS files.
        
        Args:
            session_path: Path to the session (or subject if no sessions).
            
        Returns:
            Tuple of (runs, session_level_files).
        """
        all_files = []
        
        # Scan for anat and ieeg directories (as requested)
        modality_dirs = ['anat', 'ieeg']
        
        for modality in modality_dirs:
            modality_path = session_path / modality
            
            if not modality_path.exists() or not modality_path.is_dir():
                continue
            
            logger.debug(f"    Scanning modality: {modality}")
            
            # Find all files in this modality directory
            for filepath in modality_path.iterdir():
                if filepath.is_file():
                    # Parse the BIDS filename
                    bids_file = self._parse_bids_filename(filepath, modality)
                    all_files.append(bids_file)
        
        # For now, we'll treat all files as session-level files
        # In the future, we could group them into runs based on entities
        runs = []
        session_files = all_files
        
        return runs, session_files
    
    def _parse_bids_filename(self, filepath: Path, modality: str) -> BIDSFile:
        """
        Parse a BIDS filename to extract entities and metadata.
        
        Args:
            filepath: Path to the BIDS file.
            modality: The modality directory (anat, ieeg, etc.).
            
        Returns:
            A BIDSFile object with parsed entities.
        """
        filename = filepath.name
        
        # Extract extension (handle .nii.gz as single extension)
        if filename.endswith('.nii.gz'):
            extension = '.nii.gz'
            name_without_ext = filename[:-7]
        else:
            extension = filepath.suffix
            name_without_ext = filepath.stem
        
        # Parse BIDS entities from filename using regex
        # BIDS entities follow pattern: key-value
        entity_pattern = r'([a-z]+)-([a-zA-Z0-9]+)'
        entities = {}
        
        for match in re.finditer(entity_pattern, name_without_ext):
            key = match.group(1)
            value = match.group(2)
            entities[key] = value
        
        # Extract suffix (last part of filename before extension)
        # Format: sub-XX_ses-YY_..._SUFFIX.extension
        parts = name_without_ext.split('_')
        suffix = parts[-1] if parts else None
        
        # If suffix contains a dash, it's an entity, not a suffix
        if suffix and '-' in suffix:
            suffix = None
        
        # Create BIDSFile object
        bids_file = BIDSFile(
            path=filepath,
            modality=modality,
            suffix=suffix,
            extension=extension,
            entities=entities
        )
        
        return bids_file


def is_bids_dataset(path: Path) -> bool:
    """
    Quick check if a directory appears to be a BIDS dataset.
    
    Args:
        path: Path to check.
        
    Returns:
        True if the directory contains a dataset_description.json file.
    """
    return (path / "dataset_description.json").exists()


def get_bids_version(dataset_path: Path) -> Optional[str]:
    """
    Get the BIDS version of a dataset.
    
    Args:
        dataset_path: Path to the BIDS dataset root.
        
    Returns:
        BIDS version string, or None if not found.
    """
    desc_path = dataset_path / "dataset_description.json"
    
    # TODO: handle errors gracefully
    if not desc_path.exists():
        return None
    
    try:
        with open(desc_path, 'r', encoding='utf-8') as f:
            desc = json.load(f)
            return desc.get("BIDSVersion")
    except (json.JSONDecodeError, IOError):
        return None
