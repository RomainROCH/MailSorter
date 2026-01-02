# Project Patterns & Conventions - MailSorter (Plan V5)

## Code Style
*Conventions de code strictes pour garantir la sécurité et la conformité.*

### Naming
- **Backend (Python)**: 
  - Files: `snake_case.py`
  - Classes: `PascalCase` (ex: `PrivacyGuard`)
  - Functions/Variables: `snake_case`
- **Frontend (JavaScript)**:
  - Files: `snake_case.js`
  - Classes: `PascalCase` (ex: `NativeClient`)
  - Functions/Variables: `camelCase`

### Structure
- **Backend**: `backend/<domain>/<module>.py` (ex: `backend/core/privacy.py`)
- **Extension**: `extension/<type>/<file>.js` (ex: `extension/background/background.js`)
- **Import order**: 
  1. Standard library
  2. Third-party
  3. Local imports

---

## Architectural Patterns

### Pattern 1: Provider Pattern (LLM Abstraction)
- **Use Case**: Permettre le swap de modèles LLM sans modifier le core
- **Implementation**: Interface abstraite `LLMProvider` avec `classify_email()` et `health_check()`
- **Example**: `OllamaProvider`, `OpenAIProvider`, `GeminiProvider`

### Pattern 2: Privacy-First Pipeline
- **Use Case**: Garantir RGPD et minimisation données
- **Implementation**: Tout texte passe par `PrivacyGuard.sanitize()` avant LLM
- **Example**: `orchestrator.py` appelle `privacy_guard.sanitize()` systématiquement

### Pattern 3: Feature Detection + Fallback
- **Use Case**: Robustesse API Thunderbird (versions différentes)
- **Implementation**: `typeof browser.api !== 'undefined'` avant usage
- **Example**: Si `messages.update()` indispo → Utiliser IMAP flags

---

## Testing Patterns

### Test Organization
- `tests/unit/` : Tests unitaires (Privacy, Providers)
- `tests/integration/` : Tests E2E (Extension ↔ Backend)
- `tests/benchmark/` : Scripts de benchmark sur datasets publics

### Test Naming
- `test_<fonction>_<cas>.py` (ex: `test_privacy_scrubs_email.py`)

### Mocking Strategy
- Mock HTTP responses pour tester Providers sans appel réel
- Mock Thunderbird API pour tester Extension en isolation

---

## Error Handling

### Error Types
- **Backend**: Exceptions Python loggées sur stderr, jamais de print()
- **Extension**: try/catch autour des appels API TB, notification user si critique

### Error Propagation
- **Backend**: Retourne JSON structuré `{"status": "error", "error": "description"}`
- **Extension**: Affiche notification TB ou passe en Mode Passif

### User-Facing Errors
- Messages clairs en FR/EN selon locale
- Pas de stacktraces exposées (logs uniquement)

---

## Logging

### ⚠️ RÈGLE CRITIQUE
> **JAMAIS de `print()` dans le backend Python** → Casse le protocole Native Messaging

### Log Levels
- **INFO**: Flux normal (email traité, décision prise)
- **WARNING**: Hallucination détectée, timeout
- **ERROR**: Provider down, exception critique

### Structured Logging
- Format: `YYYY-MM-DD HH:MM:SS - NAME - LEVEL - MESSAGE`
- Rotation: 5MB max, 3 backups
- Localisation: `~/.mailsorter/logs/backend.log`

### Interdictions RGPD
❌ **Ne jamais logger**:
- Contenu des emails (sujet ou body non sanitizés)
- Adresses email complètes
- Données PII non masquées

✅ **Logger uniquement**:
- Email ID
- Timestamp
- Décision (dossier cible ou "none")
- Erreurs techniques

---

## RGPD et Privacy

### Règle d'Or
> "Les données ne quittent la machine que si strictement nécessaire, et seulement après sanitization."

### Checklist par Fonctionnalité
1. Collecte de données → Justifier dans docs/RGPD.md
2. Traitement LLM → Scrubbing PII obligatoire
3. Stockage → Éphémère ou chiffré (Keyring pour secrets)
4. Logs → Métadonnées uniquement (ID, timestamp, décision)

---

## Anti-Patterns (À Éviter)

❌ **Hardcoder des seuils ou modèles** → Utiliser `backend/config.json`  
❌ **Logger du contenu email** → Violation RGPD  
❌ **Utiliser `print()` dans le backend** → Casse Native Messaging  
❌ **Ignorer les timeouts LLM** → Peut bloquer l'UI  
❌ **Stocker les clés API en clair** → Utiliser OS Keyring  
❌ **Parser le contenu des PJ** → Hors scope Plan V5, risque sécurité

---

## Notes
- Dernière mise à jour: 2026-01-02 (Plan V5)
- Toute exception aux patterns doit être documentée avec justification
- Référencer `docs/PLAN_V5.md` pour décisions architecturales
