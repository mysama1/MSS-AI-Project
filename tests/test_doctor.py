"""
pytest tests for mssclaw doctor — 环境诊断
"""
import sys
sys.path.insert(0, '.')
import pytest
from mssclaw.core.doctor import (
    check_python, check_pip_packages, check_ollama,
    check_julia, check_disk, check_paths, run_diagnosis
)


class TestPythonCheck:
    def test_returns_version(self):
        result = check_python()
        assert 'version' in result
        assert '3.' in result['version']
        assert 'executable' in result


class TestPackageCheck:
    def test_finds_mssclaw(self):
        result = check_pip_packages()
        assert result['mss_agent'] is True
        assert 'mssclaw' in result['ok']

    def test_finds_pytest(self):
        result = check_pip_packages()
        assert 'pytest' in result['ok'], f"pytest missing: {result.get('missing', {})}"


class TestOllamaCheck:
    def test_service_running(self):
        result = check_ollama()
        assert result['service'] is True, f"Ollama not running: {result.get('error')}"

    def test_has_mss_models(self):
        result = check_ollama()
        assert len(result['mss_models']) > 0, "No MSS models found in Ollama"


class TestJuliaCheck:
    """Julia环境检查 (可能耗时)."""

    @pytest.mark.slow
    def test_installed(self):
        result = check_julia()
        assert result['installed'] is True

    @pytest.mark.slow
    def test_catlab_available(self):
        result = check_julia()
        assert result['catlab'] is True, f"Catlab not found: {result.get('error', '')}"


class TestDiskCheck:
    def test_finds_drives(self):
        result = check_disk()
        assert len(result) >= 1
        for drive, info in result.items():
            assert info['free_gb'] > 0


class TestPathsCheck:
    def test_project_exists(self):
        result = check_paths()
        assert result['project_root']['exists'] is True
        assert result['mssclaw_core']['exists'] is True


class TestFullDiagnosis:
    """完整诊断整合测试 (可能耗时)."""

    @pytest.mark.slow
    def test_returns_all_sections(self):
        result = run_diagnosis()
        for key in ['python', 'packages', 'ollama', 'julia', 'disk', 'paths', 'health']:
            assert key in result, f"Missing section: {key}"

    @pytest.mark.slow
    @pytest.mark.slow
    @pytest.mark.slow
    def test_health_score_valid(self):
        result = run_diagnosis()
        h = result['health']
        assert 0 <= h['score'] <= 1
        assert h['verdict'] in ['🟢 all clear', '🟡 some issues', '🔴 needs attention']
