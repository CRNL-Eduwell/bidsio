"""
Test BIDS dataset loading functionality.
"""

import tempfile
from pathlib import Path
import json
import pytest

from bidsio.core.repository import BidsRepository
from bidsio.infrastructure.bids_loader import BidsLoader, is_bids_dataset


class TestBidsLoader:
    """Test cases for BidsLoader class."""
    
    def test_is_bids_dataset_with_valid_dataset(self, tmp_path):
        """Test that is_bids_dataset returns True for valid dataset."""
        # Create a minimal BIDS dataset
        dataset_desc = {
            "Name": "Test Dataset",
            "BIDSVersion": "1.8.0"
        }
        
        desc_file = tmp_path / "dataset_description.json"
        desc_file.write_text(json.dumps(dataset_desc))
        
        assert is_bids_dataset(tmp_path) is True
    
    def test_is_bids_dataset_with_invalid_dataset(self, tmp_path):
        """Test that is_bids_dataset returns False for invalid dataset."""
        # No dataset_description.json
        assert is_bids_dataset(tmp_path) is False
    
    def test_validate_bids_root_success(self, tmp_path):
        """Test BIDS validation with valid dataset."""
        # Create minimal BIDS dataset
        dataset_desc = {
            "Name": "Test Dataset",
            "BIDSVersion": "1.8.0"
        }
        
        desc_file = tmp_path / "dataset_description.json"
        desc_file.write_text(json.dumps(dataset_desc))
        
        loader = BidsLoader(tmp_path)
        assert loader._validate_bids_root() is True
    
    def test_validate_bids_root_missing_file(self, tmp_path):
        """Test BIDS validation fails when dataset_description.json is missing."""
        loader = BidsLoader(tmp_path)
        assert loader._validate_bids_root() is False
    
    def test_load_dataset_description(self, tmp_path):
        """Test loading dataset description."""
        dataset_desc = {
            "Name": "Test Dataset",
            "BIDSVersion": "1.8.0",
            "Authors": ["Test Author"]
        }
        
        desc_file = tmp_path / "dataset_description.json"
        desc_file.write_text(json.dumps(dataset_desc))
        
        loader = BidsLoader(tmp_path)
        desc = loader._load_dataset_description()
        
        assert desc["Name"] == "Test Dataset"
        assert desc["BIDSVersion"] == "1.8.0"
        assert "Test Author" in desc["Authors"]
    
    def test_load_participants_tsv(self, tmp_path):
        """Test loading participants.tsv file."""
        # Create participants.tsv
        participants_content = "participant_id\tage\tsex\n"
        participants_content += "sub-01\t25\tM\n"
        participants_content += "sub-02\t30\tF\n"
        
        participants_file = tmp_path / "participants.tsv"
        participants_file.write_text(participants_content)
        
        loader = BidsLoader(tmp_path)
        metadata = loader._load_participants_tsv()
        
        assert "01" in metadata
        assert metadata["01"]["age"] == "25"
        assert metadata["01"]["sex"] == "M"
        assert metadata["02"]["age"] == "30"
        assert metadata["02"]["sex"] == "F"
    
    def test_parse_bids_filename_anat(self, tmp_path):
        """Test parsing anatomical BIDS filename."""
        # Create a sample BIDS file
        filepath = tmp_path / "sub-01_ses-pre_T1w.nii.gz"
        filepath.touch()
        
        loader = BidsLoader(tmp_path)
        bids_file = loader._parse_bids_filename(filepath, "anat")
        
        assert bids_file.modality == "anat"
        assert bids_file.extension == ".nii.gz"
        assert bids_file.suffix == "T1w"
        assert bids_file.entities["sub"] == "01"
        assert bids_file.entities["ses"] == "pre"
    
    def test_parse_bids_filename_ieeg(self, tmp_path):
        """Test parsing iEEG BIDS filename."""
        # Create a sample BIDS file
        filepath = tmp_path / "sub-02_task-rest_run-01_ieeg.edf"
        filepath.touch()
        
        loader = BidsLoader(tmp_path)
        bids_file = loader._parse_bids_filename(filepath, "ieeg")
        
        assert bids_file.modality == "ieeg"
        assert bids_file.extension == ".edf"
        assert bids_file.suffix == "ieeg"
        assert bids_file.entities["sub"] == "02"
        assert bids_file.entities["task"] == "rest"
        assert bids_file.entities["run"] == "01"


class TestBidsRepository:
    """Test cases for BidsRepository class."""
    
    def test_load_nonexistent_path(self):
        """Test loading from non-existent path raises FileNotFoundError."""
        repo = BidsRepository(Path("/nonexistent/path"))
        
        with pytest.raises(FileNotFoundError):
            repo.load()
    
    def test_load_invalid_bids_dataset(self, tmp_path):
        """Test loading invalid BIDS dataset raises ValueError."""
        # Create directory without dataset_description.json
        repo = BidsRepository(tmp_path)
        
        with pytest.raises(ValueError):
            repo.load()
    
    def test_load_minimal_bids_dataset(self, tmp_path):
        """Test loading a minimal valid BIDS dataset."""
        # Create minimal BIDS dataset structure
        dataset_desc = {
            "Name": "Minimal Dataset",
            "BIDSVersion": "1.8.0"
        }
        
        desc_file = tmp_path / "dataset_description.json"
        desc_file.write_text(json.dumps(dataset_desc))
        
        # Create a subject with an anatomical file
        sub_dir = tmp_path / "sub-01" / "anat"
        sub_dir.mkdir(parents=True)
        
        anat_file = sub_dir / "sub-01_T1w.nii.gz"
        anat_file.touch()
        
        # Load dataset
        repo = BidsRepository(tmp_path)
        dataset = repo.load()
        
        assert dataset.root_path == tmp_path
        assert len(dataset.subjects) == 1
        assert dataset.subjects[0].subject_id == "01"
        assert len(dataset.subjects[0].files) == 1
        assert dataset.dataset_description["Name"] == "Minimal Dataset"
    
    def test_load_dataset_with_sessions(self, tmp_path):
        """Test loading dataset with sessions."""
        # Create BIDS dataset with sessions
        dataset_desc = {
            "Name": "Session Dataset",
            "BIDSVersion": "1.8.0"
        }
        
        desc_file = tmp_path / "dataset_description.json"
        desc_file.write_text(json.dumps(dataset_desc))
        
        # Create subject with two sessions
        sub_dir = tmp_path / "sub-01"
        ses1_dir = sub_dir / "ses-pre" / "anat"
        ses2_dir = sub_dir / "ses-post" / "anat"
        ses1_dir.mkdir(parents=True)
        ses2_dir.mkdir(parents=True)
        
        (ses1_dir / "sub-01_ses-pre_T1w.nii.gz").touch()
        (ses2_dir / "sub-01_ses-post_T1w.nii.gz").touch()
        
        # Load dataset
        repo = BidsRepository(tmp_path)
        dataset = repo.load()
        
        assert len(dataset.subjects) == 1
        assert len(dataset.subjects[0].sessions) == 2
        assert dataset.subjects[0].sessions[0].session_id == "post"
        assert dataset.subjects[0].sessions[1].session_id == "pre"
    
    def test_load_dataset_with_participants_metadata(self, tmp_path):
        """Test loading dataset with participants.tsv metadata."""
        # Create BIDS dataset
        dataset_desc = {
            "Name": "Metadata Dataset",
            "BIDSVersion": "1.8.0"
        }
        
        desc_file = tmp_path / "dataset_description.json"
        desc_file.write_text(json.dumps(dataset_desc))
        
        # Create participants.tsv
        participants_content = "participant_id\tage\tsex\tgroup\n"
        participants_content += "sub-01\t25\tM\tcontrol\n"
        participants_content += "sub-02\t30\tF\tpatient\n"
        
        participants_file = tmp_path / "participants.tsv"
        participants_file.write_text(participants_content)
        
        # Create subjects
        sub1_dir = tmp_path / "sub-01" / "anat"
        sub2_dir = tmp_path / "sub-02" / "ieeg"
        sub1_dir.mkdir(parents=True)
        sub2_dir.mkdir(parents=True)
        
        (sub1_dir / "sub-01_T1w.nii.gz").touch()
        (sub2_dir / "sub-02_task-rest_ieeg.edf").touch()
        
        # Load dataset
        repo = BidsRepository(tmp_path)
        dataset = repo.load()
        
        assert len(dataset.subjects) == 2
        
        # Check metadata for subject 1
        assert dataset.subjects[0].metadata["age"] == "25"
        assert dataset.subjects[0].metadata["sex"] == "M"
        assert dataset.subjects[0].metadata["group"] == "control"
        
        # Check metadata for subject 2
        assert dataset.subjects[1].metadata["age"] == "30"
        assert dataset.subjects[1].metadata["sex"] == "F"
        assert dataset.subjects[1].metadata["group"] == "patient"
