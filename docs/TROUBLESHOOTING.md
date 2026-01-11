# MailSorter Troubleshooting Guide

> Quick solutions to common problems

---

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Classification Problems](#classification-problems)
3. [Performance Issues](#performance-issues)
4. [Installation Problems](#installation-problems)
5. [Provider-Specific Issues](#provider-specific-issues)
6. [Extension Issues](#extension-issues)
7. [Diagnostic Commands](#diagnostic-commands)
8. [Getting Support](#getting-support)

---

## Connection Issues

### Backend Not Connected

**Symptoms:**
- Red status indicator
- "Backend not connected" error
- Extension shows disconnected state

**Diagnosis:**

1. **Check Python installation:**
   ```bash
   python --version  # Should be 3.10+
   ```

2. **Verify native messaging registration:**
   
   Windows:
   ```cmd
   reg query "HKCU\Software\Mozilla\NativeMessagingHosts\com.mailsorter.backend"
   ```
   
   Linux:
   ```bash
   cat ~/.mozilla/native-messaging-hosts/com.mailsorter.backend.json
   ```
   
   macOS:
   ```bash
   cat ~/Library/Application\ Support/Mozilla/NativeMessagingHosts/com.mailsorter.backend.json
   ```

3. **Test the backend directly:**
   ```bash
   cd /path/to/MailSorter/backend
   echo '{"action":"health"}' | python main.py
   ```

**Solutions:**

| Problem | Solution |
|---------|----------|
| Python not found | Install Python 3.10+ and add to PATH |
| Registry key missing | Run `installers/register.bat` (Windows) |
| Manifest path wrong | Edit `app_manifest.json` with correct absolute path |

## Windows: Native host "Native request timed out"

On Windows, the native messaging host **must be an executable** that speaks the Native Messaging protocol over stdin/stdout.

If the Options page shows `Native request timed out`, install the native host using the provided script:

- Build (dev): `powershell -ExecutionPolicy Bypass -File scripts\\build_native_host_windows.ps1`
- Install/register: `powershell -ExecutionPolicy Bypass -File installers\\install_windows.ps1`

Then restart Thunderbird/Betterbird.
| Permissions issue | `chmod +x backend/main.py` (Linux/macOS) |
| Missing dependencies | `pip install -r backend/requirements.txt` |

### LLM Provider Unreachable

**Symptoms:**
- Yellow status indicator
- "Provider unreachable" or timeout errors
- Classification fails but backend is connected

**For Ollama:**

1. **Check if Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```
   
2. **Start Ollama if not running:**
   ```bash
   ollama serve
   ```

3. **Verify model is installed:**
   ```bash
   ollama list
   ```

4. **Check URL in settings:**
   - Default: `http://localhost:11434`
   - If using Docker: `http://host.docker.internal:11434`

**For Cloud Providers:**

1. Check internet connectivity
2. Verify API key is valid (not expired/revoked)
3. Check provider status page:
   - [OpenAI Status](https://status.openai.com)
   - [Anthropic Status](https://status.anthropic.com)
   - [Google Cloud Status](https://status.cloud.google.com)

---

## Classification Problems

### Email Not Being Sorted

**Symptoms:**
- Email stays in Inbox
- No error message
- Status shows "Processing" then nothing happens

**Possible Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Confidence below threshold | Lower the threshold in Settings → Folder Mapping |
| Category not mapped | Map the category to a folder in Settings |
| Passive Mode enabled | Disable Passive Mode in popup menu |
| Account excluded | Check account settings in extension |

**How to check confidence:**
1. Enable Debug Mode in Settings → Advanced
2. Check logs at `~/.mailsorter/logs/`
3. Look for `confidence: 0.XX` entries

### Wrong Classification

**Symptoms:**
- Emails sorted to wrong folders
- Consistent misclassification of certain email types

**Solutions:**

1. **Adjust thresholds:**
   - Increase threshold for folders receiving wrong emails
   - Example: If work emails go to Personal, increase Personal threshold

2. **Check folder mapping:**
   - Ensure categories map to the right folders
   - Some categories overlap (e.g., "Professional" vs "Work")

3. **Try a different model:**
   - Larger models generally classify better
   - `llama3:70b` > `llama3:8b` > `phi3`

4. **Use feedback (if available):**
   - Move misclassified emails manually
   - System learns from corrections (Ollama only)

### Model Returning Unknown Category

**Symptoms:**
- Logs show category not in folder list
- Email stays in Inbox despite high confidence

**Solution:**
1. Check the categories in your folder mapping
2. Ensure prompt template includes all your folder names
3. Update templates in `backend/templates/`

---

## Performance Issues

### Slow Classification

**Symptoms:**
- Classification takes >10 seconds
- High CPU/GPU usage during processing

**For Ollama (Local):**

| Cause | Solution |
|-------|----------|
| Large model | Switch to smaller model (`mistral`, `phi3`) |
| No GPU acceleration | Enable GPU in Ollama config |
| Insufficient RAM | Close other applications or use smaller model |
| CPU throttling | Check power settings (Windows: High Performance) |

**For Cloud Providers:**

| Cause | Solution |
|-------|----------|
| Network latency | Check internet speed |
| API rate limits | Reduce request frequency in settings |
| Provider congestion | Wait or try at different time |

### High Memory Usage

**Symptoms:**
- System slowdown when MailSorter active
- Ollama using >8GB RAM

**Solutions:**

1. **Use quantized models:**
   ```bash
   ollama pull llama3:8b-q4_0  # 4-bit quantization
   ```

2. **Limit context window:**
   - Reduce body truncation limit in config
   - Use Headers-Only mode

3. **Enable batch mode:**
   - Groups multiple emails for efficiency
   - Settings → Advanced → Batch Processing

### Rate Limiting Errors

**Symptoms:**
- "Rate limit exceeded" errors
- 429 HTTP status codes
- Temporary classification failures

**Solutions:**

1. **Built-in rate limiter:**
   - MailSorter limits to 10 req/min by default
   - Adjust in config if needed

2. **Use batch mode for bulk operations:**
   - More efficient API usage
   - Respects provider rate limits

3. **Upgrade API plan:**
   - Higher tiers have higher rate limits

---

## Installation Problems

### Windows Registry Error

**Symptoms:**
- `register.bat` fails
- "Access denied" error

**Solutions:**

1. **Run as Administrator:**
   - Right-click `register.bat` → Run as administrator

2. **Use per-user key (no admin needed):**
   - The script uses `HKCU` by default which doesn't require admin
   - Check if antivirus is blocking

3. **Manual registration:**
   ```cmd
   reg add "HKCU\Software\Mozilla\NativeMessagingHosts\com.mailsorter.backend" /ve /t REG_SZ /d "C:\MailSorter\backend\app_manifest.json" /f
   ```

### Python Dependencies Fail

**Symptoms:**
- `pip install` errors
- Import errors in logs

**Solutions:**

1. **Use virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Upgrade pip:**
   ```bash
   python -m pip install --upgrade pip
   ```

3. **Install build tools:**
   
   Windows:
   ```cmd
   # Install Visual Studio Build Tools
   ```
   
   Linux:
   ```bash
   sudo apt install python3-dev build-essential
   ```

### Extension Won't Load

**Symptoms:**
- Extension not visible in Thunderbird
- "Extension could not be loaded" error

**Solutions:**

1. **Check Thunderbird version:**
   - Requires Thunderbird 115+
   - Check: Help → About Thunderbird

2. **Verify XPI integrity:**
   - Re-download if corrupted
   - Check file size matches release

3. **Load unpacked for debugging:**
   - Menu → Add-ons → Debug Add-ons
   - Load Temporary Add-on → select `manifest.json`

---

## Provider-Specific Issues

### Ollama

#### Model Download Stuck

```bash
# Cancel and retry
Ctrl+C
ollama pull llama3 --resume
```

#### CUDA/GPU Not Detected

```bash
# Check GPU support
ollama run llama3 --verbose

# Install CUDA drivers if needed
# Visit: https://developer.nvidia.com/cuda-downloads
```

#### Port Already in Use

```bash
# Find process using 11434
# Windows:
netstat -ano | findstr :11434

# Linux/macOS:
lsof -i :11434

# Change Ollama port
OLLAMA_HOST=127.0.0.1:11435 ollama serve
```

### OpenAI

#### Invalid API Key

1. Check key starts with `sk-`
2. Verify key in [OpenAI Dashboard](https://platform.openai.com/api-keys)
3. Regenerate if compromised

#### Insufficient Quota

1. Check billing at [OpenAI Billing](https://platform.openai.com/account/billing)
2. Add payment method or credits
3. Check usage limits

### Anthropic

#### API Key Format

1. Keys start with `sk-ant-`
2. Verify at [Anthropic Console](https://console.anthropic.com/)

#### Model Access

1. Some models require approval
2. Check available models in console

### Gemini

#### API Key Setup

1. Create at [Google AI Studio](https://aistudio.google.com/)
2. Enable the Generative AI API
3. Check quota limits

---

## Extension Issues

### Popup Not Opening

**Solutions:**
1. Click directly on the MailSorter icon
2. Check if extension is enabled
3. Restart Thunderbird

### Settings Not Saving

**Solutions:**
1. Check storage permissions in manifest
2. Clear extension storage and reconfigure
3. Check for JavaScript errors (Debug Add-ons)

### Keyboard Shortcuts Not Working

**Solutions:**
1. Check for conflicts (other extensions)
2. Reassign in Thunderbird's shortcut settings
3. Restart Thunderbird after changes

### UI Not Displaying Correctly

**Solutions:**
1. Disable other extensions to check conflicts
2. Reset zoom level in Thunderbird
3. Check for dark mode compatibility

---

## Diagnostic Commands

### Quick Health Check

```bash
cd /path/to/MailSorter

# Python version
python --version

# Dependencies installed
pip list | grep -E "requests|jsonschema|keyring"

# Backend test
python -c "from backend.core import orchestrator; print('OK')"

# Ollama check
curl http://localhost:11434/api/tags
```

### Log Analysis

```bash
# View recent logs
# Windows:
type %USERPROFILE%\.mailsorter\logs\mailsorter.log | more

# Linux/macOS:
tail -100 ~/.mailsorter/logs/mailsorter.log

# Search for errors
grep -i "error\|exception" ~/.mailsorter/logs/mailsorter.log
```

### Test Classification

```bash
# Send test request to backend
cd /path/to/MailSorter/backend
python -c "
from core.orchestrator import Orchestrator
o = Orchestrator()
result = o.classify({
    'subject': 'Test invoice from Acme Corp',
    'from': 'billing@acme.com',
    'body': 'Please find attached your invoice for January.'
})
print(result)
"
```

### Generate Support Bundle

```bash
# Collect diagnostic info (sanitized)
cd /path/to/MailSorter

# System info
echo "=== System ===" > support_bundle.txt
python --version >> support_bundle.txt
pip list >> support_bundle.txt

# Config (sanitized)
echo "=== Config ===" >> support_bundle.txt
cat backend/config.json | grep -v "api_key" >> support_bundle.txt

# Recent logs (last 50 lines)
echo "=== Logs ===" >> support_bundle.txt
tail -50 ~/.mailsorter/logs/mailsorter.log >> support_bundle.txt
```

---

## Getting Support

### Before Asking for Help

1. ✅ Check this troubleshooting guide
2. ✅ Enable Debug Mode and check logs
3. ✅ Try restarting Thunderbird
4. ✅ Try restarting the LLM provider

### Where to Get Help

- **GitHub Issues**: [Report a bug](https://github.com/RomainROCH/MailSorter/issues/new?template=bug_report.md)
- **GitHub Discussions**: [Ask a question](https://github.com/RomainROCH/MailSorter/discussions)
- **Documentation**: [Full docs](https://github.com/RomainROCH/MailSorter/tree/main/docs)

### Information to Include

When reporting an issue, please provide:

```
**MailSorter Version:** X.Y.Z
**Thunderbird Version:** X.Y.Z
**OS:** Windows 11 / Ubuntu 22.04 / macOS 14
**LLM Provider:** Ollama / OpenAI / etc.
**Model:** llama3 / gpt-4o-mini / etc.

**Steps to reproduce:**
1. ...
2. ...
3. ...

**Expected behavior:**
...

**Actual behavior:**
...

**Logs (sanitized):**
```

### Security Issues

⚠️ **Do NOT report security vulnerabilities in public issues!**

See [SECURITY.md](../SECURITY.md) for responsible disclosure process.

---

*Still stuck? Open a [GitHub Discussion](https://github.com/RomainROCH/MailSorter/discussions) and we'll help!*
