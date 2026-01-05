# Versioning Strategy - MailSorter

## Semantic Versioning (SemVer)

MailSorter follows [Semantic Versioning 2.0.0](https://semver.org/):

**Format:** `MAJOR.MINOR.PATCH[-PRERELEASE]`

- **MAJOR**: Incompatible API/architecture changes (e.g., 1.x → 2.x).
- **MINOR**: New features, backward-compatible (e.g., 1.0 → 1.1).
- **PATCH**: Bug fixes, security patches, backward-compatible (e.g., 1.0.0 → 1.0.1).
- **PRERELEASE**: Alpha, beta, rc (e.g., `0.1.0-alpha`, `1.0.0-rc.1`).

---

## Version Synchronization

The following files **must** be updated together for each release:

1. **`extension/manifest.json`** → `"version": "X.Y.Z"`
2. **`backend/__version__.py`** → `__version__ = "X.Y.Z[-PRERELEASE]"`
3. **`CHANGELOG.md`** → Add release section `[X.Y.Z] - YYYY-MM-DD`

---

## Current Version

**Current:** `0.1.0-alpha`

- **Extension**: `0.1.0` (manifest.json - prerelease tags not supported)
- **Backend**: `0.1.0-alpha` (__version__.py)

---

## Release Process

1. Update `backend/__version__.py` with new version.
2. Update `extension/manifest.json` with same version (strip prerelease tag).
3. Update `CHANGELOG.md` with release notes (move `[Unreleased]` to `[X.Y.Z]`).
4. Commit: `git commit -m "chore: release vX.Y.Z"`
5. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
6. Push: `git push && git push --tags`
7. Build `.xpi`: Run packaging script (TBD).

---

## Roadmap

- **0.1.0-alpha** (Current): Core functionality, Ollama provider, Plan V5 foundations.
- **0.2.0-alpha**: OpenAI provider, feature detection, fallback IMAP.
- **0.3.0-beta**: Full Plan V5 compliance (headers-only mode, HMAC signatures).
- **1.0.0**: Production-ready, tested, audited, full documentation.

---

## Notes

- Pre-1.0 versions (`0.x.x`) may introduce breaking changes in MINOR updates.
- Post-1.0, MAJOR version increments only for breaking changes.
- Security patches get PATCH increments and are backported if critical.
- Extension manifest does not support prerelease tags (use `0.1.0` not `0.1.0-alpha`).
