#!/usr/bin/env python3
"""
MailSorter Update Manifest Generator

Generates and updates the updates.json file for Thunderbird extension
automatic updates.

Usage:
    python scripts/update_manifest.py --version 1.0.0 --xpi-url URL --xpi-hash HASH
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
UPDATES_FILE = ROOT_DIR / "updates.json"
EXTENSION_ID = "mailsorter@planv5.local"
MIN_TB_VERSION = "115.0"


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def calculate_sha256_url(url: str) -> str:
    """Calculate SHA256 hash of a file from URL."""
    sha256_hash = hashlib.sha256()
    with urllib.request.urlopen(url) as response:
        for chunk in iter(lambda: response.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def load_updates() -> dict:
    """Load existing updates.json or create new structure."""
    if UPDATES_FILE.exists():
        with open(UPDATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"addons": {EXTENSION_ID: {"updates": []}}}


def save_updates(data: dict) -> None:
    """Save updates.json."""
    with open(UPDATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def add_update(
    version: str, xpi_url: str, xpi_hash: str, min_version: str = MIN_TB_VERSION
) -> None:
    """Add a new version to updates.json."""
    data = load_updates()

    updates = data["addons"][EXTENSION_ID]["updates"]

    # Check if version already exists
    for update in updates:
        if update["version"] == version:
            print(f"⚠️  Version {version} already exists, updating...")
            update["update_link"] = xpi_url
            update["update_hash"] = f"sha256:{xpi_hash}"
            update["browser_specific_settings"]["gecko"][
                "strict_min_version"
            ] = min_version
            save_updates(data)
            print(f"✅ Updated version {version}")
            return

    # Add new version
    new_update = {
        "version": version,
        "update_link": xpi_url,
        "update_hash": f"sha256:{xpi_hash}",
        "browser_specific_settings": {"gecko": {"strict_min_version": min_version}},
    }

    # Insert at the beginning (newest first)
    updates.insert(0, new_update)

    # Keep only last 10 versions
    data["addons"][EXTENSION_ID]["updates"] = updates[:10]

    save_updates(data)
    print(f"✅ Added version {version} to updates.json")


def list_versions() -> None:
    """List all versions in updates.json."""
    data = load_updates()
    updates = data["addons"][EXTENSION_ID]["updates"]

    if not updates:
        print("No versions found in updates.json")
        return

    print("Available versions:")
    for update in updates:
        print(f"  - {update['version']}: {update['update_link']}")


def main():
    parser = argparse.ArgumentParser(description="Manage MailSorter update manifest")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add version command
    add_parser = subparsers.add_parser("add", help="Add a new version")
    add_parser.add_argument("--version", "-v", required=True, help="Version number")
    add_parser.add_argument("--xpi-url", required=True, help="URL to the XPI file")
    add_parser.add_argument(
        "--xpi-hash", help="SHA256 hash (calculated if not provided)"
    )
    add_parser.add_argument("--xpi-file", help="Local XPI file to calculate hash from")
    add_parser.add_argument(
        "--min-version", default=MIN_TB_VERSION, help="Minimum TB version"
    )

    # List command
    subparsers.add_parser("list", help="List all versions")

    # Legacy mode (for backward compatibility)
    parser.add_argument("--version", help="Version number (legacy mode)")
    parser.add_argument("--xpi-url", help="URL to the XPI file (legacy mode)")
    parser.add_argument("--xpi-hash", help="SHA256 hash (legacy mode)")

    args = parser.parse_args()

    # Handle legacy mode
    if args.version and args.xpi_url:
        xpi_hash = args.xpi_hash
        if not xpi_hash:
            print("❌ --xpi-hash is required")
            sys.exit(1)
        add_update(args.version, args.xpi_url, xpi_hash)
        return

    if args.command == "add":
        xpi_hash = args.xpi_hash

        # Calculate hash if not provided
        if not xpi_hash:
            if args.xpi_file:
                xpi_hash = calculate_sha256(Path(args.xpi_file))
                print(f"📋 Calculated hash from file: {xpi_hash}")
            else:
                print("Calculating hash from URL (this may take a moment)...")
                try:
                    xpi_hash = calculate_sha256_url(args.xpi_url)
                    print(f"📋 Calculated hash from URL: {xpi_hash}")
                except Exception as e:
                    print(f"❌ Could not calculate hash: {e}")
                    print("   Provide --xpi-hash or --xpi-file")
                    sys.exit(1)

        add_update(args.version, args.xpi_url, xpi_hash, args.min_version)

    elif args.command == "list":
        list_versions()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
