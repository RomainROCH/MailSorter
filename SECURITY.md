# Security Policy

## Reporting a Vulnerability

**MailSorter Labs** takes security seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please report security issues via email:

📧 **security [at] mailsorterlabs [dot] com**

Or use GitHub's private vulnerability reporting:
1. Go to the [Security tab](https://github.com/RomainROCH/MailSorter/security)
2. Click "Report a vulnerability"
3. Fill out the form with details

### What to Include

Please include the following in your report:

- **Description** of the vulnerability
- **Steps to reproduce** (proof of concept if possible)
- **Impact assessment** (what could an attacker do?)
- **Affected components** (backend, extension, specific files)
- **Suggested fix** (if you have one)

### Response Timeline

| Phase | Timeframe |
|-------|-----------|
| Acknowledgment | Within 48 hours |
| Initial Assessment | Within 1 week |
| Fix Development | Depends on severity |
| Public Disclosure | After fix is released |

### Severity Levels

| Level | Description | Response |
|-------|-------------|----------|
| **Critical** | Remote code execution, data exfiltration | Immediate priority |
| **High** | Authentication bypass, significant data exposure | Within 1 week |
| **Medium** | Limited data exposure, denial of service | Within 2 weeks |
| **Low** | Minor issues, hardening recommendations | Next release cycle |

### Safe Harbor

We will not pursue legal action against researchers who:
- Act in good faith
- Avoid privacy violations and data destruction
- Do not exploit vulnerabilities beyond proof of concept
- Report findings promptly and privately

---

## Security Measures

MailSorter implements multiple layers of security:

### Data Protection
- **PII Scrubbing**: Email addresses, phone numbers, and IPs are removed before LLM processing
- **Body Truncation**: Email bodies limited to 2000 characters
- **Headers-Only Mode**: Optional ultra-private mode that never sends email body to AI
- **No Data Retention**: Emails are not stored by the extension

### Secure Storage
- **Keyring Integration**: API keys stored in OS secure storage, not config files
- **HMAC Signatures**: Optional cryptographic signing of classification headers

### Input Validation
- **Sanitization**: Protection against prompt injection attacks
- **Schema Validation**: All configuration validated against JSON schema

### Code Security
- **CSP Enforced**: No inline scripts in extension
- **Automated Scanning**: CI/CD runs Bandit, Ruff (security rules), and dependency audits
- **Regular Audits**: Dependency vulnerabilities scanned weekly

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.1.x | ✅ Active development |
| 1.0.x | ✅ Security fixes only |
| < 1.0 | ❌ No support |

---

## Security Audit

For a complete security and privacy audit, see:
- [docs/RGPD.md](docs/RGPD.md) - Privacy compliance
- [docs/RGPD_AUDIT.md](docs/RGPD_AUDIT.md) - Detailed audit report

---

*MailSorter Labs — Security is a feature, not an afterthought.*
