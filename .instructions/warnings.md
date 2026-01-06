# Project Warnings & Risks
*Active warnings, inconsistencies, and risks detected in this project.*

## ⚠️ Active Warnings

### W-001: Cloud Provider Data Transfer (RGPD)
- **Severity**: HIGH
- **Description**: When using OpenAI/Anthropic/Gemini providers, email content is transmitted to US-based servers.
- **Mitigation**: Verify SCC/DPF compliance with provider. Prefer local Ollama for sensitive data.
- **Status**: Open

### W-002: MIME Parsing Limitations
- **Severity**: MEDIUM
- **Description**: The JavaScript MIME parser in `background.js` uses regex-based HTML stripping which may miss edge cases.
- **Mitigation**: For complex HTML emails, some content may be lost. Consider a full MIME library for production.
- **Status**: Accepted (MVP)

### W-003: Batch API Latency
- **Severity**: LOW
- **Description**: OpenAI Batch API can take up to 24h for processing. Not suitable for real-time email sorting.
- **Mitigation**: Batch mode is explicitly documented as archive-only. Real-time mode uses standard API.
- **Status**: Documented

### W-004: Custom Headers Not Persisted
- **Severity**: LOW
- **Description**: Thunderbird WebExtension API does not allow writing custom headers to IMAP messages.
- **Mitigation**: Use message tags or folder location as the source of truth for classification.
- **Status**: By Design

---

## 🔒 Security Concerns

### S-001: API Keys in Config
- **Severity**: HIGH
- **Description**: Cloud provider API keys may be stored in `config.json` if not using keyring.
- **Mitigation**: `config.json` is in `.gitignore`. Document keyring usage for production.
- **Status**: Mitigated

### S-002: No Request Signing (Yet)
- **Severity**: MEDIUM
- **Description**: Native messaging requests are not signed (HMAC). Local tampering is possible.
- **Mitigation**: HMAC signing is planned for Phase 3 (V5-007).
- **Status**: Planned

---

## 📐 Pattern Drift

*No pattern drift detected yet*

---

## 📝 Notes
- Project initialized on 2026-01-02
- Phase 1 completed on 2026-01-06
- Phase 2 completed on 2026-01-06
- This file will be updated as warnings are detected
