# MailSorter Compatibility Matrix

> Reference for supported Thunderbird versions and feature availability

---

## Email Client Compatibility

### Thunderbird

| Version | Status | Notes |
|---------|--------|-------|
| **128.x** (ESR) | ✅ Full Support | Latest ESR, recommended |
| **115.x** (ESR) | ✅ Full Support | Minimum required version |
| **102.x** (ESR) | ⚠️ Limited | Missing some APIs, use fallback mode |
| **91.x** and older | ❌ Not Supported | WebExtension APIs incompatible |

### Betterbird

| Version | Status | Notes |
|---------|--------|-------|
| **115.x based** | ✅ Full Support | Matches Thunderbird 115 APIs |
| **102.x based** | ⚠️ Limited | Same limitations as TB 102 |

---

## Feature Support by Thunderbird Version

| Feature | TB 115+ | TB 102 | Notes |
|---------|---------|--------|-------|
| **Core Classification** | ✅ | ✅ | All versions |
| **Auto-sort new mail** | ✅ | ✅ | `messages.onNewMailReceived` |
| **Move messages** | ✅ | ✅ | `messages.move` |
| **Custom headers read** | ✅ | ⚠️ | TB 102 may have issues |
| **Custom headers write** | ✅ | ❌ | Falls back to tags |
| **Tags fallback** | ✅ | ✅ | `messages.update({tags})` |
| **Folder listing** | ✅ | ✅ | `folders.getSubFolders` |
| **Native messaging** | ✅ | ✅ | All versions |
| **Notifications** | ✅ | ✅ | `notifications.create` |
| **Keyboard shortcuts** | ✅ | ✅ | `commands` API |
| **Context menus** | ✅ | ✅ | `menus` API |
| **Dark mode detection** | ✅ | ⚠️ | Limited in TB 102 |
| **Browser action popup** | ✅ | ✅ | All versions |
| **Options page** | ✅ | ✅ | All versions |
| **Storage API** | ✅ | ✅ | `storage.local` |

### Legend
- ✅ Full support
- ⚠️ Partial/Limited support
- ❌ Not supported (fallback used)

---

## Operating System Compatibility

### Windows

| Version | Status | Python | Notes |
|---------|--------|--------|-------|
| **Windows 11** | ✅ Full | 3.10+ | Recommended |
| **Windows 10** (21H2+) | ✅ Full | 3.10+ | Supported |
| **Windows 10** (older) | ⚠️ Limited | 3.10+ | May need updates |
| **Windows 8.1** | ⚠️ Limited | 3.9 | Not tested |
| **Windows 7** | ❌ Not Supported | - | Python 3.10 not available |

### Linux

| Distribution | Status | Notes |
|--------------|--------|-------|
| **Ubuntu 22.04+** | ✅ Full | Recommended |
| **Ubuntu 20.04** | ✅ Full | Python 3.10 via PPA |
| **Debian 12 (Bookworm)** | ✅ Full | Python 3.11 default |
| **Debian 11 (Bullseye)** | ⚠️ Limited | Python 3.9, needs upgrade |
| **Fedora 38+** | ✅ Full | Python 3.11+ default |
| **Arch Linux** | ✅ Full | Rolling release |
| **openSUSE Leap 15.5+** | ✅ Full | Python 3.10+ |
| **RHEL/CentOS 9** | ✅ Full | Python 3.9 (3.11 available) |
| **RHEL/CentOS 8** | ⚠️ Limited | Python 3.8 default |

### macOS

| Version | Status | Notes |
|---------|--------|-------|
| **macOS 14 (Sonoma)** | ✅ Full | Python via Homebrew |
| **macOS 13 (Ventura)** | ✅ Full | Python via Homebrew |
| **macOS 12 (Monterey)** | ✅ Full | Minimum recommended |
| **macOS 11 (Big Sur)** | ⚠️ Limited | Older Homebrew |
| **macOS 10.15 and older** | ❌ Not Supported | EOL |

---

## Python Compatibility

| Python Version | Status | Notes |
|----------------|--------|-------|
| **3.13** | ✅ Full | Latest, recommended |
| **3.12** | ✅ Full | Recommended |
| **3.11** | ✅ Full | Recommended |
| **3.10** | ✅ Full | Minimum required |
| **3.9** | ⚠️ Limited | May work, not tested |
| **3.8 and older** | ❌ Not Supported | Missing type hints |
| **2.x** | ❌ Not Supported | EOL |

---

## LLM Provider Compatibility

### Ollama (Local)

| Ollama Version | Status | Notes |
|----------------|--------|-------|
| **0.5.x** | ✅ Full | Latest, recommended |
| **0.4.x** | ✅ Full | Supported |
| **0.3.x** | ⚠️ Limited | API changes |
| **0.2.x and older** | ❌ Not Supported | Missing APIs |

### Supported Local Models

| Model | Parameters | RAM Required | Quality | Speed |
|-------|------------|--------------|---------|-------|
| `llama3.3` | 70B | 40GB+ | ★★★★★ | Slow |
| `llama3.2` | 3B | 4GB | ★★★☆☆ | Fast |
| `llama3.1` | 8B/70B | 8GB/40GB | ★★★★☆ | Medium |
| `llama3` | 8B | 8GB | ★★★★☆ | Medium |
| `mistral` | 7B | 8GB | ★★★★☆ | Fast |
| `mixtral` | 8x7B | 32GB | ★★★★★ | Medium |
| `phi3` | 3.8B | 4GB | ★★★☆☆ | Very Fast |
| `gemma2` | 9B/27B | 8GB/20GB | ★★★★☆ | Medium |
| `qwen2.5` | 7B/72B | 8GB/48GB | ★★★★☆ | Medium |
| `deepseek-r1` | 7B/70B | 8GB/40GB | ★★★★☆ | Medium |

### Cloud Providers

| Provider | API Version | Status | Models |
|----------|-------------|--------|--------|
| **OpenAI** | v1 | ✅ Full | gpt-4o, gpt-4o-mini, gpt-4-turbo |
| **Anthropic** | 2024-01 | ✅ Full | claude-3.5-sonnet, claude-3-haiku |
| **Google Gemini** | v1 | ✅ Full | gemini-2.5-pro, gemini-2.0-flash |
| **Azure OpenAI** | 2024-02 | ⚠️ Planned | via OpenAI provider |
| **AWS Bedrock** | - | ⚠️ Planned | Future support |
| **Groq** | - | ⚠️ Planned | Future support |

---

## Browser/Extension API Compatibility

### Required Manifest Permissions

| Permission | Purpose | Minimum TB Version |
|------------|---------|-------------------|
| `messagesRead` | Read email content | 78 |
| `messagesModify` | Modify headers/tags | 78 |
| `messagesMove` | Move emails to folders | 78 |
| `accountsRead` | List email accounts | 78 |
| `foldersRead` | List folders | 91 |
| `nativeMessaging` | Communicate with Python | 78 |
| `storage` | Save settings | 78 |
| `notifications` | Show alerts | 78 |
| `menus` | Context menus | 88 |
| `tabs` | Open options page | 78 |

### API Availability

| API | TB 115+ | TB 102 | TB 91 |
|-----|---------|--------|-------|
| `messages.getFull()` | ✅ | ✅ | ✅ |
| `messages.update()` | ✅ | ⚠️ | ⚠️ |
| `messages.move()` | ✅ | ✅ | ✅ |
| `messages.listTags()` | ✅ | ✅ | ✅ |
| `folders.getSubFolders()` | ✅ | ✅ | ⚠️ |
| `accounts.list()` | ✅ | ✅ | ✅ |

---

## Hardware Requirements

### Minimum (Cloud LLM)

| Component | Requirement |
|-----------|-------------|
| CPU | Dual-core 2GHz |
| RAM | 4 GB |
| Disk | 500 MB |
| Network | Broadband internet |

### Recommended (Local LLM - Small Models)

| Component | Requirement |
|-----------|-------------|
| CPU | Quad-core 3GHz |
| RAM | 16 GB |
| Disk | 20 GB (models + app) |
| GPU | Optional (NVIDIA 4GB+ VRAM) |

### Optimal (Local LLM - Large Models)

| Component | Requirement |
|-----------|-------------|
| CPU | 8+ cores |
| RAM | 32 GB+ |
| Disk | 100 GB SSD |
| GPU | NVIDIA RTX 3080+ (12GB+ VRAM) |

---

## Known Limitations

### Thunderbird 102 Specific

1. **Custom headers may not persist** - Use tags fallback
2. **Some notification styles unavailable** - Basic notifications work
3. **Dark mode detection inconsistent** - May need manual toggle

### Linux Specific

1. **Wayland clipboard issues** - Use X11 fallback if needed
2. **Flatpak Thunderbird** - Native messaging requires extra configuration
3. **Snap Thunderbird** - May have path issues with Python

### macOS Specific

1. **Gatekeeper warnings** - May need to allow in Security settings
2. **Apple Silicon** - Use ARM Python for best performance
3. **Keychain access** - Grant permission for API key storage

### Windows Specific

1. **Antivirus interference** - Whitelist MailSorter directory
2. **Long paths** - Enable long path support if installation path is deep
3. **UAC prompts** - Registration script may trigger UAC

---

## Testing Matrix

MailSorter is tested on the following configurations:

| Configuration | Frequency | Status |
|---------------|-----------|--------|
| Windows 11 + TB 128 + Ollama | Per release | ✅ |
| Windows 10 + TB 115 + OpenAI | Per release | ✅ |
| Ubuntu 22.04 + TB 128 + Ollama | Per release | ✅ |
| Ubuntu 22.04 + TB 115 + OpenAI | Per release | ✅ |
| macOS 14 (ARM) + TB 128 + Ollama | Per release | ✅ |
| macOS 13 (Intel) + TB 115 + Anthropic | Per release | ✅ |
| Debian 12 + Betterbird 115 | Major releases | ✅ |
| Fedora 39 + TB 128 + Gemini | Major releases | ✅ |

---

## Reporting Compatibility Issues

If you encounter compatibility issues not listed here:

1. Check [GitHub Issues](https://github.com/RomainROCH/MailSorter/issues) for existing reports
2. Open a new issue with:
   - OS version
   - Thunderbird version
   - Python version
   - LLM provider and model
   - Error messages/logs

---

*Last updated: January 2026*
