# Release Notes Template

Use this template when creating release notes for GitHub Releases.

---

## Template

```markdown
## MailSorter vX.Y.Z

**Release Date:** YYYY-MM-DD

### 🎉 Highlights

- Brief summary of the most important changes
- Focus on user-facing improvements
- Keep it to 2-3 bullet points

### ✨ New Features

- **Feature Name** - Brief description (#issue)
- **Feature Name** - Brief description (#issue)

### 🐛 Bug Fixes

- Fixed issue with... (#issue)
- Resolved problem where... (#issue)

### 🔧 Improvements

- Improved performance of...
- Enhanced UI for...
- Updated documentation for...

### 🔒 Security

- Updated dependency X to address CVE-XXXX-XXXX
- Fixed security issue in...

### ⚠️ Breaking Changes

- **Config format changed**: `old_key` is now `new_key`
- **Minimum Thunderbird version**: Now requires TB 115+

### 📦 Dependencies

- Updated requests to 2.32.0
- Updated jsonschema to 4.20.0

### 🙏 Contributors

Thanks to everyone who contributed to this release:
- @contributor1
- @contributor2

---

### Installation

**New Installation:**
1. Download `mailsorter-X.Y.Z.xpi` below
2. Open Thunderbird → Add-ons → Install from File
3. Select the downloaded file

**Upgrade:**
- Thunderbird will auto-update if you have a previous version
- Or download and install manually

**Verify Download:**
```bash
sha256sum -c mailsorter-X.Y.Z.xpi.sha256
```

---

### Compatibility

| Component | Requirement |
|-----------|-------------|
| Thunderbird | 115+ |
| Python | 3.10+ |
| Ollama | 0.4+ (for local LLM) |

See [COMPATIBILITY.md](https://github.com/RomainROCH/MailSorter/blob/main/docs/COMPATIBILITY.md) for details.

---

**Full Changelog:** [CHANGELOG.md](https://github.com/RomainROCH/MailSorter/blob/main/CHANGELOG.md)
**Documentation:** [User Guide](https://github.com/RomainROCH/MailSorter/blob/main/docs/USER_GUIDE.md)
```

---

## Quick Release Notes Examples

### Patch Release (X.Y.Z → X.Y.Z+1)

```markdown
## MailSorter v1.0.1

**Release Date:** 2026-01-15

### 🐛 Bug Fixes

- Fixed crash when processing emails with malformed headers (#123)
- Resolved issue where Ollama connection would timeout prematurely (#125)

### 🔧 Improvements

- Improved error messages for connection failures

---

### Installation

Download `mailsorter-1.0.1.xpi` below and install in Thunderbird.
```

### Minor Release (X.Y → X.Y+1)

```markdown
## MailSorter v1.1.0

**Release Date:** 2026-02-01

### 🎉 Highlights

- New Groq provider support for ultra-fast inference
- Improved folder mapping UI with search

### ✨ New Features

- **Groq Provider** - Access Groq's fast inference API (#150)
- **Folder Search** - Quickly find folders in mapping UI (#145)
- **Export Stats** - Download your sorting statistics (#140)

### 🐛 Bug Fixes

- Fixed memory leak during batch processing (#148)
- Resolved UI glitch in dark mode (#142)

---

### Installation

Download `mailsorter-1.1.0.xpi` below and install in Thunderbird.
```

### Major Release (X → X+1)

```markdown
## MailSorter v2.0.0

**Release Date:** 2026-06-01

### 🎉 Highlights

- Complete UI redesign with modern look
- New rule-based sorting alongside AI
- Multi-account support

### ⚠️ Breaking Changes

- **Config format changed**: Please run `python scripts/migrate.py` after updating
- **Minimum Thunderbird**: Now requires TB 128+
- **Python**: Now requires Python 3.11+

### ✨ New Features

- **Rule Engine** - Create custom sorting rules (#200)
- **Multi-Account** - Different settings per email account (#195)
- **New UI** - Completely redesigned interface (#180)

### 🔄 Migration

Run the migration script after updating:
```bash
cd MailSorter
python scripts/migrate.py --from 1.x --to 2.0
```

See [Migration Guide](https://github.com/RomainROCH/MailSorter/blob/main/docs/MIGRATION.md) for details.

---

### Installation

Download `mailsorter-2.0.0.xpi` below and install in Thunderbird.
```

---

## Changelog Entry Template

For CHANGELOG.md:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature description (#issue)

### Changed
- Changed behavior description (#issue)

### Deprecated
- Feature X is deprecated, use Y instead

### Removed
- Removed obsolete feature

### Fixed
- Bug fix description (#issue)

### Security
- Security fix description (CVE-XXXX-XXXX)
```

---

## Pre-Release Labels

Use these labels for pre-release versions:

| Label | Meaning | Example |
|-------|---------|---------|
| `-alpha` | Early testing, unstable | `1.0.0-alpha` |
| `-beta` | Feature complete, testing | `1.0.0-beta` |
| `-rc.1` | Release candidate | `1.0.0-rc.1` |

---

## GitHub Release Settings

When creating a GitHub Release:

| Setting | Value |
|---------|-------|
| Tag | `vX.Y.Z` (e.g., `v1.0.0`) |
| Title | `MailSorter vX.Y.Z` |
| Pre-release | Check if alpha/beta/rc |
| Latest | Check for stable releases |
| Assets | XPI file + SHA256 checksum |
