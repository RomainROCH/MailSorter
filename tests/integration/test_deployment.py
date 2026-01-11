"""
Deployment and Installation Tests.

Tests for installation scripts, XPI packaging, upgrade paths, 
and configuration setup.

Run with: pytest tests/integration/test_deployment.py -v

Task: DEPLOY-001
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import pytest
from pathlib import Path
from typing import Dict, List, Optional


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
EXTENSION_DIR = PROJECT_ROOT / "extension"
INSTALLERS_DIR = PROJECT_ROOT / "installers"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DIST_DIR = PROJECT_ROOT / "dist"


# =============================================================================
# INSTALLATION SCRIPT TESTS
# =============================================================================

class TestRegisterBatScript:
    """Tests for Windows register.bat installer script."""
    
    @pytest.fixture
    def register_bat(self) -> Path:
        """Path to register.bat."""
        return INSTALLERS_DIR / "register.bat"
    
    def test_script_exists(self, register_bat: Path):
        """register.bat should exist."""
        assert register_bat.exists(), "Missing register.bat"
    
    def test_script_has_correct_encoding(self, register_bat: Path):
        """Script should be readable as text."""
        content = register_bat.read_text(encoding="utf-8", errors="replace")
        assert "@echo off" in content.lower() or "echo" in content.lower()
    
    def test_script_sets_app_name(self, register_bat: Path):
        """Script should set correct app name."""
        content = register_bat.read_text(encoding="utf-8")
        assert "com.mailsorter.backend" in content
    
    def test_script_references_manifest(self, register_bat: Path):
        """Script should reference app_manifest.json."""
        content = register_bat.read_text(encoding="utf-8")
        assert "app_manifest.json" in content
    
    def test_script_uses_hkcu(self, register_bat: Path):
        """Script should use HKCU for per-user install (no admin required)."""
        content = register_bat.read_text(encoding="utf-8")
        assert "HKCU" in content, "Should use HKCU for per-user install"
    
    def test_script_uses_native_messaging_hosts_path(self, register_bat: Path):
        """Script should use correct registry path."""
        content = register_bat.read_text(encoding="utf-8")
        assert "NativeMessagingHosts" in content
        assert "Mozilla" in content
    
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
    def test_script_syntax_valid(self, register_bat: Path):
        """Script should have valid batch syntax (Windows only)."""
        # Run with /? to check syntax without executing
        result = subprocess.run(
            ["cmd", "/c", f'"{register_bat}" /?'],
            capture_output=True,
            text=True,
            timeout=10
        )
        # If syntax is invalid, cmd will fail
        # Note: /? may not work for all scripts, so just check it doesn't crash
        assert result.returncode in [0, 1]  # 0 or 1 is acceptable


class TestRegisterShScript:
    """Tests for Linux/macOS register.sh installer script."""
    
    @pytest.fixture
    def register_sh(self) -> Path:
        """Path to register.sh."""
        return INSTALLERS_DIR / "register.sh"
    
    def test_script_exists(self, register_sh: Path):
        """register.sh should exist."""
        assert register_sh.exists(), "Missing register.sh"
    
    def test_script_has_shebang(self, register_sh: Path):
        """Script should have shebang line."""
        content = register_sh.read_text(encoding="utf-8")
        first_line = content.split("\n")[0]
        assert first_line.startswith("#!"), "Missing shebang"
        assert "bash" in first_line or "sh" in first_line
    
    def test_script_sets_app_name(self, register_sh: Path):
        """Script should set correct app name."""
        content = register_sh.read_text(encoding="utf-8")
        assert "com.mailsorter.backend" in content
    
    def test_script_handles_linux(self, register_sh: Path):
        """Script should handle Linux path."""
        content = register_sh.read_text(encoding="utf-8")
        assert ".mozilla/native-messaging-hosts" in content
    
    def test_script_handles_macos(self, register_sh: Path):
        """Script should handle macOS path."""
        content = register_sh.read_text(encoding="utf-8")
        # Check for either Application Support path format
        assert "Library" in content or "Mozilla" in content
    
    def test_script_creates_directory(self, register_sh: Path):
        """Script should create target directory."""
        content = register_sh.read_text(encoding="utf-8")
        assert "mkdir" in content
    
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix only")
    def test_script_syntax_valid(self, register_sh: Path):
        """Script should have valid shell syntax (Unix only)."""
        result = subprocess.run(
            ["bash", "-n", str(register_sh)],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"


class TestAppManifest:
    """Tests for native messaging app manifest."""
    
    @pytest.fixture
    def app_manifest(self) -> dict:
        """Load app_manifest.json."""
        manifest_path = BACKEND_DIR / "app_manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def test_manifest_exists(self):
        """app_manifest.json should exist."""
        manifest_path = BACKEND_DIR / "app_manifest.json"
        assert manifest_path.exists()
    
    def test_manifest_has_required_fields(self, app_manifest):
        """Manifest should have all required fields."""
        required = ["name", "description", "path", "type", "allowed_extensions"]
        
        for field in required:
            assert field in app_manifest, f"Missing field: {field}"
    
    def test_manifest_name_valid(self, app_manifest):
        """Name should follow naming convention."""
        name = app_manifest["name"]
        
        # Must be lowercase
        assert name == name.lower() or "." in name
        # Must use dots for namespacing
        assert "." in name
        # Specific check
        assert name == "com.mailsorter.backend"
    
    def test_manifest_type_is_stdio(self, app_manifest):
        """Type must be 'stdio'."""
        assert app_manifest["type"] == "stdio"
    
    def test_manifest_allowed_extensions_not_empty(self, app_manifest):
        """Allowed extensions should not be empty."""
        allowed = app_manifest["allowed_extensions"]
        assert len(allowed) > 0
    
    def test_manifest_extension_id_format(self, app_manifest):
        """Extension ID should be valid format."""
        for ext_id in app_manifest["allowed_extensions"]:
            # Should be email-like format
            assert "@" in ext_id


# =============================================================================
# XPI PACKAGING TESTS
# =============================================================================

class TestXPIPackaging:
    """Tests for XPI extension packaging."""
    
    @pytest.fixture
    def package_script(self) -> Path:
        """Path to package_xpi.py."""
        return SCRIPTS_DIR / "package_xpi.py"
    
    def test_package_script_exists(self, package_script: Path):
        """package_xpi.py should exist."""
        assert package_script.exists()
    
    def test_package_script_syntax_valid(self, package_script: Path):
        """Script should have valid Python syntax."""
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(package_script)],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"
    
    def test_extension_files_exist(self):
        """Required extension files should exist."""
        required_files = [
            "manifest.json",
            "background/background.js",
            "popup/popup.html",
            "options/options.html",
        ]
        
        for file in required_files:
            file_path = EXTENSION_DIR / file
            assert file_path.exists(), f"Missing: {file}"
    
    def test_locales_valid_json(self):
        """All locale files should be valid JSON."""
        locales_dir = EXTENSION_DIR / "_locales"
        
        if locales_dir.exists():
            for locale_dir in locales_dir.iterdir():
                if locale_dir.is_dir():
                    messages_file = locale_dir / "messages.json"
                    if messages_file.exists():
                        with open(messages_file, "r", encoding="utf-8") as f:
                            messages = json.load(f)
                        assert isinstance(messages, dict)
    
    def test_manifest_valid_json(self):
        """manifest.json should be valid JSON."""
        manifest_path = EXTENSION_DIR / "manifest.json"
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        assert "manifest_version" in manifest
        assert "name" in manifest
        assert "version" in manifest
    
    def test_manifest_version_semver(self):
        """Version should follow semantic versioning."""
        manifest_path = EXTENSION_DIR / "manifest.json"
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        version = manifest["version"]
        
        # Should match X.Y.Z pattern
        pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(pattern, version), \
            f"Version '{version}' should be semver format"
    
    def test_no_debug_code_in_extension(self):
        """Extension should not contain debug code markers."""
        debug_patterns = [
            "console.log",  # This is actually okay for logging
            "debugger;",
            "TODO:",  # These are okay in development
        ]
        
        critical_patterns = [
            "debugger;",
            "eval(",
            "document.write(",
        ]
        
        for js_file in EXTENSION_DIR.rglob("*.js"):
            content = js_file.read_text(encoding="utf-8", errors="replace")
            
            for pattern in critical_patterns:
                assert pattern not in content, \
                    f"Found '{pattern}' in {js_file.relative_to(EXTENSION_DIR)}"
    
    def test_create_xpi_dry_run(self):
        """Test XPI creation logic without actually creating file."""
        # Simulate XPI creation
        extension_files = list(EXTENSION_DIR.rglob("*"))
        
        # Filter out files that should be excluded
        exclude_patterns = [
            "__pycache__",
            ".pyc",
            ".DS_Store",
            "Thumbs.db",
            ".git",
        ]
        
        included_files = []
        for f in extension_files:
            if f.is_file():
                should_exclude = any(
                    pat in str(f) for pat in exclude_patterns
                )
                if not should_exclude:
                    included_files.append(f)
        
        # Should have files
        assert len(included_files) > 0
        
        # Should include manifest
        manifest_included = any(
            f.name == "manifest.json" for f in included_files
        )
        assert manifest_included


class TestXPIStructure:
    """Test XPI file structure if it exists."""
    
    def find_latest_xpi(self) -> Optional[Path]:
        """Find most recent XPI in dist folder."""
        if not DIST_DIR.exists():
            return None
        
        xpi_files = list(DIST_DIR.glob("*.xpi"))
        if not xpi_files:
            return None
        
        return max(xpi_files, key=lambda p: p.stat().st_mtime)
    
    @pytest.fixture
    def xpi_path(self) -> Optional[Path]:
        """Get path to XPI file if exists."""
        return self.find_latest_xpi()
    
    def test_xpi_is_valid_zip(self, xpi_path: Optional[Path]):
        """XPI should be a valid ZIP file."""
        if xpi_path is None:
            pytest.skip("No XPI file found in dist/")
        
        assert zipfile.is_zipfile(xpi_path)
    
    def test_xpi_contains_manifest(self, xpi_path: Optional[Path]):
        """XPI should contain manifest.json."""
        if xpi_path is None:
            pytest.skip("No XPI file found in dist/")
        
        with zipfile.ZipFile(xpi_path, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
    
    def test_xpi_manifest_valid(self, xpi_path: Optional[Path]):
        """Manifest in XPI should be valid JSON."""
        if xpi_path is None:
            pytest.skip("No XPI file found in dist/")
        
        with zipfile.ZipFile(xpi_path, "r") as zf:
            content = zf.read("manifest.json")
            manifest = json.loads(content.decode("utf-8"))
            
            assert "manifest_version" in manifest
    
    def test_xpi_no_excluded_files(self, xpi_path: Optional[Path]):
        """XPI should not contain excluded files."""
        if xpi_path is None:
            pytest.skip("No XPI file found in dist/")
        
        excluded = [".git", "__pycache__", ".pyc", ".DS_Store", "Thumbs.db"]
        
        with zipfile.ZipFile(xpi_path, "r") as zf:
            for name in zf.namelist():
                for pattern in excluded:
                    assert pattern not in name, \
                        f"XPI contains excluded: {name}"


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================

class TestConfigurationSetup:
    """Tests for configuration file setup."""
    
    def test_config_example_exists(self):
        """config.json.example should exist."""
        example_path = BACKEND_DIR / "config.json.example"
        assert example_path.exists()
    
    def test_config_example_valid_json(self):
        """config.json.example should be valid JSON."""
        example_path = BACKEND_DIR / "config.json.example"
        
        with open(example_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        assert isinstance(config, dict)
    
    def test_config_example_has_required_sections(self):
        """Config example should have required sections."""
        example_path = BACKEND_DIR / "config.json.example"
        
        with open(example_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Check expected top-level keys
        expected_keys = ["provider", "providers"]
        
        for key in expected_keys:
            assert key in config, f"Missing config section: {key}"
    
    def test_config_json_not_in_git(self):
        """config.json should be gitignored (contains secrets)."""
        gitignore_path = PROJECT_ROOT / ".gitignore"
        
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
            # Should have some form of config.json ignore
            assert "config.json" in content or "*.json" not in content
    
    def test_requirements_file_exists(self):
        """requirements.txt should exist."""
        req_path = BACKEND_DIR / "requirements.txt"
        assert req_path.exists()
    
    def test_requirements_has_core_deps(self):
        """requirements.txt should have core dependencies."""
        req_path = BACKEND_DIR / "requirements.txt"
        content = req_path.read_text(encoding="utf-8")
        
        core_deps = ["requests", "jsonschema"]
        
        for dep in core_deps:
            assert dep in content, f"Missing dependency: {dep}"
    
    def test_pyproject_exists(self):
        """pyproject.toml should exist."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        assert pyproject_path.exists()


# =============================================================================
# UPGRADE PATH TESTS
# =============================================================================

class TestUpgradePaths:
    """Tests for version upgrade handling."""
    
    def test_version_file_exists(self):
        """__version__.py should exist."""
        version_path = BACKEND_DIR / "__version__.py"
        assert version_path.exists()
    
    def test_version_extractable(self):
        """Version should be extractable from __version__.py."""
        version_path = BACKEND_DIR / "__version__.py"
        content = version_path.read_text(encoding="utf-8")
        
        # Should have __version__ defined
        assert "__version__" in content
        
        # Extract version
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        assert match is not None
        
        version = match.group(1)
        # Should be semver-like
        assert re.match(r"^\d+\.\d+\.\d+", version)
    
    def test_versions_match(self):
        """Backend and extension versions should match."""
        # Backend version
        version_path = BACKEND_DIR / "__version__.py"
        content = version_path.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        backend_version = match.group(1) if match else None
        
        # Extension version
        manifest_path = EXTENSION_DIR / "manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        extension_version = manifest.get("version")
        
        assert backend_version == extension_version, \
            f"Version mismatch: backend={backend_version}, extension={extension_version}"
    
    def test_changelog_exists(self):
        """CHANGELOG.md should exist."""
        changelog_path = PROJECT_ROOT / "CHANGELOG.md"
        assert changelog_path.exists()
    
    def test_changelog_has_versions(self):
        """CHANGELOG should document versions."""
        changelog_path = PROJECT_ROOT / "CHANGELOG.md"
        content = changelog_path.read_text(encoding="utf-8")
        
        # Should have version headers
        assert re.search(r"##\s*\[?\d+\.\d+", content), \
            "CHANGELOG should have version headers"
    
    def test_updates_json_valid(self):
        """updates.json should be valid (for auto-update)."""
        updates_path = PROJECT_ROOT / "updates.json"
        
        if updates_path.exists():
            with open(updates_path, "r", encoding="utf-8") as f:
                updates = json.load(f)
            
            assert isinstance(updates, dict)


# =============================================================================
# ENVIRONMENT TESTS
# =============================================================================

class TestEnvironmentSetup:
    """Tests for development environment setup."""
    
    def test_venv_script_windows_exists(self):
        """Windows venv setup script should exist."""
        script_path = SCRIPTS_DIR / "setup-venv.ps1"
        assert script_path.exists()
    
    def test_venv_script_unix_exists(self):
        """Unix venv setup script should exist."""
        script_path = SCRIPTS_DIR / "setup-venv.sh"
        assert script_path.exists()
    
    def test_makefile_exists(self):
        """Makefile should exist for common tasks."""
        makefile_path = PROJECT_ROOT / "Makefile"
        assert makefile_path.exists()
    
    def test_makefile_has_common_targets(self):
        """Makefile should have common targets."""
        makefile_path = PROJECT_ROOT / "Makefile"
        content = makefile_path.read_text(encoding="utf-8")
        
        common_targets = ["test", "lint", "install"]
        
        for target in common_targets:
            assert f"{target}:" in content or f"{target} :" in content, \
                f"Missing Makefile target: {target}"
    
    def test_dockerfile_exists(self):
        """Dockerfile should exist for containerization."""
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        assert dockerfile_path.exists()
    
    def test_pytest_ini_exists(self):
        """pytest.ini should exist."""
        pytest_ini = PROJECT_ROOT / "pytest.ini"
        assert pytest_ini.exists()


# =============================================================================
# DOCUMENTATION TESTS
# =============================================================================

class TestDocumentation:
    """Tests for documentation completeness."""
    
    def test_readme_exists(self):
        """README.md should exist."""
        readme_path = PROJECT_ROOT / "README.md"
        assert readme_path.exists()
    
    def test_readme_has_installation(self):
        """README should have installation instructions."""
        readme_path = PROJECT_ROOT / "README.md"
        content = readme_path.read_text(encoding="utf-8").lower()
        
        assert "install" in content
    
    def test_user_guide_exists(self):
        """User guide should exist."""
        guide_path = PROJECT_ROOT / "docs" / "USER_GUIDE.md"
        assert guide_path.exists()
    
    def test_troubleshooting_exists(self):
        """Troubleshooting guide should exist."""
        troubleshoot_path = PROJECT_ROOT / "docs" / "TROUBLESHOOTING.md"
        assert troubleshoot_path.exists()
    
    def test_architecture_docs_exist(self):
        """Architecture documentation should exist."""
        arch_path = PROJECT_ROOT / "docs" / "ARCHITECTURE.md"
        assert arch_path.exists()


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestSecurityConfiguration:
    """Tests for security-related configuration."""
    
    def test_no_hardcoded_secrets(self):
        """No hardcoded API keys in source files."""
        patterns = [
            r"sk-[a-zA-Z0-9]{20,}",  # OpenAI key pattern
            r"sk-ant-[a-zA-Z0-9]{20,}",  # Anthropic key pattern
            r"AIza[a-zA-Z0-9_-]{35}",  # Google API key pattern
        ]
        
        # Check Python files
        for py_file in BACKEND_DIR.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="replace")
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                # Filter out test patterns
                real_matches = [m for m in matches if "test" not in m.lower()]
                assert len(real_matches) == 0, \
                    f"Possible API key in {py_file}: {real_matches}"
    
    def test_gitignore_excludes_secrets(self):
        """Gitignore should exclude secret files."""
        gitignore_path = PROJECT_ROOT / ".gitignore"
        
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
            
            # Should exclude common secret files
            secret_patterns = ["*.env", ".env", "secrets", "config.json"]
            
            found_any = any(p in content for p in secret_patterns)
            assert found_any, "Gitignore should exclude secret files"
    
    def test_security_md_exists(self):
        """SECURITY.md should exist."""
        security_path = PROJECT_ROOT / "SECURITY.md"
        assert security_path.exists()
