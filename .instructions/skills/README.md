# .instructions/skills/

This directory is for **legacy skill overrides** only. 

## Recommended: Use `.github/skills/` instead

For new projects, it's recommended to place project-specific skills in:
```
.github/skills/
```

This location:
- ✅ Is Git-tracked (shareable across team)
- ✅ Follows VS Code Copilot conventions
- ✅ Integrates with the lazy-loading system

## When to use `.instructions/skills/`

Use this directory only for:
- **Temporary local overrides** of shared skills
- **Developer-specific experimentation** (not committed to Git)
- **Migration period** (while transitioning to `.github/skills/`)

## Skill Format

Skills should follow the `SKILL.md` format:
```markdown
---
name: skill-name
description: "What this skill does"
tools: ['read', 'edit', 'search']
---

# Skill Name

## Inputs
...

## Steps
...

## Output
...
```

## Notes
- Skill file names must be lowercase with hyphens
- One skill per directory
- Use the skill-builder agent to create new skills
