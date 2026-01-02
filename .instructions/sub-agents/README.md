# .instructions/sub-agents/

This directory is for **project-specific sub-agents**.

## Purpose

Sub-agents are specialized agents that extend the base instruction-engine agents with project-specific behavior.

## Structure

Each sub-agent should be in its own file:
```
.instructions/sub-agents/
├── mailsorter.rules.agent.md      # Example: email sorting rules agent
├── mailsorter.providers.agent.md  # Example: email provider integration agent
└── README.md
```

## Agent Format

Sub-agents should follow the agent format:
```markdown
---
name: agent-name
description: "What this agent does"
tools: ['read', 'edit', 'search']
infer: false
---

# Agent Name

## Inputs
- What the agent needs

## Steps
1. What the agent does
2. ...

## Output
- What the agent produces
```

## Usage

Reference sub-agents with:
```
@agent-name
```

## Notes
- This directory is **not Git-tracked** by default
- Sub-agents are for project-specific workflows only
- Generic agents belong in `instruction-engine/.github/agents/`
