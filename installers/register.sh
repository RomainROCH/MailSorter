#!/usr/bin/env bash
# ============================================================
# MailSorter - Linux/macOS Native Messaging Host Registration
# ============================================================
# This script installs the Native Messaging manifest so that
# Thunderbird/Betterbird can locate the MailSorter backend.
# ============================================================

set -euo pipefail

APP_NAME="com.mailsorter.backend"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_SRC="$SCRIPT_DIR/../backend/app_manifest.json"

# Resolve absolute path
MANIFEST_ABS="$(cd "$(dirname "$MANIFEST_SRC")" && pwd)/$(basename "$MANIFEST_SRC")"

if [[ ! -f "$MANIFEST_ABS" ]]; then
    echo "ERROR: Manifest not found at $MANIFEST_ABS"
    exit 1
fi

# Detect OS and set target directory
case "$(uname -s)" in
    Linux*)
        TARGET_DIR="$HOME/.mozilla/native-messaging-hosts"
        ;;
    Darwin*)
        TARGET_DIR="$HOME/Library/Application Support/Mozilla/NativeMessagingHosts"
        ;;
    *)
        echo "ERROR: Unsupported OS. This script supports Linux and macOS only."
        exit 1
        ;;
esac

mkdir -p "$TARGET_DIR"
TARGET_FILE="$TARGET_DIR/$APP_NAME.json"

echo "Installing Native Messaging Host..."
echo "  App Name : $APP_NAME"
echo "  Source   : $MANIFEST_ABS"
echo "  Target   : $TARGET_FILE"

# Copy (or symlink) the manifest
cp "$MANIFEST_ABS" "$TARGET_FILE"

echo ""
echo "SUCCESS: Native Messaging Host installed."
echo "Restart Thunderbird/Betterbird to apply changes."
