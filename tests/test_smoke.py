from climateguard.config import DATA_DIR, PROJECT_ROOT, SRC_DIR
from climateguard.data.loader import list_data_files


def test_project_structure_exists() -> None:
    assert PROJECT_ROOT.exists()
    assert SRC_DIR.exists()
    assert DATA_DIR.exists()
    assert (PROJECT_ROOT / "tests").exists()


def test_loader_returns_list() -> None:
    files = list_data_files(DATA_DIR)
    assert isinstance(files, list)
