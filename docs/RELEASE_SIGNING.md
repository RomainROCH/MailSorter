# MailSorter Release & Signing Guide

> Documentation for the release process, extension signing, and update mechanism

---

## Table of Contents

1. [Release Process Overview](#release-process-overview)
2. [Version Management](#version-management)
3. [Extension Signing](#extension-signing)
4. [Update Mechanism](#update-mechanism)
5. [Rollback Procedure](#rollback-procedure)
6. [Self-Distribution](#self-distribution)
7. [Troubleshooting](#troubleshooting)

---

## Release Process Overview

### Pre-Release Checklist

- [ ] All tests pass (`make test`)
- [ ] Lint checks pass (`make lint`)
- [ ] Security scan passes
- [ ] CHANGELOG.md updated with release notes
- [ ] Version numbers synchronized (manifest.json, __version__.py)
- [ ] User documentation updated if needed
- [ ] Manual QA checklist completed (see docs/QA_CHECKLIST.md)

### Release Steps

1. **Create release branch:**
   ```bash
   git checkout -b release/v1.0.0
   ```

2. **Update version numbers:**
   ```bash
   python scripts/package_xpi.py --update-version --version 1.0.0
   ```

3. **Update CHANGELOG.md:**
   - Move items from `[Unreleased]` to `[1.0.0] - YYYY-MM-DD`
   - Add summary of changes

4. **Commit and tag:**
   ```bash
   git add -A
   git commit -m "chore: release v1.0.0"
   git tag -a v1.0.0 -m "Release v1.0.0"
   ```

5. **Push and trigger CI:**
   ```bash
   git push origin release/v1.0.0
   git push origin v1.0.0
   ```

6. **CI will automatically:**
   - Build the XPI package
   - Create GitHub release
   - Attach XPI and checksum files

7. **Merge to main:**
   ```bash
   git checkout main
   git merge release/v1.0.0
   git push origin main
   ```

---

## Version Management

### Semantic Versioning

MailSorter follows [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH[-PRERELEASE]
```

| Component | When to Increment |
|-----------|-------------------|
| MAJOR | Breaking changes (config format, API) |
| MINOR | New features, backward-compatible |
| PATCH | Bug fixes, security patches |
| PRERELEASE | Alpha, beta, rc versions |

### Version File Locations

| File | Format | Notes |
|------|--------|-------|
| `extension/manifest.json` | `"version": "1.0.0"` | No prerelease tags |
| `backend/__version__.py` | `__version__ = "1.0.0"` | Can include prerelease |
| `CHANGELOG.md` | `[1.0.0] - 2026-01-08` | Keep a changelog format |

### Synchronization Script

```bash
# Update all version files at once
python scripts/package_xpi.py --update-version --version 1.0.0
```

---

## Extension Signing

### Why Sign?

Thunderbird requires extensions to be signed for installation (except in debug mode). Signing provides:

- **Authenticity**: Verifies the extension comes from a trusted source
- **Integrity**: Ensures the extension hasn't been tampered with
- **User Trust**: Shows users the extension is legitimate

### Signing Options

#### Option 1: Mozilla Add-ons (AMO) - Recommended

The official way to distribute Thunderbird extensions:

1. **Create AMO account:**
   - Visit [addons.thunderbird.net](https://addons.thunderbird.net)
   - Create developer account

2. **Submit for review:**
   - Upload the XPI
   - Fill in listing details
   - Wait for review (1-7 days typically)

3. **Benefits:**
   - Automatic updates for users
   - Wider distribution
   - Trusted by Thunderbird

4. **Limitations:**
   - Review process takes time
   - Must comply with AMO policies
   - Source code review may be required

#### Option 2: Self-Signing (web-ext)

For self-distribution without AMO listing:

1. **Get API credentials:**
   - Visit [addons.mozilla.org/developers/addon/api/key/](https://addons.mozilla.org/en-US/developers/addon/api/key/)
   - Generate API key and secret

2. **Install web-ext:**
   ```bash
   npm install -g web-ext
   ```

3. **Sign the extension:**
   ```bash
   cd extension
   web-ext sign \
     --api-key=YOUR_API_KEY \
     --api-secret=YOUR_API_SECRET \
     --channel=unlisted
   ```

4. **Output:**
   - Signed XPI in `web-ext-artifacts/`
   - Can be installed in Thunderbird

5. **Limitations:**
   - No automatic updates (must implement manually)
   - Users see "unlisted" warning
   - Still requires AMO account

#### Option 3: Development Mode (Unsigned)

For development and testing only:

1. Open Thunderbird
2. Go to `Menu → Add-ons → Debug Add-ons`
3. Click "Load Temporary Add-on"
4. Select `extension/manifest.json`

**Note:** Extension unloads when Thunderbird closes.

### CI/CD Signing

For automated signing in GitHub Actions:

```yaml
# .github/workflows/release.yml
- name: Sign extension
  env:
    WEB_EXT_API_KEY: ${{ secrets.AMO_API_KEY }}
    WEB_EXT_API_SECRET: ${{ secrets.AMO_API_SECRET }}
  run: |
    npm install -g web-ext
    cd extension
    web-ext sign --channel=unlisted
```

**Required secrets:**
- `AMO_API_KEY`: Your AMO API key
- `AMO_API_SECRET`: Your AMO API secret

---

## Update Mechanism

### How Updates Work

Thunderbird checks for extension updates periodically. The update process:

1. Thunderbird reads `update_url` from manifest.json
2. Fetches update manifest (JSON file)
3. Compares versions
4. Downloads new XPI if available
5. Installs update (user confirmation may be required)

### Setting Up Automatic Updates

#### Step 1: Add update_url to manifest.json

```json
{
  "browser_specific_settings": {
    "gecko": {
      "id": "mailsorter@planv5.local",
      "strict_min_version": "115.0",
      "update_url": "https://raw.githubusercontent.com/RomainROCH/MailSorter/main/updates.json"
    }
  }
}
```

#### Step 2: Create updates.json

Host this file at the `update_url`:

```json
{
  "addons": {
    "mailsorter@planv5.local": {
      "updates": [
        {
          "version": "1.0.0",
          "update_link": "https://github.com/RomainROCH/MailSorter/releases/download/v1.0.0/mailsorter-1.0.0.xpi",
          "update_hash": "sha256:abc123...",
          "browser_specific_settings": {
            "gecko": {
              "strict_min_version": "115.0"
            }
          }
        }
      ]
    }
  }
}
```

#### Step 3: Update on Each Release

Add this to your release workflow:

```yaml
- name: Update updates.json
  run: |
    python scripts/update_manifest.py \
      --version ${{ steps.version.outputs.version }} \
      --xpi-url "https://github.com/.../releases/download/v.../mailsorter-....xpi" \
      --xpi-hash "sha256:..."
```

### Update Manifest Schema

| Field | Description |
|-------|-------------|
| `version` | Version string (must match XPI) |
| `update_link` | URL to download the XPI |
| `update_hash` | SHA256 hash prefixed with `sha256:` |
| `strict_min_version` | Minimum Thunderbird version |

### AMO Updates (Recommended)

If distributed through AMO, updates are automatic:

1. Upload new version to AMO
2. Pass review
3. Users auto-update (within 24 hours typically)

No `update_url` or `updates.json` needed for AMO distribution.

---

## Rollback Procedure

### Emergency Rollback

If a release has critical issues:

1. **Create hotfix tag:**
   ```bash
   git tag -a v1.0.1 -m "Hotfix: rollback to v0.9.x"
   git push origin v1.0.1
   ```

2. **Update updates.json:**
   - Point to previous stable version
   - Users will "update" to older version

3. **Communicate:**
   - Post in GitHub Discussions
   - Update release notes

### Version Archival

Keep previous versions available:

```
releases/
├── mailsorter-0.9.0.xpi
├── mailsorter-0.9.0.xpi.sha256
├── mailsorter-1.0.0.xpi  # Current
└── mailsorter-1.0.0.xpi.sha256
```

### User Rollback Instructions

For manual user rollback:

1. Download previous version from [Releases](https://github.com/RomainROCH/MailSorter/releases)
2. Uninstall current version:
   - Menu → Add-ons → MailSorter → Remove
3. Install previous version:
   - Menu → Add-ons → Install from File
4. Restart Thunderbird

---

## Self-Distribution

For distributing outside of AMO:

### Hosting Requirements

- HTTPS required for update_url
- Stable URLs (GitHub Releases recommended)
- Checksums for integrity verification

### Recommended: GitHub Releases

```
https://github.com/USERNAME/MailSorter/releases/download/vX.Y.Z/mailsorter-X.Y.Z.xpi
```

Benefits:
- Free hosting
- Reliable CDN
- Version history
- Easy automation

### Installation Instructions for Users

1. Download `mailsorter-X.Y.Z.xpi` from [Releases](https://github.com/RomainROCH/MailSorter/releases)
2. Verify checksum (optional but recommended):
   ```bash
   sha256sum -c mailsorter-X.Y.Z.xpi.sha256
   ```
3. Open Thunderbird
4. Go to Menu → Add-ons and Themes
5. Click gear icon → Install Add-on From File
6. Select downloaded .xpi file
7. Click "Add" when prompted

---

## Troubleshooting

### Signing Issues

#### "Extension signing is required"

- Use web-ext to sign, or
- Distribute through AMO, or
- Users can disable signing requirement (not recommended for production)

#### "API key invalid"

- Regenerate key at addons.mozilla.org
- Check key hasn't expired
- Verify secrets in CI

### Update Issues

#### Updates not detected

1. Check `update_url` is accessible
2. Verify HTTPS certificate
3. Check JSON syntax in updates.json
4. Compare version numbers (new must be > old)

#### Update download fails

1. Verify `update_link` URL
2. Check file exists at URL
3. Verify hash matches

### Version Mismatch

#### "Version already exists"

- Cannot reuse version numbers
- Bump patch version for fixes
- Delete failed release before retry

---

## Quick Reference

### Common Commands

```bash
# Build package
make package

# Build release package (updates versions)
make package-release VERSION=1.0.0

# Validate only
make package-validate

# Sign with web-ext
cd extension && web-ext sign --api-key=$KEY --api-secret=$SECRET

# Create release tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### Required Secrets (CI)

| Secret | Purpose |
|--------|---------|
| `GITHUB_TOKEN` | Create releases (auto-provided) |
| `AMO_API_KEY` | Sign extension (optional) |
| `AMO_API_SECRET` | Sign extension (optional) |

---

*See also: [VERSIONING.md](VERSIONING.md), [CONTRIBUTING.md](../CONTRIBUTING.md)*
