# MailSorter - Copilot Instructions

## 🚨 MANDATORY: Git Branching Rules

> **STOP! READ THIS BEFORE MAKING ANY CODE CHANGES.**

### Branch Model

| Branch | Purpose | Can I commit here? |
|--------|---------|-------------------|
| `main` | 🏭 Production (stable) | ❌ **NEVER** |
| `develop` | 🔧 Integration | ❌ **NEVER** |
| `feat/*`, `fix/*`, `chore/*` | Your work | ✅ **YES** |

### Required Workflow

**Before ANY code change:**
```bash
# 1. Make sure you're on develop and up-to-date
git checkout develop
git pull origin develop

# 2. Create a feature branch
git checkout -b feat/your-feature-name   # or fix/, chore/
```

**After completing your work:**
```bash
# 3. Commit and push your branch
git add .
git commit -m "feat: description of changes"
git push origin feat/your-feature-name

# 4. Merge to develop (NOT to main!)
git checkout develop
git merge feat/your-feature-name
git push origin develop
```

**For production releases (human decision only):**
```bash
git checkout main
git merge develop
git tag vX.Y.Z
git push origin main --tags
```

### ⚠️ Why This Matters
- `main` must ALWAYS be deployable - users depend on it
- `develop` is where we test integrations
- Feature branches let us experiment safely

---

## Project Context

**MailSorter** is an intelligent email sorting system for Thunderbird/Betterbird using LLM.

### Key Files to Read First
1. `.instructions/architecture.md` - System architecture
2. `.instructions/contexts/project.memory.md` - Lessons learned & gotchas
3. `docs/PLAN_V5.md` - Full specification

### Tech Stack
- **Frontend**: Thunderbird WebExtension (JavaScript, Manifest V2)
- **Backend**: Python 3.10+ (Native Messaging Host)
- **LLM**: Ollama (local) or OpenAI API (cloud)

### Critical Rules
1. **No `print()` in Python backend** - Use `logger.info()` only (stdout breaks protocol)
2. **Privacy First** - Sanitize PII before sending to LLM
3. **Validate LLM output** - Always check folder exists before moving emails

---

## File Conventions

### Branch Naming
- `feat/TASK-ID-description` - New features
- `fix/TASK-ID-description` - Bug fixes
- `chore/description` - Maintenance

### Commit Messages
Follow Conventional Commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `chore:` - Maintenance
- `test:` - Tests
- `refactor:` - Code refactoring

---

## Testing

Before merging to develop:
```bash
cd backend
python -m pytest tests/ -v
```

---

## Remember

> **NEVER commit directly to `main` or `develop`. ALWAYS use feature branches.**
