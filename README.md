# MailSorter

![Version](https://img.shields.io/badge/version-1.0.0-green) ![License](https://img.shields.io/badge/license-MIT-blue) ![Status](https://img.shields.io/badge/status-stable-green)

**Version:** 1.0.0 | [Changelog](CHANGELOG.md) | [User Guide](docs/USER_GUIDE.md)

> 🚀 **AI-powered email sorting for Thunderbird & Betterbird**

## Overview

MailSorter is an intelligent email sorting extension that uses Large Language Models (LLMs) to automatically classify and organize your emails. Built with a **Privacy-First** approach using a hybrid WebExtension + Native Messaging architecture.

**Key Features:**
- 🤖 **Multiple LLM Providers** - Ollama (local), OpenAI, Anthropic, Google Gemini
- 🔒 **Privacy-First** - PII scrubbing, headers-only mode, local processing option
- 📊 **92-98% Accuracy** - Observed on public dataset benchmarks
- ⚡ **Real-Time & Batch** - Sort new emails instantly or process archives in bulk
- 🌍 **Multi-Language** - French and English interface

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/RomainROCH/MailSorter.git
cd MailSorter

# 2. Install Python dependencies
cd backend && pip install -r requirements.txt && cd ..

# 3. Register native messaging (Windows)
installers\register.bat

# 4. Install extension in Thunderbird
# Menu → Add-ons → Install from File → select mailsorter-1.0.0.xpi
```

See the [User Guide](docs/USER_GUIDE.md) for detailed installation instructions.

## Documentation

| Document | Description |
|----------|-------------|
| 📖 [User Guide](docs/USER_GUIDE.md) | Installation, configuration, and usage |
| 🔧 [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| 📋 [Compatibility Matrix](docs/COMPATIBILITY.md) | Supported versions and platforms |
| 🏗️ [Architecture](docs/ARCHITECTURE.md) | Technical design and data flow |
| 🔒 [RGPD Compliance](docs/RGPD.md) | Privacy and security details |
| 📝 [Plan V5](docs/PLAN_V5.md) | Full specification |

## Requirements

| Component | Requirement |
|-----------|-------------|
| Email Client | Thunderbird 115+ or Betterbird |
| Python | 3.10 or higher |
| LLM | Ollama (local) or cloud API key |

See [Compatibility Matrix](docs/COMPATIBILITY.md) for detailed requirements.

## Usage

1. **Configure** - Run the onboarding wizard or go to Settings
2. **Map folders** - Connect categories to your email folders
3. **Sort automatically** - New emails are classified in real-time
4. **Manual sort** - Right-click → "Sort with MailSorter" or `Ctrl+Shift+M`

## Providers

| Provider | Type | Privacy | Cost |
|----------|------|---------|------|
| **Ollama** | Local | ⭐⭐⭐⭐⭐ | Free |
| **OpenAI** | Cloud | ⭐⭐⭐ | Paid |
| **Anthropic** | Cloud | ⭐⭐⭐ | Paid |
| **Gemini** | Cloud | ⭐⭐⭐ | Paid |

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

For security vulnerabilities, please see [SECURITY.md](SECURITY.md).

## License

MIT License - see [LICENSE](LICENSE)

---

*Made with ❤️ for email sanity*
