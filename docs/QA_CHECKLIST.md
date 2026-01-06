# MailSorter QA Checklist

## Overview

This checklist is used for manual QA testing before releases. Complete each section and record results.

**Tester:** _______________  
**Date:** _______________  
**Version:** _______________  
**Platform:** Windows / macOS / Linux  
**Thunderbird Version:** _______________  

---

## 1. Installation Verification

### 1.1 Extension Installation
- [ ] Extension installs without errors
- [ ] Extension appears in Thunderbird add-ons manager
- [ ] Extension icon appears in toolbar
- [ ] Extension options page opens correctly

### 1.2 Backend Installation
- [ ] Python backend is present and accessible
- [ ] Native messaging host registration successful
- [ ] Backend starts without errors
- [ ] Backend logs to expected location

### 1.3 Configuration
- [ ] config.json created from example
- [ ] API keys stored securely (not in plaintext)
- [ ] Default folders configured correctly
- [ ] Provider selection works

**Notes:**
```
_______________________________________
```

---

## 2. Core Functionality

### 2.1 Ping/Pong Communication
- [ ] Extension can ping backend
- [ ] Pong response received correctly
- [ ] Connection status indicator updates

### 2.2 Email Classification
- [ ] Sample email classified correctly
- [ ] Classification confidence displayed
- [ ] Correct folder suggested
- [ ] Move action available

### 2.3 Folder Operations
- [ ] All folders listed correctly
- [ ] Folder names with special characters work
- [ ] Nested folders displayed properly

### 2.4 Multiple Providers
- [ ] Ollama (local) works if configured
- [ ] OpenAI works if API key provided
- [ ] Anthropic works if API key provided
- [ ] Provider switch works without restart

**Notes:**
```
_______________________________________
```

---

## 3. Privacy & Security

### 3.1 Data Handling
- [ ] PII redaction visible in logs (emails masked)
- [ ] Phone numbers redacted
- [ ] Body text truncated appropriately
- [ ] No sensitive data in console logs

### 3.2 Configuration Security
- [ ] API keys not exposed in UI
- [ ] API keys not in source control
- [ ] Keys stored in system keyring

### 3.3 Privacy Settings
- [ ] Passive mode toggle works
- [ ] Local-only mode available
- [ ] Cloud warning shown when applicable

**Notes:**
```
_______________________________________
```

---

## 4. Performance

### 4.1 Response Times
- [ ] First classification < 5 seconds
- [ ] Cached classification < 500ms
- [ ] UI remains responsive during classification

### 4.2 Resource Usage
- [ ] Memory usage stable over time
- [ ] No memory leaks observed (after 1 hour)
- [ ] CPU usage reasonable (< 5% idle)

### 4.3 High Volume
- [ ] 10 emails classified without issues
- [ ] 50 emails classified without issues
- [ ] Queue processed in order

**Notes:**
```
_______________________________________
```

---

## 5. Error Handling

### 5.1 Network Errors
- [ ] Timeout handled gracefully
- [ ] Provider unavailable shows error
- [ ] Retry logic works

### 5.2 Invalid Input
- [ ] Empty email handled
- [ ] Malformed email handled
- [ ] Very large email handled

### 5.3 Configuration Errors
- [ ] Invalid API key shows error
- [ ] Missing provider shows error
- [ ] Invalid config.json handled

**Notes:**
```
_______________________________________
```

---

## 6. User Interface

### 6.1 Popup
- [ ] Popup opens correctly
- [ ] Status shows connection state
- [ ] Statistics displayed
- [ ] Actions buttons work

### 6.2 Options Page
- [ ] All settings accessible
- [ ] Settings saved correctly
- [ ] Settings persist after restart
- [ ] Help links work

### 6.3 Statistics
- [ ] Stats page shows classification history
- [ ] Charts render correctly
- [ ] Export functionality works

**Notes:**
```
_______________________________________
```

---

## 7. Cross-Platform

### 7.1 Windows Specific
- [ ] Native host registration (registry)
- [ ] Path handling (backslashes)
- [ ] Terminal/PowerShell execution

### 7.2 macOS Specific
- [ ] Native host registration (plist)
- [ ] Path handling
- [ ] Keychain integration

### 7.3 Linux Specific
- [ ] Native host registration (manifest)
- [ ] Path handling
- [ ] Secret service integration

**Notes:**
```
_______________________________________
```

---

## 8. Localization

### 8.1 Multi-language Content
- [ ] French emails classified correctly
- [ ] German emails classified correctly
- [ ] Spanish emails classified correctly
- [ ] Japanese/Chinese emails handled

### 8.2 UI Translations (if applicable)
- [ ] UI displays in user's locale
- [ ] No untranslated strings visible

**Notes:**
```
_______________________________________
```

---

## 9. Edge Cases

### 9.1 Special Emails
- [ ] HTML-only email
- [ ] Multipart email
- [ ] Email with attachments
- [ ] Email with inline images
- [ ] Encrypted email (should skip or indicate)

### 9.2 Special Folders
- [ ] "Inbox" with various capitalizations
- [ ] Folders with unicode names
- [ ] Deeply nested folders (3+ levels)

**Notes:**
```
_______________________________________
```

---

## 10. Uninstallation

### 10.1 Clean Removal
- [ ] Extension uninstalls cleanly
- [ ] No orphan files left
- [ ] Native host unregistered
- [ ] User data removal option provided

**Notes:**
```
_______________________________________
```

---

## Test Summary

| Category | Passed | Failed | Skipped |
|----------|--------|--------|---------|
| Installation | __ / 12 | | |
| Core Functionality | __ / 11 | | |
| Privacy & Security | __ / 10 | | |
| Performance | __ / 9 | | |
| Error Handling | __ / 9 | | |
| User Interface | __ / 10 | | |
| Cross-Platform | __ / 9 | | |
| Localization | __ / 6 | | |
| Edge Cases | __ / 7 | | |
| Uninstallation | __ / 4 | | |
| **TOTAL** | __ / 87 | | |

## Issues Found

| # | Severity | Description | Steps to Reproduce |
|---|----------|-------------|-------------------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

## Sign-off

**QA Passed:** ☐ Yes ☐ No ☐ With Issues  
**Blocker Issues:** _______________  
**Approved for Release:** ☐ Yes ☐ No  

**Signatures:**
- QA Lead: _______________ Date: ___
- Dev Lead: _______________ Date: ___
