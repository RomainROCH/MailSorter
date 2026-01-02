# Project Architecture
---
description: "High-level architecture overview for AI agents."
version: "2.0 - Plan V5"
last-updated: "2026-01-02"
---

> **Purpose**: This file gives AI agents quick context about your project structure.
> Keep it updated as architecture evolves. Agents read this before making changes.

## Overview
**MailSorter** - Système de tri d'emails intelligent pour Thunderbird/Betterbird via LLM.

**Architecture** : Hybride WebExtension (Frontend) + Python Native Messaging Host (Backend).

**Principe directeur** : Privacy First, RGPD-compliant, Model-Agnostic.

---

## Tech Stack

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| Frontend | Thunderbird WebExtension (JS) | Manifest V2 | API messages, accounts, folders |
| Backend | Python | 3.10+ | Native Messaging Host (stdio) |
| LLM Local | Ollama | Latest | Llama3, Mistral, etc. |
| LLM Cloud | OpenAI API (optionnel) | v1 | Via provider pattern |
| Privacy | Regex + (future: Presidio) | - | PII scrubbing avant LLM |
| Logs | Python logging | - | Rotating file, stderr only |
| Config | JSON | - | À externaliser (actuellement hardcodé) |

---

## Solution Structure

```
/MailSorter
├── extension/              # Frontend Thunderbird
│   ├── manifest.json
│   ├── background/         # Event listeners, Native client
│   └── options/            # UI de configuration
├── backend/                # Backend Python
│   ├── main.py             # Entry point (stdio loop)
│   ├── core/               # Orchestrateur, Privacy Guard
│   ├── providers/          # LLM adapters (Ollama, OpenAI)
│   └── utils/              # Logger, security
├── docs/                   # Documentation
│   ├── PLAN_V5.md          # Source de vérité
│   ├── ARCHITECTURE.md     # Architecture technique
│   └── RGPD.md             # Conformité
└── README.md               # Guide d'installation
```

---

## Key Components

### Component 1: Extension (Frontend)
- **Responsibility**: Capture des nouveaux emails, extraction métadonnées, déplacement
- **Location**: `extension/background/background.js`
- **Dependencies**: Thunderbird APIs (messages, accounts, folders), Native Messaging

### Component 2: Native Host (Backend)
- **Responsibility**: Traitement IA, privacy, orchestration
- **Location**: `backend/main.py` + `core/orchestrator.py`
- **Dependencies**: Python 3.10+, requests

### Component 3: Privacy Guard
- **Responsibility**: Scrubbing PII (emails, phones, IPs), troncature 2000 chars
- **Location**: `backend/core/privacy.py`
- **Dependencies**: re (regex), future: Presidio

### Component 4: LLM Providers (Model-Agnostic)
- **Responsibility**: Interface abstraite pour swapper les modèles
- **Location**: `backend/providers/base.py` (interface) + implémentations
- **Dependencies**: requests (HTTP API calls)

---

## Data Flow

1. **Trigger**: Email arrive → `messages.onNewMailReceived`
2. **Extract**: Subject, Body, Sender (via Thunderbird API)
3. **Send**: JSON vers Native Host (stdio)
4. **Sanitize**: Privacy Guard nettoie les PII
5. **Infer**: LLM Provider classifie (avec liste stricte de dossiers)
6. **Respond**: Backend renvoie décision (move/none)
7. **Execute**: Extension déplace le message

---

## Security Principles

- **No stdout pollution**: Logs uniquement sur stderr (Native Messaging strict)
- **API Keys**: Stockage via OS Keyring (jamais en clair)
- **PII Minimization**: Scrubbing avant toute transmission
- **Fallback**: Si LLM down ou hallucination, email reste dans Inbox

---

## Plan V5 Compliance

Voir [docs/PLAN_V5.md](../docs/PLAN_V5.md) pour la spec complète.

**Modules en développement** :
- Feature Detection (API TB)
- Mode Headers-Only
- Seuil dynamique par dossier
- Gestion attachments (hash, MIME)
- Signature HMAC headers
- Feedback loop local (fine-tuning Ollama) 

---

## Dependencies

### Internal
*Internal service dependencies.*

### External
*Third-party APIs and services.*

---

## Data Flow

### Core Flows
*Describe key data flows here.*

---

## Deployment

### Environments
- **Development**: Local
- **Staging**: TBD
- **Production**: TBD

### Configuration
*Environment-specific configuration approach.*

---

## Security

### Authentication
*Authentication approach.*

### Authorization
*Authorization model.*

### Secrets Management
*How secrets are managed.*

---

## Observability

### Logging
*Logging approach.*

### Monitoring
*Monitoring and alerting.*

### Tracing
*Distributed tracing approach.*

---

## Notes
- Project initialized on 2026-01-02
- Empty project - architecture to be defined as development progresses
