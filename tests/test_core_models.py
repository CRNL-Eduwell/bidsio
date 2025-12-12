"""
Tests for core domain models.

These tests verify the behavior of data models in the core package.
"""

import pytest
from pathlib import Path

from src.bidsio.core.models import (
    BIDSFile,
    BIDSSession,
    BIDSSubject,
    BIDSDataset
)
from src.bidsio.core.export import (
    SelectedEntities,
    ExportRequest
)
from src.bidsio.infrastructure.bids_loader import BidsLoader


class TestBIDSFile:
    """Tests for BIDSFile model."""
    
    def test_create_bids_file(self):
        """Test creating a BIDSFile instance."""
        file = BIDSFile(
            path=Path("/data/sub-01/anat/sub-01_T1w.nii.gz"),
            modality="anat",
            suffix="T1w",
            extension=".nii.gz"
        )
        
        assert file.path == Path("/data/sub-01/anat/sub-01_T1w.nii.gz")
        assert file.modality == "anat"
        assert file.suffix == "T1w"
    
    def test_parse_entities_from_filename(self, tmp_path):
        """Test that BIDS filename parsing extracts entities correctly using BidsLoader."""
        # Create a fake BIDS file
        filepath = tmp_path / "sub-01_ses-pre_task-rest_run-01_bold.nii.gz"
        filepath.touch()

        loader = BidsLoader(tmp_path)
        bids_file = loader._parse_bids_filename(filepath, "func")

        assert bids_file.entities["sub"] == "01"
        assert bids_file.entities["ses"] == "pre"
        assert bids_file.entities["task"] == "rest"
        assert bids_file.entities["run"] == "01"

    def test_load_metadata_from_json_sidecar(self, tmp_path):
        """Test lazy metadata loading from JSON sidecar for a BIDSFile."""
        # Create directories
        anat_dir = tmp_path / "sub-01" / "anat"
        anat_dir.mkdir(parents=True)

        data_file = anat_dir / "sub-01_T1w.nii.gz"
        data_file.touch()

        # Create JSON sidecar
        json_sidecar = anat_dir / "sub-01_T1w.json"
        json_content = {"EchoTime": 0.003, "Manufacturer": "TestMaker"}
        import json
        with open(json_sidecar, 'w', encoding='utf-8') as f:
            json.dump(json_content, f)

        # Create BIDSFile and load metadata
        bids_file = BIDSFile(
            path=data_file,
            modality="anat",
            suffix="T1w",
            extension=".nii.gz",
            entities={"sub": "01"}
        )

        assert bids_file.metadata is None
        loaded = bids_file.load_metadata()
        assert loaded is not None
        assert loaded.get("EchoTime") == 0.003


class TestBIDSSubject:
    """Tests for BIDSSubject model."""
    
    def test_create_subject(self):
        """Test creating a BIDSSubject instance."""
        subject = BIDSSubject(subject_id="01")
        assert subject.subject_id == "01"
        assert len(subject.sessions) == 0
        assert len(subject.files) == 0
    
    def test_add_sessions_and_files(self):
        """Test adding sessions and files to a BIDSSubject."""
        subject = BIDSSubject(subject_id="01")
        assert len(subject.sessions) == 0
        assert len(subject.files) == 0

        # Add a session
        ses = BIDSSession(session_id="pre")
        subject.sessions.append(ses)
        assert len(subject.sessions) == 1

        # Add a file at subject-level
        file = BIDSFile(path=Path("/tmp/sub-01/file.tsv"), modality=None, suffix=None, extension=".tsv", entities={})
        subject.files.append(file)
        assert len(subject.files) == 1


class TestBIDSDataset:
    """Tests for BIDSDataset model."""
    
    def test_create_dataset(self):
        """Test creating a BIDSDataset instance."""
        dataset = BIDSDataset(root_path=Path("/data"))
        assert dataset.root_path == Path("/data")
        assert len(dataset.subjects) == 0
    
    def test_get_subject(self):
        """Test retrieving a subject by ID."""
        dataset = BIDSDataset(root_path=Path("/data"))
        subject1 = BIDSSubject(subject_id="01")
        subject2 = BIDSSubject(subject_id="02")
        dataset.subjects = [subject1, subject2]
        
        found = dataset.get_subject("01")
        assert found is not None
        assert found.subject_id == "01"
        
        not_found = dataset.get_subject("03")
        assert not_found is None
    
    def test_get_all_modalities_and_tasks(self):
        """Test retrieval of all modalities and tasks in a BIDSDataset."""
        dataset = BIDSDataset(root_path=Path("/data"))

        # Subject 1 with anat and func files
        s1 = BIDSSubject(subject_id="01")
        s1.files.append(BIDSFile(path=Path("/data/sub-01/anat/sub-01_T1w.nii.gz"), modality="anat", suffix="T1w", extension=".nii.gz", entities={"sub": "01"}))
        func_file = BIDSFile(path=Path("/data/sub-01/func/sub-01_task-rest_bold.nii.gz"), modality="func", suffix="bold", extension=".nii.gz", entities={"sub": "01", "task": "rest"})
        s1.sessions.append(BIDSSession(session_id="pre", files=[func_file]))

        # Subject 2 with dwi
        s2 = BIDSSubject(subject_id="02")
        s2.files.append(BIDSFile(path=Path("/data/sub-02/dwi/sub-02_dwi.nii.gz"), modality="dwi", suffix="dwi", extension=".nii.gz", entities={"sub": "02"}))

        dataset.subjects = [s1, s2]

        modalities = dataset.get_all_modalities()
        tasks = dataset.get_all_tasks()

        assert modalities == {"anat", "func", "dwi"}
        assert tasks == {"rest"}


class TestExportRequest:
    """Tests for ExportRequest model."""
    
    def test_create_export_request(self):
        """Test creating an ExportRequest."""
        dataset = BIDSDataset(root_path=Path("/data"))
        selected = SelectedEntities(entities={"sub": ["01"]}, derivative_pipelines=[])
        
        request = ExportRequest(
            source_dataset=dataset,
            selected_entities=selected,
            output_path=Path("/output")
        )
        
        assert request.source_dataset == dataset
        assert request.selected_entities == selected
        assert request.output_path == Path("/output")
        assert request.overwrite == False
    
    def test_selected_entities_defaults_and_export_request(self):
        """Test SelectedEntities defaults and basic ExportRequest creation."""
        dataset = BIDSDataset(root_path=Path("/data"))
        selected = SelectedEntities()
        assert selected.entities == {}
        assert selected.derivative_pipelines == []

        request = ExportRequest(source_dataset=dataset, selected_entities=selected, output_path=Path("/output"))
        assert request.source_dataset == dataset
        assert request.selected_entities == selected
        assert request.output_path == Path("/output")
        assert request.overwrite is False
