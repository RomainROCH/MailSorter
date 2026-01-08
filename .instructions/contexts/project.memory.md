# Project Memory & Lessons Learned - MailSorter (Plan V5)
---
description: "Persistent memory of project-specific patterns, anti-patterns, and recurring issues."
last-updated: "2026-01-08"
---

## 🚨 CRITICAL: Git Branching Rules (READ FIRST)

> **ALL AI AGENTS MUST FOLLOW THESE RULES. NO EXCEPTIONS.**

### ❌ NEVER DO THIS
- `git commit` directly on `main` → **FORBIDDEN**
- `git commit` directly on `develop` → **FORBIDDEN**
- `git push origin main` without going through `develop` → **FORBIDDEN**

### ✅ ALWAYS DO THIS
1. **Create a branch** for ANY change (feature, fix, chore):
   ```bash
   git checkout develop
   git checkout -b feat/descriptive-name   # or fix/, chore/
   ```
2. **Make your changes** and commit to your branch
3. **Push your branch** to origin:
   ```bash
   git push origin feat/descriptive-name
   ```
4. **Merge to develop** (integration branch):
   ```bash
   git checkout develop
   git merge feat/descriptive-name
   git push origin develop
   ```
5. **Delete your feature branch** after merge (optional but recommended)

### Branch Naming Convention
- `feat/TASK-ID-short-description` - New features
- `fix/TASK-ID-short-description` - Bug fixes  
- `chore/short-description` - Maintenance, refactoring

### Why?
- `main` = PRODUCTION = must ALWAYS work perfectly
- `develop` = Integration testing before production
- Feature branches = Safe isolation for experiments

---

## 🧠 Lessons Learned
*Record solutions to tricky problems here to avoid repeating mistakes.*

### Native Messaging Protocol Fragility
- **Problem**: Le moindre `print()` dans le backend Python casse le protocole (stdio binaire avec longueur préfixée).
- **Solution**: Tous les logs doivent utiliser `sys.stderr` uniquement. Logger créé dès le début du projet.
- **Anti-Pattern**: ❌ `print("Debug info")` → ✅ `logger.info("Debug info")`

### Thunderbird API Complexity (messages.getFull)
- **Problem**: L'API `messages.getFull()` retourne un objet MIME complexe, difficile à parser sans lib externe.
- **Solution**: V1 utilise sujet + extrait simplifié. Parser MIME complet prévu en V2 avec lib dédiée.
- **Anti-Pattern**: ❌ Essayer de parser manuellement les MIME parts → ✅ Utiliser une lib spécialisée

### LLM Hallucinations
- **Problem**: Même avec prompt strict, les LLM inventent des noms de dossiers.
- **Solution**: Validation post-traitement obligatoire. Vérifier que le dossier existe dans la liste fournie.
- **Anti-Pattern**: ❌ Faire confiance aveuglément à la réponse → ✅ Toujours valider contre la liste des dossiers

### API Key Storage Security
- **Problem**: Stocker les clés dans `localStorage` de l'extension = risque XSS/vol.
- **Solution**: Passer la clé une fois à l'init, la stocker côté Python dans le Keyring OS.
- **Anti-Pattern**: ❌ `localStorage.setItem("api_key", key)` → ✅ Keyring OS via Python

### RGPD Minimization
- **Problem**: Premiers tests envoyaient l'email complet au LLM (violation potentielle).
- **Solution**: Troncature à 2000 chars + scrubbing PII via Regex (Presidio prévu en V2).
- **Anti-Pattern**: ❌ Envoyer tout le contenu brut → ✅ Sanitize puis tronquer

---

## ⚠️ Gotchas
*Things that look correct but break this specific project.*

### Manifest V3 vs V2 Confusion
- **Gotcha**: Thunderbird supporte encore Manifest V2, contrairement à Chrome/Firefox (V3 obligatoire).
- **Action**: Rester sur Manifest V2 pour Thunderbird. Surveiller roadmap Mozilla.

### Ollama URL Non Standard
- **Gotcha**: Ollama peut tourner sur un port différent de `11434` selon config système.
- **Action**: Ne jamais hardcoder l'URL. Toujours externaliser dans `backend/config.json`.

### Cloud API Latency
- **Gotcha**: Les API Cloud peuvent mettre 1-3s (temps réel) ou jusqu'à 24h (Batch API).
- **Action**: Afficher indicateur de progression. Documenter distinction Batch vs Real-Time.

### Spam vs Phishing Confusion
- **Gotcha**: Les LLM génériques confondent spam (publicité) et phishing (fraude).
- **Action**: Ajouter contexte dans le prompt : "Spam = commercial. Phishing = usurpation/malveillant."

### Pièces Jointes Non Traitées
- **Gotcha**: Utilisateurs s'attendent à analyse des PJ (PDF de factures, etc.).
- **Action**: Documenter clairement dans README et UI que seuls hash/MIME sont collectés (pas de parsing contenu).

---

## 🚫 Ignored Warnings
*Warnings we have consciously decided to ignore.*

### Presidio Non Intégré en V1
- **Warning**: Regex seuls sont insuffisants pour détecter toutes les PII.
- **Justification**: Trade-off acceptable pour V1. Presidio prévu en V2 (tâche AUDIT-001).
- **Risque**: Faux négatifs sur PII non standards (ex : numéros INSEE FR).

### MIME Parsing Simplifié
- **Warning**: Ne traite pas les emails multipart/alternative complexes.
- **Justification**: Complexité technique élevée, impact limité sur précision observée.
- **Risque**: Emails HTML purs ou avec inline images mal traités.

---

## 🔄 Recurring Issues
*Problems that keep coming back.*

| Issue | Frequency | Root Cause | Workaround |
|-------|-----------|------------|------------|
| Ollama non démarré | Souvent (dev) | Service non lancé automatiquement | Vérifier `ollama serve` avant tests |
| Extension non connectée | Parfois | Manifest path incorrect | Vérifier chemin absolu dans `app_manifest.json` |
| Headers API indisponible | Rarement | Version TB ancienne | Feature detection + fallback IMAP flags |

---

## 📐 Architectural Decisions Log

### Pourquoi Hybride (Extension + Python) ?
- **Alternatives envisagées**:
  1. Extension pure JS → ❌ CORS, pas d'accès LLM locaux
  2. Serveur HTTP local Python → ❌ Complexité firewall, risque réseau
  3. **Choix final** : Native Messaging (stdio) → ✅ Sécurité max, pas de port ouvert

### Pourquoi Provider Pattern ?
- **Raison**: Plan V5 exige "model-agnostic". Le pattern permet d'ajouter Gemini, Claude sans refonte.

### Pourquoi Pas de Base de Données ?
- **Raison**: Minimisation RGPD. Aucune rétention de contenu email nécessaire. Tout est éphémère.

---

## 📝 Notes
- Dernière mise à jour: 2026-01-02 (Plan V5 appliqué)
- Ajouter ici toute nouvelle leçon apprise pendant le dev/audit
- Référencer ce fichier avant de répéter une erreur connue
