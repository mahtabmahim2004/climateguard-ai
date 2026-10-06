from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def test_windows_batch_launcher_uses_project_runtime_and_existing_app() -> None:
    launcher = (SCRIPTS_DIR / "start_climateguard.bat").read_text(encoding="utf-8")
    normalized = launcher.lower()
    assert 'for %%i in ("%~dp0..")' in normalized
    assert r"\.venv\scripts\python.exe" in normalized
    assert 'set "pythonpath=src"' in normalized
    assert "-m climateguard.webapp" in normalized
    assert "http://127.0.0.1:8000" in normalized
    assert "/api/health" in normalized
    assert "pip install" not in normalized
    assert "python -m venv" not in normalized
    assert "train_baseline_models" not in normalized


def test_hidden_launcher_and_desktop_shortcut_are_repository_relative() -> None:
    hidden_launcher = (SCRIPTS_DIR / "start_climateguard_hidden.vbs").read_text(encoding="utf-8")
    shortcut_creator = (SCRIPTS_DIR / "create_climateguard_shortcut.vbs").read_text(encoding="utf-8")
    assert "GetParentFolderName(WScript.ScriptFullName)" in hidden_launcher
    assert 'shell.Run """" & batchPath & """", 0, False' in hidden_launcher
    assert 'shell.SpecialFolders("Desktop")' in shortcut_creator
    assert '"ClimateGuard AI.lnk"' in shortcut_creator
    assert "start_climateguard_hidden.vbs" in shortcut_creator
