#!/usr/bin/env python3
"""
MailSorter XPI Packaging Script

Creates a versioned .xpi file for Thunderbird extension distribution.
Validates the extension structure and updates version numbers.

Usage:
    python scripts/package_xpi.py [--version X.Y.Z] [--output DIR]
"""

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Project root
ROOT_DIR = Path(__file__).parent.parent
EXTENSION_DIR = ROOT_DIR / "extension"
DIST_DIR = ROOT_DIR / "dist"
BACKEND_VERSION_FILE = ROOT_DIR / "backend" / "__version__.py"
MANIFEST_FILE = EXTENSION_DIR / "manifest.json"

# Files/folders to exclude from XPI
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".DS_Store",
    "Thumbs.db",
    ".git",
    "*.map",
    "*.log",
]


def read_manifest_version() -> str:
    """Read current version from manifest.json."""
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    return manifest.get("version", "0.0.0")


def update_manifest_version(version: str) -> None:
    """Update version in manifest.json."""
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    manifest["version"] = version
    
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    
    print(f"✅ Updated manifest.json to version {version}")


def update_backend_version(version: str) -> None:
    """Update version in backend/__version__.py."""
    content = f'''"""
MailSorter Backend - Version and metadata
"""

__version__ = "{version}"
__author__ = "MailSorter Contributors"
__license__ = "MIT"
__description__ = (
    "LLM-powered email sorting for Thunderbird/Betterbird (Plan V5 compliant)"
)
'''
    with open(BACKEND_VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ Updated backend/__version__.py to version {version}")


def validate_semver(version: str) -> bool:
    """Validate semantic version format."""
    pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"
    return bool(re.match(pattern, version))


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from XPI."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*"):
            if path.name.endswith(pattern[1:]):
                return True
        elif pattern in path.parts:
            return True
        elif path.name == pattern:
            return True
    return False


def validate_extension() -> list[str]:
    """Validate extension structure. Returns list of errors."""
    errors = []
    
    # Check required files
    required_files = [
        "manifest.json",
        "background/background.js",
        "popup/popup.html",
        "options/options.html",
    ]
    
    for file in required_files:
        if not (EXTENSION_DIR / file).exists():
            errors.append(f"Missing required file: {file}")
    
    # Validate manifest.json
    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        required_keys = ["manifest_version", "name", "version", "permissions"]
        for key in required_keys:
            if key not in manifest:
                errors.append(f"manifest.json missing required key: {key}")
        
        # Check for debug settings that shouldn't be in production
        if manifest.get("developer", {}).get("name") == "debug":
            errors.append("manifest.json contains debug developer settings")
            
    except json.JSONDecodeError as e:
        errors.append(f"Invalid manifest.json: {e}")
    
    # Check icons exist
    if (EXTENSION_DIR / "icons").exists():
        icons_found = list((EXTENSION_DIR / "icons").glob("*.svg")) + \
                      list((EXTENSION_DIR / "icons").glob("*.png"))
        if not icons_found:
            errors.append("No icon files found in icons/")
    
    # Check locales
    locales_dir = EXTENSION_DIR / "_locales"
    if locales_dir.exists():
        for locale in ["en", "fr"]:
            locale_file = locales_dir / locale / "messages.json"
            if not locale_file.exists():
                errors.append(f"Missing locale file: _locales/{locale}/messages.json")
    
    return errors


def create_xpi(version: str, output_dir: Path) -> Path:
    """Create the XPI file. Returns path to created file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    xpi_name = f"mailsorter-{version}.xpi"
    xpi_path = output_dir / xpi_name
    
    # Remove existing file
    if xpi_path.exists():
        xpi_path.unlink()
    
    file_count = 0
    
    with zipfile.ZipFile(xpi_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(EXTENSION_DIR):
            root_path = Path(root)
            
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not should_exclude(root_path / d)]
            
            for file in files:
                file_path = root_path / file
                
                if should_exclude(file_path):
                    continue
                
                # Calculate archive path (relative to extension dir)
                arcname = file_path.relative_to(EXTENSION_DIR)
                zf.write(file_path, arcname)
                file_count += 1
    
    # Get file size
    size_kb = xpi_path.stat().st_size / 1024
    
    print(f"✅ Created {xpi_name} ({file_count} files, {size_kb:.1f} KB)")
    
    return xpi_path


def create_checksum(xpi_path: Path) -> Path:
    """Create SHA256 checksum file."""
    import hashlib
    
    sha256_hash = hashlib.sha256()
    with open(xpi_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    
    checksum = sha256_hash.hexdigest()
    checksum_file = xpi_path.with_suffix(".xpi.sha256")
    
    with open(checksum_file, "w") as f:
        f.write(f"{checksum}  {xpi_path.name}\n")
    
    print(f"✅ Created checksum: {checksum_file.name}")
    
    return checksum_file


def main():
    parser = argparse.ArgumentParser(
        description="Package MailSorter extension as XPI"
    )
    parser.add_argument(
        "--version", "-v",
        help="Version number (default: read from manifest.json)"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(DIST_DIR),
        help=f"Output directory (default: {DIST_DIR})"
    )
    parser.add_argument(
        "--update-version", "-u",
        action="store_true",
        help="Update version in manifest.json and backend/__version__.py"
    )
    parser.add_argument(
        "--no-checksum",
        action="store_true",
        help="Skip creating SHA256 checksum file"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate, don't create XPI"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("MailSorter XPI Packaging")
    print("=" * 50)
    print()
    
    # Determine version
    if args.version:
        version = args.version
        if not validate_semver(version):
            print(f"❌ Invalid version format: {version}")
            print("   Expected format: X.Y.Z or X.Y.Z-prerelease")
            sys.exit(1)
    else:
        version = read_manifest_version()
    
    print(f"📦 Version: {version}")
    print(f"📂 Extension: {EXTENSION_DIR}")
    print(f"📂 Output: {args.output}")
    print()
    
    # Validate extension
    print("Validating extension structure...")
    errors = validate_extension()
    
    if errors:
        print()
        print("❌ Validation errors:")
        for error in errors:
            print(f"   - {error}")
        sys.exit(1)
    
    print("✅ Extension structure valid")
    print()
    
    if args.validate_only:
        print("Validation complete (--validate-only)")
        return
    
    # Update versions if requested
    if args.update_version:
        print("Updating version numbers...")
        update_manifest_version(version)
        update_backend_version(version)
        print()
    
    # Create XPI
    print("Creating XPI package...")
    output_dir = Path(args.output)
    xpi_path = create_xpi(version, output_dir)
    
    # Create checksum
    if not args.no_checksum:
        create_checksum(xpi_path)
    
    print()
    print("=" * 50)
    print(f"✅ Package complete: {xpi_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
