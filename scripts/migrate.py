#!/usr/bin/env python3
"""
MailSorter Migration Scripts

Handles configuration and data migrations between versions.
Run automatically during startup or manually via CLI.

Usage:
    python scripts/migrate.py [--from VERSION] [--to VERSION] [--dry-run]
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

ROOT_DIR = Path(__file__).parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
CONFIG_FILE = BACKEND_DIR / "config.json"
CONFIG_BACKUP_DIR = BACKEND_DIR / "config_backups"


# Migration registry: (from_version, to_version) -> migration_function
MIGRATIONS: dict[tuple[str, str], Callable[[dict], dict]] = {}


def register_migration(from_version: str, to_version: str):
    """Decorator to register a migration function."""

    def decorator(func: Callable[[dict], dict]):
        MIGRATIONS[(from_version, to_version)] = func
        return func

    return decorator


def version_tuple(version: str) -> tuple[int, ...]:
    """Convert version string to tuple for comparison."""
    # Remove prerelease suffix for comparison
    base = version.split("-")[0]
    return tuple(int(x) for x in base.split("."))


def backup_config(config_path: Path) -> Path:
    """Create a backup of the config file."""
    if not config_path.exists():
        return None

    CONFIG_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"config_{timestamp}.json"
    backup_path = CONFIG_BACKUP_DIR / backup_name

    shutil.copy2(config_path, backup_path)
    print(f"📦 Backed up config to {backup_path}")

    return backup_path


def load_config() -> dict:
    """Load current config file."""
    if not CONFIG_FILE.exists():
        return {}

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """Save config file."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_config_version(config: dict) -> str:
    """Get version from config, or '0.0.0' if not present."""
    return config.get("_version", "0.0.0")


# ============================================================================
# Migration Functions
# ============================================================================


@register_migration("0.1.0", "0.2.0")
def migrate_0_1_to_0_2(config: dict) -> dict:
    """
    Migration from 0.1.0 to 0.2.0:
    - Rename 'ollama_url' to 'providers.ollama.url'
    - Add provider selection
    """
    # Move ollama config to provider structure
    if "ollama_url" in config:
        providers = config.get("providers", {})
        providers["ollama"] = {
            "url": config.pop("ollama_url"),
            "model": config.pop("ollama_model", "llama3"),
        }
        config["providers"] = providers

    # Set default provider
    if "provider" not in config:
        config["provider"] = "ollama"

    return config


@register_migration("0.2.0", "1.0.0")
def migrate_0_2_to_1_0(config: dict) -> dict:
    """
    Migration from 0.2.0 to 1.0.0:
    - Add thresholds structure if missing
    - Add privacy settings
    - Add rate limiting defaults
    """
    # Ensure thresholds exist
    if "thresholds" not in config:
        config["thresholds"] = {"default": 0.7, "Trash": 0.95, "Spam": 0.9}

    # Ensure privacy settings exist
    if "privacy" not in config:
        config["privacy"] = {
            "analysis_mode": "full",
            "pii_scrubbing": True,
            "body_max_length": 2000,
        }

    # Ensure rate limiting exists
    if "rate_limit" not in config:
        config["rate_limit"] = {"max_requests_per_minute": 10, "enabled": True}

    # Add logging config
    if "logging" not in config:
        config["logging"] = {"level": "INFO", "debug_mode": False}

    return config


# ============================================================================
# Migration Engine
# ============================================================================


def find_migration_path(from_version: str, to_version: str) -> list[tuple[str, str]]:
    """Find sequence of migrations needed to go from one version to another."""
    path = []
    current = from_version
    target_tuple = version_tuple(to_version)

    while version_tuple(current) < target_tuple:
        # Find next migration
        next_migration = None
        for (from_v, to_v), _ in MIGRATIONS.items():
            if from_v == current and version_tuple(to_v) <= target_tuple:
                next_migration = (from_v, to_v)
                break

        if next_migration is None:
            # No direct migration, try to find any that advances us
            best_match = None
            for (from_v, to_v), _ in MIGRATIONS.items():
                if (
                    version_tuple(from_v)
                    <= version_tuple(current)
                    < version_tuple(to_v)
                ):
                    if best_match is None or version_tuple(to_v) < version_tuple(
                        best_match[1]
                    ):
                        best_match = (from_v, to_v)

            if best_match:
                next_migration = best_match
            else:
                break

        path.append(next_migration)
        current = next_migration[1]

    return path


def run_migrations(
    from_version: str, to_version: str, config: dict, dry_run: bool = False
) -> dict:
    """Run all migrations from one version to another."""
    path = find_migration_path(from_version, to_version)

    if not path:
        print(f"ℹ️  No migrations needed from {from_version} to {to_version}")
        return config

    print(f"📋 Migration path: {' -> '.join([from_version] + [p[1] for p in path])}")

    for from_v, to_v in path:
        migration_func = MIGRATIONS.get((from_v, to_v))
        if migration_func:
            print(f"🔄 Running migration {from_v} -> {to_v}...")
            if not dry_run:
                config = migration_func(config)
            print("   ✅ Done")

    # Update version in config
    if not dry_run:
        config["_version"] = to_version

    return config


def migrate(
    from_version: str = None, to_version: str = None, dry_run: bool = False
) -> bool:
    """Main migration entry point."""
    print("=" * 50)
    print("MailSorter Configuration Migration")
    print("=" * 50)
    print()

    # Load current config
    config = load_config()

    # Determine versions
    if from_version is None:
        from_version = get_config_version(config)

    if to_version is None:
        # Get current version from __version__.py
        from backend.__version__ import __version__

        to_version = __version__.split("-")[0]  # Remove prerelease suffix

    print(f"📌 Current config version: {from_version}")
    print(f"🎯 Target version: {to_version}")
    print()

    if version_tuple(from_version) >= version_tuple(to_version):
        print("✅ Config is up to date, no migration needed")
        return True

    if dry_run:
        print("🔍 DRY RUN - no changes will be made")
        print()
    else:
        # Backup before migration
        backup_config(CONFIG_FILE)
        print()

    # Run migrations
    try:
        config = run_migrations(from_version, to_version, config, dry_run)

        if not dry_run:
            save_config(config)
            print()
            print("✅ Migration complete!")
        else:
            print()
            print("✅ Dry run complete - no changes made")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("   Config backup available in backend/config_backups/")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Migrate MailSorter configuration between versions"
    )
    parser.add_argument(
        "--from",
        dest="from_version",
        help="Source version (default: current config version)",
    )
    parser.add_argument(
        "--to", dest="to_version", help="Target version (default: current app version)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument("--list", action="store_true", help="List available migrations")

    args = parser.parse_args()

    if args.list:
        print("Available migrations:")
        for (from_v, to_v), func in sorted(MIGRATIONS.items()):
            print(f"  {from_v} -> {to_v}: {func.__doc__.strip().split(chr(10))[0]}")
        return

    success = migrate(
        from_version=args.from_version, to_version=args.to_version, dry_run=args.dry_run
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
