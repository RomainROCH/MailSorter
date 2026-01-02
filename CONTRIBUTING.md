# Contributing to MailSorter

Thank you for your interest in contributing! 🎉

## Current Status

**MailSorter is in ALPHA (v0.1.0-alpha)**. The architecture is stable, but many features are still in development.

## How to Contribute

### Reporting Bugs
- Check [existing issues](https://github.com/YOUR_USERNAME/MailSorter/issues) first
- Include: OS, Thunderbird/Betterbird version, Python version, logs
- Attach anonymized email samples if possible (scrub PII!)

### Suggesting Features
- Review [Plan V5](docs/PLAN_V5.md) to ensure alignment
- Open an issue with `[Feature Request]` prefix
- Explain the use case and expected behavior

### Pull Requests
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Follow the coding conventions in [.instructions/contexts/project.patterns.md](.instructions/contexts/project.patterns.md)
4. Add tests for new code
5. Update `CHANGELOG.md` (Unreleased section)
6. Submit PR with clear description

## Development Setup

```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/MailSorter.git
cd MailSorter

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run tests
pytest -v

# Extension setup
# Load extension/ folder in Thunderbird Debug Addons
```

## Code Standards

- **Python**: PEP 8, docstrings for all functions
- **JavaScript**: ESLint (config TBD), async/await preferred
- **Logging**: Never use `print()` in backend (Native Messaging constraint)
- **Security**: All user data must pass through `PrivacyGuard.sanitize()`

## Architecture Decisions

Major changes should be discussed in an issue first. See:
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/PLAN_V5.md](docs/PLAN_V5.md)
- [.instructions/contexts/project.memory.md](.instructions/contexts/project.memory.md)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
