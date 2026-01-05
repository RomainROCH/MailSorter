# .github/skills/

This directory contains **project-specific skills** for the MailSorter project.

## Purpose

Skills are reusable AI agent workflows specific to this project. They extend the generic skills from `instruction-engine/.github/skills/`.

## When to Add Skills Here

- Project-specific workflows (e.g., email sorting logic)
- Custom integration patterns (e.g., email provider APIs)
- Domain-specific operations (e.g., rule validation)

## Skill Format

Each skill should be in its own directory with a `SKILL.md` file:
```
.github/skills/
├── email-sorting/
│   └── SKILL.md
├── provider-integration/
│   └── SKILL.md
└── README.md
```

Skill format:
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

## Skill Builder

Use the skill-builder agent to create new skills:
```
@skill-builder create a skill for [description]
```

## Notes

- This directory **is Git-tracked** (shareable across team)
- Skills here override generic skills with the same name
- Follow the naming convention: lowercase with hyphens
- One skill per directory
