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
    BIDSFile,
    BIDSDerivative,
    IEEGData
)
from .logging_config import get_logger
from .tsv_loader import load_tsv_file, find_ieeg_tsv_files

logger = get_logger(__name__)


class BidsLoader:
    """
    Loads and indexes BIDS datasets from the filesystem.
    
    This class handles the low-level details of scanning directories,
    parsing BIDS filenames, and building the dataset model.
    """
    
    def __init__(self, root_path: Path, progress_callback=None):
        """
        Initialize the loader with a dataset root path.
        
        Args:
            root_path: Path to the root directory of a BIDS dataset.
            progress_callback: Optional callback function(current, total, message) for progress updates.
        """
        self.root_path = Path(root_path)
        self.progress_callback = progress_callback
    
    def load_lazy(self) -> BIDSDataset:
        """
        Load only the basic dataset structure without scanning subjects.
        
        This is a fast operation that only reads dataset_description.json and
        identifies subject directories without loading their contents.
        
        Returns:
            A BIDSDataset with empty subject list (subjects can be loaded on-demand).
            
        Raises:
            FileNotFoundError: If root_path does not exist.
            ValueError: If the directory is not a valid BIDS dataset.
        """
        logger.info(f"Lazy loading BIDS dataset from: {self.root_path}")
        
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
        
        # Scan for dataset-level files
        dataset_files = self._scan_dataset_files()
        logger.debug(f"Found {len(dataset_files)} dataset-level files")
        
        # Create dataset object with empty subjects (will be loaded on-demand)
        dataset = BIDSDataset(
            root_path=self.root_path,
            subjects=[],
            dataset_description=dataset_description,
            dataset_files=dataset_files
        )
        
        logger.info("Lazy load complete - subjects not loaded yet")
        return dataset
    
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
        
        # Scan for subjects (eager mode - load all metadata)
        subjects = self._scan_subjects(participant_metadata, eager_load_metadata=True)
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
    
    def load_subject(self, subject_id: str) -> Optional[BIDSSubject]:
        """
        Load a single subject's data on-demand.
        
        Args:
            subject_id: The subject identifier (without 'sub-' prefix).
            
        Returns:
            BIDSSubject object if found, None otherwise.
        """
        subject_dir = self.root_path / f"sub-{subject_id}"
        
        if not subject_dir.exists() or not subject_dir.is_dir():
            logger.warning(f"Subject directory not found: {subject_dir}")
            return None
        
        logger.debug(f"Loading subject on-demand: {subject_id}")
        
        # Load participant metadata
        participant_metadata = self._load_participants_tsv()
        metadata = participant_metadata.get(subject_id, {})
        
        # Scan for sessions
        sessions = self._scan_sessions(subject_dir)
        
        # If no sessions, scan the subject directory directly for files
        subject_files = []
        if not sessions:
            # Single-session dataset, scan subject directory directly
            subject_files = self._scan_files(subject_dir)
        
        # Create subject object
        subject = BIDSSubject(
            subject_id=subject_id,
            sessions=sessions,
            files=subject_files,
            metadata=metadata
        )
        
        return subject
    
    def get_subject_ids(self) -> list[str]:
        """
        Get a list of all subject IDs in the dataset without loading their data.
        
        Returns:
            List of subject IDs (without 'sub-' prefix).
        """
        subject_dirs = sorted(self.root_path.glob('sub-*'))
        subject_ids = []
        
        for subject_dir in subject_dirs:
            if subject_dir.is_dir():
                subject_id = subject_dir.name.replace('sub-', '')
                subject_ids.append(subject_id)
        
        return subject_ids
    
    def _scan_subjects(
        self, 
        participant_metadata: dict[str, dict[str, str]],
        eager_load_metadata: bool = False
    ) -> list[BIDSSubject]:
        """
        Scan the dataset root for subject directories.
        
        Args:
            participant_metadata: Dictionary mapping subject IDs to their metadata.
            eager_load_metadata: If True, load all JSON sidecar metadata during parsing.
        
        Returns:
            List of BIDSSubject objects.
        """
        subjects = []
        
        # Find all directories matching pattern 'sub-*'
        subject_dirs = sorted(self.root_path.glob('sub-*'))
        total_subjects = len(subject_dirs)
        
        for idx, subject_dir in enumerate(subject_dirs):
            if not subject_dir.is_dir():
                continue
            
            # Extract subject ID from directory name
            subject_id = subject_dir.name.replace('sub-', '')
            
            logger.debug(f"Scanning subject: {subject_id}")
            
            # Report progress
            if self.progress_callback:
                self.progress_callback(idx + 1, total_subjects, f"Loading subject: {subject_id}")
            
            # Get metadata for this subject
            metadata = participant_metadata.get(subject_id, {})
            
            # Scan for sessions
            sessions = self._scan_sessions(subject_dir, eager_load_metadata)
            
            # If no sessions, scan the subject directory directly for files
            subject_files = []
            if not sessions:
                # Single-session dataset, scan subject directory directly
                subject_files = self._scan_files(subject_dir, eager_load_metadata)
            
            # Scan derivatives for this subject (if derivatives folder exists)
            derivatives = self._scan_subject_derivatives(subject_id, eager_load_metadata)
            
            # Load iEEG-specific data (channels and electrodes TSV files)
            ieeg_data = self._load_ieeg_data(subject_dir)
            
            # Create subject object
            subject = BIDSSubject(
                subject_id=subject_id,
                sessions=sessions,
                files=subject_files,
                derivatives=derivatives,
                metadata=metadata,
                ieeg_data=ieeg_data
            )
            
            subjects.append(subject)
        
        return subjects
    
    def _scan_sessions(self, subject_path: Path, eager_load_metadata: bool = False) -> list[BIDSSession]:
        """
        Scan a subject directory for session directories.
        
        Args:
            subject_path: Path to the subject directory.
            eager_load_metadata: If True, load all JSON sidecar metadata during parsing.
            
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
            session_files = self._scan_files(session_dir, eager_load_metadata)
            
            # Create session object
            session = BIDSSession(
                session_id=session_id,
                files=session_files
            )
            
            sessions.append(session)
        
        return sessions
    
    def _scan_files(self, session_path: Path, eager_load_metadata: bool = False) -> list[BIDSFile]:
        """
        Scan a session directory for BIDS files.
        
        Args:
            session_path: Path to the session (or subject if no sessions).
            eager_load_metadata: If True, load all JSON sidecar metadata during parsing.
            
        Returns:
            List of BIDSFile objects found in the session.
        """
        all_files = []
        
        # Scan for all standard BIDS modality directories
        modality_dirs = [
            'anat',      # Anatomical MRI
            'func',      # Functional MRI
            'dwi',       # Diffusion MRI
            'fmap',      # Field maps
            'ieeg',      # Intracranial EEG
            'eeg',       # Electroencephalography
            'meg',       # Magnetoencephalography
            'beh',       # Behavioral data
            'pet',       # Positron Emission Tomography
            'micr',      # Microscopy
            'nirs',      # Near-Infrared Spectroscopy
            'motion',    # Motion tracking
            'perf',      # Perfusion imaging
        ]
        
        for modality in modality_dirs:
            modality_path = session_path / modality
            
            if not modality_path.exists() or not modality_path.is_dir():
                continue
            
            logger.debug(f"    Scanning modality: {modality}")
            
            # Find all files in this modality directory
            for filepath in modality_path.iterdir():
                if filepath.is_file():
                    # Parse the BIDS filename
                    bids_file = self._parse_bids_filename(filepath, modality, eager_load_metadata)
                    all_files.append(bids_file)
        
        # Run information is stored in file entities (e.g., {'run': '01'})
        return all_files
    
    def _parse_bids_filename(
        self, 
        filepath: Path, 
        modality: str,
        eager_load_metadata: bool = False
    ) -> BIDSFile:
        """
        Parse a BIDS filename to extract entities and metadata.
        
        Args:
            filepath: Path to the BIDS file.
            modality: The modality directory (anat, ieeg, etc.).
            eager_load_metadata: If True, load JSON sidecar metadata immediately.
            
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
            entities=entities,
            metadata=None  # Will be loaded based on mode
        )
        
        # In eager mode, load metadata immediately using the BIDSFile method
        if eager_load_metadata:
            bids_file.load_metadata()
        # In lazy mode, metadata stays None and will be loaded on-demand
        
        return bids_file
    
    def _scan_subject_derivatives(
        self, 
        subject_id: str,
        eager_load_metadata: bool = False
    ) -> list[BIDSDerivative]:
        """
        Scan derivatives folder for a specific subject.
        
        Scans the standard BIDS derivatives structure:
        derivatives/pipeline_name/.../sub-XX/ses-YY/
        
        Args:
            subject_id: The subject ID to scan derivatives for.
            eager_load_metadata: If True, load all JSON sidecar metadata during parsing.
            
        Returns:
            List of BIDSDerivative objects, one per pipeline.
        """
        derivatives = []
        derivatives_root = self.root_path / "derivatives"
        
        # If no derivatives folder exists at dataset root, return empty list
        if not derivatives_root.exists():
            return derivatives
        
        # Scan each pipeline directory
        for pipeline_dir in sorted(derivatives_root.iterdir()):
            if not pipeline_dir.is_dir():
                continue
            
            pipeline_name = pipeline_dir.name
            
            # Load pipeline description if exists (at pipeline root)
            pipeline_description = {}
            pipeline_desc_file = pipeline_dir / 'dataset_description.json'
            if pipeline_desc_file.exists():
                try:
                    with open(pipeline_desc_file, 'r', encoding='utf-8') as f:
                        pipeline_description = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load pipeline description for {pipeline_name}: {e}")
            
            # Find this subject's data within the pipeline (recursively search for sub-XX)
            subject_derivative_path = self._find_subject_in_pipeline(pipeline_dir, subject_id)
            
            if not subject_derivative_path:
                continue
            
            logger.debug(f"Scanning derivative pipeline '{pipeline_name}' for subject {subject_id}")
            
            # Scan sessions within this subject's derivative data
            sessions = self._scan_derivative_sessions(subject_derivative_path, eager_load_metadata)
            
            # If no sessions, scan subject directory directly
            derivative_files = []
            if not sessions:
                derivative_files = self._scan_derivative_files(subject_derivative_path, eager_load_metadata)
            
            # Create derivative object
            derivative = BIDSDerivative(
                pipeline_name=pipeline_name,
                sessions=sessions,
                files=derivative_files,
                pipeline_description=pipeline_description
            )
            
            derivatives.append(derivative)
        
        return derivatives
    
    def _find_subject_in_pipeline(
        self,
        pipeline_dir: Path,
        subject_id: str
    ) -> Optional[Path]:
        """
        Find a subject's directory within a derivative pipeline.
        
        Searches recursively for sub-XX directory within the pipeline.
        
        Args:
            pipeline_dir: Path to the pipeline directory.
            subject_id: The subject ID to find.
            
        Returns:
            Path to the subject's derivative directory, or None if not found.
        """
        subject_pattern = f"sub-{subject_id}"
        
        # Search recursively for subject directory
        for path in pipeline_dir.rglob(subject_pattern):
            if path.is_dir() and path.name == subject_pattern:
                return path
        
        return None
    
    def _scan_derivative_sessions(
        self, 
        subject_path: Path,
        eager_load_metadata: bool = False
    ) -> list[BIDSSession]:
        """
        Scan sessions within a subject's derivative data.
        
        Args:
            subject_path: Path to the subject directory in derivatives.
            eager_load_metadata: If True, load all JSON sidecar metadata during parsing.
            
        Returns:
            List of BIDSSession objects.
        """
        sessions = []
        
        # Look for session directories (ses-*)
        session_dirs = sorted(subject_path.glob('ses-*'))
        
        for session_dir in session_dirs:
            if not session_dir.is_dir():
                continue
            
            # Extract session ID
            session_id = session_dir.name.replace('ses-', '')
            
            # Scan files in this session
            session_files = self._scan_derivative_files(session_dir, eager_load_metadata)
            
            # Create session object
            session = BIDSSession(
                session_id=session_id,
                files=session_files
            )
            
            sessions.append(session)
        
        return sessions
    
    def _scan_derivative_files(
        self, 
        path: Path,
        eager_load_metadata: bool = False
    ) -> list[BIDSFile]:
        """
        Scan files in a derivative directory.
        
        Uses the same logic as regular file scanning to maintain consistency.
        
        Args:
            path: Path to scan for files.
            eager_load_metadata: If True, load all JSON sidecar metadata during parsing.
            
        Returns:
            List of BIDSFile objects.
        """
        # Reuse the existing _scan_files method as derivatives follow BIDS structure
        return self._scan_files(path, eager_load_metadata)
    
    def _load_ieeg_data(self, subject_path: Path) -> Optional[IEEGData]:
        """
        Load iEEG-specific TSV data (channels and electrodes) for a subject.
        
        This method scans the subject directory and all subdirectories for
        _channels.tsv and _electrodes.tsv files and loads their contents.
        
        Args:
            subject_path: Path to the subject directory.
            
        Returns:
            IEEGData object if iEEG TSV files found, None otherwise.
        """
        # Find all channels and electrodes TSV files
        channels_files = find_ieeg_tsv_files(subject_path, 'channels')
        electrodes_files = find_ieeg_tsv_files(subject_path, 'electrodes')
        
        # If no iEEG TSV files found, return None
        if not channels_files and not electrodes_files:
            return None
        
        # Create IEEGData container
        ieeg_data = IEEGData()
        
        # Load all channels files
        for channels_file in channels_files:
            channels_data = load_tsv_file(channels_file)
            if channels_data:
                ieeg_data.channels[channels_file] = channels_data
                logger.debug(f"Loaded {len(channels_data)} channels from {channels_file.name}")
        
        # Load all electrodes files
        for electrodes_file in electrodes_files:
            electrodes_data = load_tsv_file(electrodes_file)
            if electrodes_data:
                ieeg_data.electrodes[electrodes_file] = electrodes_data
                logger.debug(f"Loaded {len(electrodes_data)} electrodes from {electrodes_file.name}")
        
        return ieeg_data if (ieeg_data.channels or ieeg_data.electrodes) else None


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
    
    if not desc_path.exists():
        logger.warning(f"dataset_description.json not found at: {desc_path}")
        return None
    
    try:
        with open(desc_path, 'r', encoding='utf-8') as f:
            desc = json.load(f)
            bids_version = desc.get("BIDSVersion")
            
            if bids_version is None:
                logger.warning(f"BIDSVersion field missing in: {desc_path}")
            
            return bids_version
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in dataset_description.json: {e}")
        return None
    except IOError as e:
        logger.error(f"Failed to read dataset_description.json: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading BIDS version: {e}")
        return None
