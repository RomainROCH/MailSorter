# MailSorter User Guide

> **Version:** 1.0.0 | **Last Updated:** January 2026

Welcome to MailSorter! This guide will help you install, configure, and use MailSorter to automatically sort your emails in Thunderbird or Betterbird using AI.

---

## Table of Contents

1. [What is MailSorter?](#what-is-mailsorter)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
   - [Windows Installation](#windows-installation)
   - [Linux Installation](#linux-installation)
   - [macOS Installation](#macos-installation)
4. [Initial Setup](#initial-setup)
5. [Configuration](#configuration)
   - [Provider Setup](#provider-setup)
   - [Folder Mapping](#folder-mapping)
   - [Privacy Settings](#privacy-settings)
6. [Usage](#usage)
   - [Automatic Sorting](#automatic-sorting)
   - [Manual Sorting](#manual-sorting)
   - [Bulk Sorting](#bulk-sorting)
   - [Undo Actions](#undo-actions)
7. [Keyboard Shortcuts](#keyboard-shortcuts)
8. [Understanding the Dashboard](#understanding-the-dashboard)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)
11. [Privacy & Security](#privacy--security)
12. [Getting Help](#getting-help)

---

## What is MailSorter?

MailSorter is an intelligent email sorting extension for Thunderbird and Betterbird that uses Large Language Models (LLMs) to automatically classify and organize your emails into folders.

**Key Features:**
- 🤖 **AI-Powered Sorting** - Uses local (Ollama) or cloud (OpenAI, Anthropic, Gemini) LLMs
- 🔒 **Privacy-First** - PII scrubbing before any AI processing
- 📧 **Headers-Only Mode** - Ultra-private mode that never sends email body to AI
- 🎯 **Smart Thresholds** - Configurable confidence levels per folder
- ⚡ **Real-Time & Batch** - Sort new emails instantly or process archives in bulk
- 🌍 **Multi-Language** - Supports French and English interfaces

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| Email Client | Thunderbird 115+ or Betterbird |
| Python | Python 3.10 or higher |
| OS | Windows 10/11, Linux (Ubuntu 20.04+), macOS 12+ |
| Memory | 4 GB RAM (8 GB recommended for local LLM) |
| Disk | 500 MB for extension + Python backend |

### For Local LLM (Ollama)

| Component | Requirement |
|-----------|-------------|
| Ollama | Latest version from [ollama.ai](https://ollama.ai) |
| GPU | Optional but recommended (NVIDIA/AMD) |
| Memory | 8 GB RAM minimum (16 GB recommended) |
| Disk | 4-10 GB per model (varies by model) |

### For Cloud LLM

| Component | Requirement |
|-----------|-------------|
| API Key | From OpenAI, Anthropic, or Google |
| Internet | Active connection required |

---

## Installation

### Windows Installation

#### Step 1: Install Python

1. Download Python 3.10+ from [python.org](https://python.org/downloads/)
2. Run the installer
3. **Important:** Check "Add Python to PATH" during installation
4. Verify installation:
   ```cmd
   python --version
   ```

#### Step 2: Download MailSorter

1. Download the latest release from [GitHub Releases](https://github.com/RomainROCH/MailSorter/releases)
2. Extract the ZIP to a folder (e.g., `C:\MailSorter`)

#### Step 3: Install Python Dependencies

Open Command Prompt and run:
```cmd
cd C:\MailSorter\backend
pip install -r requirements.txt
```

#### Step 4: Register Native Messaging Host

Run the registration script as Administrator:
```cmd
cd C:\MailSorter\installers
register.bat
```

This registers MailSorter with Thunderbird via the Windows Registry.

#### Step 5: Install the Extension

1. Open Thunderbird
2. Go to **Menu** → **Add-ons and Themes** (or press `Ctrl+Shift+A`)
3. Click the gear icon → **Install Add-on From File...**
4. Select `mailsorter-1.0.0.xpi` from the downloaded files
5. Click **Add** when prompted

#### Step 6: Restart Thunderbird

Close and reopen Thunderbird to activate MailSorter.

---

### Linux Installation

#### Step 1: Install Python

Most Linux distributions include Python. Verify:
```bash
python3 --version
```

If not installed:
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip

# Fedora
sudo dnf install python3 python3-pip

# Arch
sudo pacman -S python python-pip
```

#### Step 2: Download MailSorter

```bash
cd ~
git clone https://github.com/RomainROCH/MailSorter.git
# Or download and extract the ZIP
```

#### Step 3: Install Python Dependencies

```bash
cd ~/MailSorter/backend
pip3 install -r requirements.txt
```

#### Step 4: Register Native Messaging Host

```bash
cd ~/MailSorter/installers
chmod +x register.sh
./register.sh
```

This creates the manifest in `~/.mozilla/native-messaging-hosts/`.

#### Step 5: Configure the Manifest Path

Edit `backend/app_manifest.json` and set the correct path:
```json
{
  "name": "com.mailsorter.backend",
  "description": "MailSorter Native Backend",
  "path": "/home/YOUR_USERNAME/MailSorter/backend/main.py",
  "type": "stdio",
  "allowed_extensions": ["mailsorter@planv5.local"]
}
```

Make the main script executable:
```bash
chmod +x ~/MailSorter/backend/main.py
```

#### Step 6: Install the Extension

1. Open Thunderbird
2. Go to **Menu** → **Add-ons and Themes**
3. Click the gear icon → **Install Add-on From File...**
4. Select `mailsorter-1.0.0.xpi`

---

### macOS Installation

#### Step 1: Install Python

macOS includes Python, but you may need a newer version:
```bash
# Using Homebrew
brew install python@3.11
```

#### Step 2: Download MailSorter

```bash
cd ~
git clone https://github.com/RomainROCH/MailSorter.git
```

#### Step 3: Install Python Dependencies

```bash
cd ~/MailSorter/backend
pip3 install -r requirements.txt
```

#### Step 4: Register Native Messaging Host

```bash
cd ~/MailSorter/installers
chmod +x register.sh
./register.sh
```

This creates the manifest in `~/Library/Application Support/Mozilla/NativeMessagingHosts/`.

#### Step 5: Configure and Install Extension

Same as Linux Steps 5-6.

---

## Initial Setup

When you first launch Thunderbird after installing MailSorter, the **Onboarding Wizard** will guide you through setup:

### Step 1: Choose Your LLM Provider

Select one of the available providers:

| Provider | Type | Cost | Privacy |
|----------|------|------|---------|
| **Ollama** | Local | Free | Maximum (data never leaves your machine) |
| **OpenAI** | Cloud | Paid | Good (data processed by OpenAI) |
| **Anthropic** | Cloud | Paid | Good (data processed by Anthropic) |
| **Gemini** | Cloud | Paid | Good (data processed by Google) |

**For Ollama (Recommended for Privacy):**
1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull a model: `ollama pull llama3` or `ollama pull mistral`
3. Start Ollama: `ollama serve`

**For Cloud Providers:**
1. Create an account and get an API key
2. Enter the API key in the onboarding wizard

### Step 2: Test Connection

Click **Test Connection** to verify:
- ✅ Backend is running
- ✅ LLM provider is reachable
- ✅ Model is available

### Step 3: Map Your Folders

Drag and drop to map categories to your email folders:

| Category | Example Folder |
|----------|----------------|
| Invoices | `Finances/Invoices` |
| Newsletters | `Newsletters` |
| Work | `Professional` |
| Personal | `Personal` |
| Spam | `Junk` |
| Phishing | `Trash` |

### Step 4: Complete Setup

Click **Finish** to start sorting!

---

## Configuration

Access settings via **Menu** → **Add-ons** → **MailSorter** → **Preferences**, or click the MailSorter icon and select ⚙️ **Settings**.

### Provider Setup

#### Ollama Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| URL | Ollama server address | `http://localhost:11434` |
| Model | LLM model to use | `llama3` |
| Timeout | Request timeout (seconds) | `30` |

#### OpenAI Configuration

| Setting | Description |
|---------|-------------|
| API Key | Your OpenAI API key (stored securely in OS keyring) |
| Model | `gpt-4o-mini` (recommended) or `gpt-4o` |
| Use Streaming | Enable for faster perceived response |

#### Anthropic Configuration

| Setting | Description |
|---------|-------------|
| API Key | Your Anthropic API key |
| Model | `claude-3-haiku` (fast) or `claude-3-sonnet` |

#### Gemini Configuration

| Setting | Description |
|---------|-------------|
| API Key | Your Google AI API key |
| Model | `gemini-2.0-flash` or `gemini-2.5-pro` |

### Folder Mapping

Configure which folders correspond to each category:

1. Go to **Settings** → **Folder Mapping**
2. Use the visual drag-and-drop interface
3. Map categories like:
   - `Invoices` → `Finances/Factures`
   - `Newsletters` → `Newsletters`
   - `Work` → `Travail`

### Privacy Settings

#### Analysis Mode

| Mode | Description | Sent to LLM |
|------|-------------|-------------|
| **Full** (default) | Headers + truncated body | Subject, From, Body (2000 chars max) |
| **Headers-Only** | Ultra-private mode | Subject, From, Date only |

#### PII Scrubbing

Automatically removes before LLM processing:
- Email addresses (except sender/recipient)
- Phone numbers
- IP addresses
- Credit card patterns

#### HMAC Signatures

Enable to cryptographically sign classification headers:
- Prevents tampering with `X-LLM-Category` headers
- Verifies authenticity on future reads

### Threshold Configuration

Set confidence thresholds per folder:

| Folder | Threshold | Meaning |
|--------|-----------|---------|
| Archives | 0.60 | Low threshold (accept more) |
| Invoices | 0.85 | High threshold (strict) |
| Trash | 0.95 | Very high (avoid false positives) |

If classification confidence is below the threshold, the email stays in Inbox.

---

## Usage

### Automatic Sorting

Once configured, MailSorter works automatically:

1. **New email arrives** → Thunderbird triggers MailSorter
2. **Processing** → Shows "Sorting..." indicator
3. **Classification** → AI determines the category
4. **Action** → Email moves to the mapped folder

The status indicator in the toolbar shows:
- 🟢 **Green** - Connected and ready
- 🟡 **Yellow** - Processing
- 🔴 **Red** - Error (click for details)

### Manual Sorting

To manually classify an email:

1. **Right-click** the email → **Sort with MailSorter**
2. Or use keyboard shortcut: `Ctrl+Shift+M` (Windows/Linux) / `Cmd+Shift+M` (macOS)

### Bulk Sorting

To sort multiple emails at once:

1. Select multiple emails (use `Ctrl+Click` or `Shift+Click`)
2. Right-click → **Sort Selected with MailSorter**
3. A progress bar shows the status
4. Click **Cancel** to stop if needed

**Note:** Bulk sorting uses batch mode for efficiency, which may be slower per-email but more efficient for large selections.

### Undo Actions

Made a mistake? You have 10 seconds to undo:

1. After any sort action, a notification appears
2. Click **Undo** within 10 seconds
3. The email returns to its previous location

Or access undo from the popup menu → **Undo Last Sort**.

### Passive Mode

Disable automatic sorting temporarily:

1. Click the MailSorter icon in the toolbar
2. Toggle **Passive Mode** on
3. Manual sorting still works
4. Toggle off to resume automatic sorting

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+M` | Classify selected email |
| `Ctrl+Shift+Z` | Undo last sort (within 10s) |

*macOS: Replace `Ctrl` with `Cmd`*

---

## Understanding the Dashboard

Access the stats dashboard from the MailSorter popup → **📊 Statistics**.

### Metrics Displayed

| Metric | Description |
|--------|-------------|
| **Emails Sorted Today** | Number of emails classified today |
| **Emails Sorted This Week** | Total for the current week |
| **Top Categories** | Most common classifications |
| **Accuracy** | Percentage correct (if feedback enabled) |

### Privacy Note

All statistics are stored locally. No data is sent externally.

---

## Troubleshooting

### Common Issues

#### "Backend not connected"

**Symptoms:** Red status indicator, "Backend not connected" error.

**Solutions:**
1. Verify Python is installed: `python --version`
2. Check the native messaging registration:
   - Windows: Run `register.bat` again
   - Linux/macOS: Run `register.sh` again
3. Verify `app_manifest.json` has the correct path
4. Restart Thunderbird

#### "LLM provider unreachable"

**Symptoms:** Yellow status, classification fails.

**For Ollama:**
1. Ensure Ollama is running: `ollama serve`
2. Check the URL in settings (default: `http://localhost:11434`)
3. Verify the model is downloaded: `ollama list`

**For Cloud Providers:**
1. Check internet connection
2. Verify API key is correct
3. Check API rate limits on provider dashboard

#### "Model not found"

**Solutions:**
1. Ollama: `ollama pull <modelname>`
2. Settings: Verify the model name matches exactly

#### Email stuck in Inbox

**Possible causes:**
1. Confidence below threshold (check logs)
2. Folder not mapped for the category
3. LLM returned unknown category

**Solution:** Check logs in `~/.mailsorter/logs/` or enable Debug Mode in settings.

#### High CPU/Memory Usage

**For Ollama users:**
1. Use a smaller model (e.g., `mistral` instead of `llama3:70b`)
2. Reduce concurrent requests in settings
3. Enable batch mode for bulk operations

### Debug Mode

Enable detailed logging:

1. Go to **Settings** → **Advanced**
2. Toggle **Debug Mode** on
3. Logs are saved to `~/.mailsorter/logs/`
4. Share logs (sanitized) when reporting issues

### Checking Logs

**Location:**
- Windows: `%USERPROFILE%\.mailsorter\logs\`
- Linux/macOS: `~/.mailsorter/logs/`

**Log Levels:**
- `INFO` - Normal operations
- `WARNING` - Non-critical issues
- `ERROR` - Failures (check these first)
- `DEBUG` - Detailed trace (when Debug Mode enabled)

---

## FAQ

### General

**Q: Is my email data sent to the cloud?**

A: It depends on your provider:
- **Ollama**: No, all processing is local
- **Cloud providers**: Yes, subject and truncated body (2000 chars) are sent
- **Headers-Only mode**: Only metadata (subject, from, date) is sent

**Q: Can I use MailSorter offline?**

A: Yes, with Ollama. Cloud providers require internet.

**Q: Does MailSorter read my attachments?**

A: No. Only attachment metadata (filename, size, type) is used for heuristics. Attachment content is never read.

### Privacy

**Q: What data is stored?**

A: 
- Configuration (locally)
- Statistics (locally, anonymized)
- Logs (locally, can be disabled)
- Feedback history (if enabled, locally only)

**Q: Is MailSorter GDPR compliant?**

A: Yes. See [RGPD.md](RGPD.md) for details. Key points:
- Data minimization (2000 char limit, PII scrubbing)
- No data retention beyond classification
- Right to disable (Passive Mode)
- Right to delete (uninstall removes all data)

### Performance

**Q: How long does classification take?**

A: 
- Ollama: 1-5 seconds (depends on hardware)
- Cloud: 0.5-2 seconds (depends on network)

**Q: Can I use MailSorter with thousands of emails?**

A: Yes! Use bulk sorting with batch mode for best performance.

### Compatibility

**Q: Does it work with IMAP accounts?**

A: Yes, MailSorter works with any email account configured in Thunderbird.

**Q: What about Exchange/Office 365?**

A: Yes, if configured in Thunderbird via IMAP or Exchange add-on.

---

## Privacy & Security

MailSorter is designed with privacy as a core principle:

### Data Handling

1. **PII Scrubbing**: Email addresses, phone numbers, IPs are removed before LLM processing
2. **Truncation**: Body is limited to 2000 characters
3. **No Storage**: Emails are not stored by the extension
4. **Local Stats**: All statistics stay on your machine

### Security Features

1. **Keyring Storage**: API keys stored in OS secure storage, not config files
2. **HMAC Signatures**: Optional signing of classification headers
3. **CSP Enforced**: No inline scripts in extension
4. **Input Sanitization**: Protection against prompt injection

### Audit

See [RGPD_AUDIT.md](RGPD_AUDIT.md) for the complete security and privacy audit.

---

## Getting Help

### Resources

- **Documentation**: [docs/](https://github.com/RomainROCH/MailSorter/tree/main/docs)
- **Issues**: [GitHub Issues](https://github.com/RomainROCH/MailSorter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/RomainROCH/MailSorter/discussions)

### Reporting Bugs

When reporting a bug, please include:

1. MailSorter version
2. Thunderbird version
3. Operating system
4. LLM provider and model
5. Error message (from logs if available)
6. Steps to reproduce

**Important:** Sanitize any logs before sharing (remove email addresses, API keys).

### Security Issues

For security vulnerabilities, please see [SECURITY.md](../SECURITY.md) for responsible disclosure.

---

## Appendix

### Supported Models

#### Ollama (Local)

| Model | Size | Quality | Speed |
|-------|------|---------|-------|
| `llama3` | 4.7 GB | High | Medium |
| `llama3:8b` | 4.7 GB | High | Medium |
| `llama3:70b` | 40 GB | Very High | Slow |
| `mistral` | 4.1 GB | High | Fast |
| `mixtral` | 26 GB | Very High | Medium |
| `phi3` | 2.2 GB | Good | Very Fast |
| `gemma2` | 5.4 GB | High | Medium |

#### Cloud Providers

| Provider | Model | Quality | Cost |
|----------|-------|---------|------|
| OpenAI | `gpt-4o-mini` | High | $ |
| OpenAI | `gpt-4o` | Very High | $$$ |
| Anthropic | `claude-3-haiku` | High | $ |
| Anthropic | `claude-3-sonnet` | Very High | $$ |
| Google | `gemini-2.0-flash` | High | $ |
| Google | `gemini-2.5-pro` | Very High | $$ |

### File Locations

| File | Windows | Linux/macOS |
|------|---------|-------------|
| Config | `%APPDATA%\MailSorter\` | `~/.config/mailsorter/` |
| Logs | `%USERPROFILE%\.mailsorter\logs\` | `~/.mailsorter/logs/` |
| Extension Storage | Thunderbird profile | Thunderbird profile |

---

*Happy sorting! 📧✨*
