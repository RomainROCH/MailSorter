# Changelog

All notable changes to MailSorter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Structured logging (OPS-001)
- Debug mode toggle (OPS-002)
- Telemetry opt-in (OPS-004)
- GitHub issue templates (COM-001)

## [1.0.0] - 2026-01-08

### 🎉 Highlights

This is the first stable release of MailSorter! A production-ready, privacy-first email sorting solution for Thunderbird and Betterbird.

### Added

**Core Features (Phases 1-4)**
- Hybrid WebExtension + Python Native Host architecture
- Multiple LLM provider support: Ollama (local), OpenAI, Anthropic, Gemini
- Provider factory pattern for easy provider switching
- Feature detection with Thunderbird API compatibility checks
- IMAP fallback when custom headers unavailable
- Batch processing mode for archive sorting
- Real-time mode for new mail
- Circuit breaker for LLM resilience (3 failures = 30s cooldown)
- Smart caching for repeated classifications
- Rate limiting (10 req/min default)

**Privacy & Security (Phase 3)**
- Privacy Guard with Presidio NLP-based PII detection
- Headers-only mode for ultra-sensitive environments
- HMAC-SHA256 signature for classification headers
- API key storage via OS keyring (not in config files)
- Input sanitization against prompt injection
- Content Security Policy enforcement
- Attachment heuristics (SHA256 hash, MIME type analysis)

**User Experience (Phase 5)**
- Full options page with provider configuration
- Onboarding wizard for first-time setup
- Visual folder mapping with drag-and-drop
- Connection status indicator (green/yellow/red)
- Processing indicator during classification
- Undo last sort action (10s window)
- Bulk archive sorting with progress bar
- Passive mode toggle (one-click disable)
- Keyboard shortcuts (Ctrl+Shift+M to classify)
- Context menu integration (right-click to sort)
- Stats dashboard with sorting metrics
- Dark mode support (follows Thunderbird theme)
- Internationalization (English and French)
- WCAG 2.1 AA accessibility compliance
- High contrast mode support

**Quality Assurance (Phase 6)**
- 186+ automated tests covering:
  - Unit tests (80%+ coverage)
  - Integration tests (E2E)
  - Security tests (OWASP focused)
  - Performance benchmarks
  - Cross-platform tests
  - Stress tests
  - Regression tests
  - Fuzz tests for MIME parsing
- Benchmark infrastructure with 50-email dataset
- Manual QA checklist (87 items)
- RGPD compliance audit documentation

**Documentation & Release (Phase 7)**
- Comprehensive User Guide
- Troubleshooting Guide
- Compatibility Matrix (TB versions, OS, Python)
- Architecture documentation
- RGPD compliance documentation
- Release and signing guide
- Automated XPI packaging (`make package`)
- GitHub Actions release workflow
- Automatic update mechanism
- Migration scripts for config upgrades
- Release notes template

### Changed
- Upgraded from simple regex PII detection to Presidio NLP
- Configuration now uses JSON Schema validation
- Improved error messages with user-friendly notifications

### Security
- PII scrubbing before LLM processing (email, phone, IP, credit cards)
- 2000 character body truncation
- Native Messaging stdio isolation
- No inline scripts (CSP compliant)
- Dependency vulnerability scanning in CI

### Compatibility
- Thunderbird 115+ required (128+ recommended)
- Betterbird 115+ supported
- Python 3.10+ required
- Windows 10/11, Linux (Ubuntu 20.04+), macOS 12+

## [0.2.0] - 2026-01-06

### Added
- OpenAI provider with GPT-4o-mini support
- Anthropic provider with Claude 3 support
- Gemini provider with Google AI support
- Dynamic thresholds per folder configuration
- Prompt template system for A/B testing
- Multi-language prompt support (FR/EN detection)
- Confidence score calibration

### Changed
- Provider configuration moved to structured format
- Improved error handling with centralized logging

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
