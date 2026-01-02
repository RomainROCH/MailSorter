# Changelog

All notable changes to MailSorter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Feature detection with IMAP fallback (V5-001)
- OpenAI provider (V5-003)
- Headers-only mode (V5-004)
- Dynamic thresholds per folder (V5-005)
- HMAC signature for headers (V5-007)
- Full test suite and benchmarks (V5-009, V5-010)

## [0.1.0-alpha] - 2026-01-02

### Added
- Initial architecture (hybrid WebExtension + Python Native Host)
- Ollama provider for local LLM inference
- Privacy Guard with PII scrubbing (email, phone, IP addresses)
- Native Messaging protocol implementation (stdio)
- Configuration system with JSON Schema validation
- Plan V5 compliance documentation (RGPD, security, architecture)
- Project management structure (.instructions/, tasks.md)
- CI workflow with pytest
- Comprehensive documentation (Plan V5, Architecture, RGPD, Versioning)

### Security
- PII minimization (2000 char truncation, regex scrubbing)
- Native Messaging stdio isolation (no network ports)
- Logs sent to stderr only (no stdout pollution)
- Configuration secrets excluded from git
- OS Keyring integration planned for API keys

### Known Limitations
- MIME parsing simplified (multipart emails may not be fully processed)
- Attachment content not analyzed (hash/MIME only)
- Configuration currently hardcoded (will be externalized in 0.2.0)
- No Windows installer yet (manual Registry setup required)

---

**Legend:**
- `Added` for new features.
- `Changed` for changes in existing functionality.
- `Deprecated` for soon-to-be removed features.
- `Removed` for now removed features.
- `Fixed` for any bug fixes.
- `Security` in case of vulnerabilities.
