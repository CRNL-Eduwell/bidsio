"""
Tests for export functionality.

Tests the core export logic, file generation, and entity matching.
"""

import pytest
import json
import shutil
from pathlib import Path

from src.bidsio.core.models import (
    BIDSDataset,
    BIDSSubject,
    BIDSSession,
    BIDSFile,
    BIDSDerivative,
    ExportRequest,
    SelectedEntities,
    ExportStats
)
from src.bidsio.core.export import (
    export_dataset,
    generate_file_list,
    calculate_export_stats,
    copy_file_tree,
    create_participants_tsv,
    _file_matches_entities
)


@pytest.fixture
def mock_bids_dataset(tmp_path):
    """Create a mock BIDS dataset on disk."""
    dataset_root = tmp_path / "test_dataset"
    dataset_root.mkdir()
    
    # Create dataset_description.json
    desc = {
        "Name": "Test Dataset",
        "BIDSVersion": "1.8.0",
        "Authors": ["Test Author"]
    }
    with open(dataset_root / "dataset_description.json", "w") as f:
        json.dump(desc, f)
    
    # Create participants.tsv
    with open(dataset_root / "participants.tsv", "w") as f:
        f.write("participant_id\tage\tsex\n")
        f.write("sub-01\t25\tM\n")
        f.write("sub-02\t30\tF\n")
    
    # Create subject directories and files
    for sub_id in ["01", "02"]:
        sub_dir = dataset_root / f"sub-{sub_id}"
        
        # Session structure
        for ses_id in ["pre", "post"]:
            ses_dir = sub_dir / f"ses-{ses_id}"
            
            # Anatomical files
            anat_dir = ses_dir / "anat"
            anat_dir.mkdir(parents=True)
            (anat_dir / f"sub-{sub_id}_ses-{ses_id}_T1w.nii.gz").write_text("mock nifti data")
            (anat_dir / f"sub-{sub_id}_ses-{ses_id}_T1w.json").write_text('{"EchoTime": 0.003}')
            
            # iEEG files with tasks and runs
            ieeg_dir = ses_dir / "ieeg"
            ieeg_dir.mkdir(parents=True)
            for task in ["rest", "task"]:
                for run in ["01", "02"]:
                    (ieeg_dir / f"sub-{sub_id}_ses-{ses_id}_task-{task}_run-{run}_ieeg.eeg").write_text("mock eeg data")
    
    return dataset_root


@pytest.fixture
def mock_bids_dataset_with_derivatives(mock_bids_dataset):
    """Add derivatives to the mock dataset."""
    dataset_root = mock_bids_dataset
    
    # Create derivatives structure
    deriv_root = dataset_root / "derivatives"
    
    for pipeline in ["pipeline1", "pipeline2"]:
        pipeline_dir = deriv_root / pipeline
        pipeline_dir.mkdir(parents=True)
        
        # Pipeline description
        pipeline_desc = {
            "Name": pipeline.title(),
            "BIDSVersion": "1.8.0",
            "PipelineDescription": {"Name": f"{pipeline} processing"},
            "GeneratedBy": [{"Name": pipeline, "Version": "1.0.0"}]
        }
        with open(pipeline_dir / "dataset_description.json", "w") as f:
            json.dump(pipeline_desc, f)
        
        # Subject data in derivatives
        for sub_id in ["01", "02"]:
            sub_deriv_dir = pipeline_dir / f"sub-{sub_id}"
            
            for ses_id in ["pre", "post"]:
                ses_deriv_dir = sub_deriv_dir / f"ses-{ses_id}"
                anat_dir = ses_deriv_dir / "anat"
                anat_dir.mkdir(parents=True)
                
                # Derivative files
                (anat_dir / f"sub-{sub_id}_ses-{ses_id}_space-MNI_T1w.nii.gz").write_text("normalized data")
                (anat_dir / f"sub-{sub_id}_ses-{ses_id}_desc-preproc_T1w.nii.gz").write_text("preprocessed data")
    
    return dataset_root


@pytest.fixture
def loaded_dataset(mock_bids_dataset):
    """Load the mock dataset into BIDSDataset model."""
    from src.bidsio.infrastructure.bids_loader import BidsLoader
    
    loader = BidsLoader(mock_bids_dataset)
    return loader.load()


@pytest.fixture
def loaded_dataset_with_derivatives(mock_bids_dataset_with_derivatives):
    """Load the mock dataset with derivatives."""
    from src.bidsio.infrastructure.bids_loader import BidsLoader
    
    loader = BidsLoader(mock_bids_dataset_with_derivatives)
    return loader.load()


class TestFileMatching:
    """Test entity matching logic."""
    
    def test_file_matches_all_entities(self):
        """Test that file matches when all entities are in selection."""
        file = BIDSFile(
            path=Path("/test/sub-01/ses-pre/ieeg/sub-01_ses-pre_task-rest_run-01_ieeg.eeg"),
            modality="ieeg",
            suffix="ieeg",
            extension=".eeg",
            entities={"task": "rest", "run": "01"}
        )
        
        selected = SelectedEntities(
            entities={"task": ["rest", "memory"], "run": ["01", "02"]},
            derivative_pipelines=[]
        )
        
        assert _file_matches_entities(file, "01", "pre", selected)
    
    def test_file_excluded_by_empty_entity_list(self):
        """Test that file is excluded when entity list is empty."""
        file = BIDSFile(
            path=Path("/test/sub-01/ses-pre/ieeg/sub-01_ses-pre_task-rest_ieeg.eeg"),
            modality="ieeg",
            suffix="ieeg",
            extension=".eeg",
            entities={"task": "rest"}
        )
        
        selected = SelectedEntities(
            entities={"task": []},  # Empty list means exclude all files with task entity
            derivative_pipelines=[]
        )
        
        assert not _file_matches_entities(file, "01", "pre", selected)
    
    def test_file_excluded_by_entity_value_not_in_list(self):
        """Test that file is excluded when its entity value is not selected."""
        file = BIDSFile(
            path=Path("/test/sub-01/ses-pre/ieeg/sub-01_ses-pre_task-rest_ieeg.eeg"),
            modality="ieeg",
            suffix="ieeg",
            extension=".eeg",
            entities={"task": "rest"}
        )
        
        selected = SelectedEntities(
            entities={"task": ["memory"]},  # Only 'memory' selected, not 'rest'
            derivative_pipelines=[]
        )
        
        assert not _file_matches_entities(file, "01", "pre", selected)
    
    def test_file_matches_when_entity_not_in_selection(self):
        """Test that file matches when it has entities not in selection criteria."""
        file = BIDSFile(
            path=Path("/test/sub-01/ses-pre/anat/sub-01_ses-pre_T1w.nii.gz"),
            modality="anat",
            suffix="T1w",
            extension=".nii.gz",
            entities={}
        )
        
        selected = SelectedEntities(
            entities={"task": ["rest"]},  # File has no task entity
            derivative_pipelines=[]
        )
        
        assert _file_matches_entities(file, "01", "pre", selected)
    
    def test_subject_filtering(self):
        """Test that subject filtering works correctly."""
        file = BIDSFile(
            path=Path("/test/sub-01/ses-pre/anat/sub-01_ses-pre_T1w.nii.gz"),
            modality="anat",
            suffix="T1w",
            extension=".nii.gz",
            entities={}
        )
        
        selected = SelectedEntities(
            entities={"sub": ["02"]},  # Only subject 02 selected
            derivative_pipelines=[]
        )
        
        assert not _file_matches_entities(file, "01", "pre", selected)
    
    def test_session_filtering(self):
        """Test that session filtering works correctly."""
        file = BIDSFile(
            path=Path("/test/sub-01/ses-pre/anat/sub-01_ses-pre_T1w.nii.gz"),
            modality="anat",
            suffix="T1w",
            extension=".nii.gz",
            entities={}
        )
        
        selected = SelectedEntities(
            entities={"ses": ["post"]},  # Only post session selected
            derivative_pipelines=[]
        )
        
        assert not _file_matches_entities(file, "01", "pre", selected)


class TestGenerateFileList:
    """Test file list generation."""
    
    def test_generate_all_files(self, loaded_dataset):
        """Test generating file list with all entities selected."""
        selected = SelectedEntities(
            entities={},
            derivative_pipelines=[]
        )
        
        files = generate_file_list(loaded_dataset, selected)
        
        # Should include all data files
        assert len(files) > 0
        # Check that files are Path objects
        assert all(isinstance(f, Path) for f in files)
    
    def test_generate_filtered_by_subject(self, loaded_dataset):
        """Test filtering by subject."""
        selected = SelectedEntities(
            entities={"sub": ["01"]},
            derivative_pipelines=[]
        )
        
        files = generate_file_list(loaded_dataset, selected)
        
        # All files should be from sub-01
        assert all("sub-01" in str(f) for f in files)
        assert not any("sub-02" in str(f) for f in files)
    
    def test_generate_filtered_by_session(self, loaded_dataset):
        """Test filtering by session."""
        selected = SelectedEntities(
            entities={"ses": ["pre"]},
            derivative_pipelines=[]
        )
        
        files = generate_file_list(loaded_dataset, selected)
        
        # All files should be from ses-pre
        assert all("ses-pre" in str(f) for f in files)
        assert not any("ses-post" in str(f) for f in files)
    
    def test_generate_filtered_by_task(self, loaded_dataset):
        """Test filtering by task."""
        selected = SelectedEntities(
            entities={"task": ["rest"]},
            derivative_pipelines=[]
        )
        
        files = generate_file_list(loaded_dataset, selected)
        
        # Should only include rest task files
        task_files = [f for f in files if "task-" in str(f)]
        assert all("task-rest" in str(f) for f in task_files)
        assert not any("task-task" in str(f) for f in task_files)


class TestCalculateStats:
    """Test export statistics calculation."""
    
    def test_calculate_stats_all_files(self, loaded_dataset):
        """Test statistics with all files selected."""
        selected = SelectedEntities(
            entities={},
            derivative_pipelines=[]
        )
        
        stats = calculate_export_stats(loaded_dataset, selected)
        
        assert isinstance(stats, ExportStats)
        assert stats.file_count > 0
        assert stats.total_size > 0
    
    def test_calculate_stats_filtered(self, loaded_dataset):
        """Test statistics with filtered selection."""
        # Select all
        selected_all = SelectedEntities(entities={}, derivative_pipelines=[])
        stats_all = calculate_export_stats(loaded_dataset, selected_all)
        
        # Select only one subject
        selected_one = SelectedEntities(entities={"sub": ["01"]}, derivative_pipelines=[])
        stats_one = calculate_export_stats(loaded_dataset, selected_one)
        
        # Filtered selection should have fewer files
        assert stats_one.file_count < stats_all.file_count
        assert stats_one.total_size < stats_all.total_size


class TestCopyFileTree:
    """Test file copying functionality."""
    
    def test_copy_single_file(self, tmp_path):
        """Test copying a single file."""
        source_root = tmp_path / "source"
        source_root.mkdir()
        
        dest_root = tmp_path / "dest"
        dest_root.mkdir()
        
        # Create source file
        test_file = source_root / "sub-01" / "anat" / "test.nii.gz"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test data")
        
        # Copy
        copy_file_tree([test_file], source_root, dest_root)
        
        # Verify
        dest_file = dest_root / "sub-01" / "anat" / "test.nii.gz"
        assert dest_file.exists()
        assert dest_file.read_text() == "test data"
    
    def test_copy_preserves_structure(self, tmp_path):
        """Test that directory structure is preserved."""
        source_root = tmp_path / "source"
        dest_root = tmp_path / "dest"
        
        # Create complex structure
        files = [
            source_root / "sub-01" / "ses-pre" / "anat" / "file1.nii.gz",
            source_root / "sub-01" / "ses-post" / "ieeg" / "file2.eeg",
            source_root / "sub-02" / "ses-pre" / "anat" / "file3.nii.gz",
        ]
        
        for f in files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("data")
        
        # Copy
        copy_file_tree(files, source_root, dest_root)
        
        # Verify all files exist with correct structure
        for f in files:
            rel_path = f.relative_to(source_root)
            dest_file = dest_root / rel_path
            assert dest_file.exists()


class TestCreateParticipantsTsv:
    """Test participants.tsv creation."""
    
    def test_create_filtered_participants(self, mock_bids_dataset, tmp_path):
        """Test creating filtered participants.tsv."""
        source_tsv = mock_bids_dataset / "participants.tsv"
        output_tsv = tmp_path / "participants.tsv"
        
        # Filter to only sub-01
        create_participants_tsv(source_tsv, ["01"], output_tsv)
        
        # Read and verify
        content = output_tsv.read_text()
        lines = content.strip().split("\n")
        
        assert len(lines) == 2  # Header + 1 subject
        assert "sub-01" in content
        assert "sub-02" not in content
    
    def test_create_all_participants(self, mock_bids_dataset, tmp_path):
        """Test creating participants.tsv with all subjects."""
        source_tsv = mock_bids_dataset / "participants.tsv"
        output_tsv = tmp_path / "participants.tsv"
        
        create_participants_tsv(source_tsv, ["01", "02"], output_tsv)
        
        content = output_tsv.read_text()
        lines = content.strip().split("\n")
        
        assert len(lines) == 3  # Header + 2 subjects
        assert "sub-01" in content
        assert "sub-02" in content


class TestExportDataset:
    """Test full dataset export."""
    
    def test_export_full_dataset(self, loaded_dataset, tmp_path):
        """Test exporting entire dataset."""
        output_path = tmp_path / "exported"
        
        request = ExportRequest(
            source_dataset=loaded_dataset,
            selected_entities=SelectedEntities(entities={}, derivative_pipelines=[]),
            output_path=output_path
        )
        
        result = export_dataset(request)
        
        # Verify output
        assert result == output_path
        assert output_path.exists()
        assert (output_path / "dataset_description.json").exists()
        
        # Check that subject directories exist
        assert (output_path / "sub-01").exists()
        assert (output_path / "sub-02").exists()
    
    def test_export_filtered_dataset(self, loaded_dataset, tmp_path):
        """Test exporting filtered dataset."""
        output_path = tmp_path / "exported"
        
        request = ExportRequest(
            source_dataset=loaded_dataset,
            selected_entities=SelectedEntities(
                entities={"sub": ["01"], "ses": ["pre"]},
                derivative_pipelines=[]
            ),
            output_path=output_path
        )
        
        result = export_dataset(request)
        
        # Verify filtering
        assert (output_path / "sub-01").exists()
        assert not (output_path / "sub-02").exists()
        
        # Check session filtering
        assert (output_path / "sub-01" / "ses-pre").exists()
        assert not (output_path / "sub-01" / "ses-post").exists()
    
    def test_export_with_derivatives(self, loaded_dataset_with_derivatives, tmp_path):
        """Test exporting dataset with derivatives."""
        output_path = tmp_path / "exported"
        
        request = ExportRequest(
            source_dataset=loaded_dataset_with_derivatives,
            selected_entities=SelectedEntities(
                entities={},
                derivative_pipelines=["pipeline1"]
            ),
            output_path=output_path
        )
        
        result = export_dataset(request)
        
        # Verify derivative structure
        assert (output_path / "derivatives" / "pipeline1").exists()
        assert (output_path / "derivatives" / "pipeline1" / "dataset_description.json").exists()
        
        # Verify derivative files
        derivative_files = list((output_path / "derivatives" / "pipeline1").rglob("*.nii.gz"))
        assert len(derivative_files) > 0
    
    def test_export_metadata_files(self, loaded_dataset, tmp_path):
        """Test that metadata files are copied."""
        output_path = tmp_path / "exported"
        
        request = ExportRequest(
            source_dataset=loaded_dataset,
            selected_entities=SelectedEntities(entities={}, derivative_pipelines=[]),
            output_path=output_path
        )
        
        export_dataset(request)
        
        # Check metadata files
        assert (output_path / "dataset_description.json").exists()
        
        # Verify content
        with open(output_path / "dataset_description.json") as f:
            desc = json.load(f)
            assert desc["Name"] == "Test Dataset"
    
    def test_export_no_files_raises_error(self, loaded_dataset, tmp_path):
        """Test that export raises error when no files match."""
        output_path = tmp_path / "exported"
        
        request = ExportRequest(
            source_dataset=loaded_dataset,
            selected_entities=SelectedEntities(
                entities={"sub": []},  # Empty selection
                derivative_pipelines=[]
            ),
            output_path=output_path
        )
        
        with pytest.raises(ValueError, match="No files match"):
            export_dataset(request)
